from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import httpx, sqlite3, json, re, os, hashlib, hmac, uuid

app=FastAPI(title='Ana Agent Tools',version='1.0.0')
EA=os.getenv('EA_BASE_URL','https://calendario.nolapenses.com.ar/index.php/api/v1').rstrip('/')
DB=os.getenv('TOOLS_DB','/data/ana_tools.db')
TZ=ZoneInfo('America/Argentina/Buenos_Aires')
PROVIDER_ID=int(os.getenv('PROVIDER_ID','2'))
ADMIN_PHONES={digits for digits in (re.sub(r'\D','',v) for v in os.getenv('ADMIN_PHONES','').split(',')) if digits}
EXPECTED_BASIC_AUTH_SHA256=os.getenv('EXPECTED_BASIC_AUTH_SHA256','').strip().lower()
CLINIC_ADDRESS='Junín 383, Clínica Domínguez D’Agata'
CLINIC_MAPS_URL='https://maps.app.goo.gl/DFzPyGhUfcVSd5qN8'
SERVICES={
 'consulta': {'id':1,'name':'Consulta odontológica','duration':60},
 'consulta odontologica': {'id':1,'name':'Consulta odontológica','duration':60},
 'camioneros': {'id':2,'name':'Consulta OS Camioneros','duration':15},
 'consulta os camioneros': {'id':2,'name':'Consulta OS Camioneros','duration':15},
 'urgencia': {'id':3,'name':'Urgencia odontológica','duration':60},
 'urgencia odontologica': {'id':3,'name':'Urgencia odontológica','duration':60},
 'limpieza': {'id':4,'name':'Limpieza dental','duration':60},
 'limpieza dental': {'id':4,'name':'Limpieza dental','duration':60},
 'arreglo': {'id':5,'name':'Arreglo dental','duration':60},
 'arreglo dental': {'id':5,'name':'Arreglo dental','duration':60},
 'conducto': {'id':6,'name':'Tratamiento de conducto / Endodoncia','duration':120},
 'endodoncia': {'id':6,'name':'Tratamiento de conducto / Endodoncia','duration':120},
 'incrustacion': {'id':7,'name':'Incrustación','duration':120},
}

_INITIALIZED_DBS=set()

def init_db():
 if DB in _INITIALIZED_DBS:return
 c=sqlite3.connect(DB);c.execute('PRAGMA journal_mode=WAL');c.execute('''CREATE TABLE IF NOT EXISTS tool_runs(id INTEGER PRIMARY KEY, message_id TEXT NOT NULL, tool TEXT NOT NULL, request_hash TEXT NOT NULL, role TEXT, requester_phone TEXT, dry_run INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(message_id,tool,request_hash))''')
 cols={r[1] for r in c.execute('PRAGMA table_info(tool_runs)')}
 if 'requester_phone' not in cols:c.execute('ALTER TABLE tool_runs ADD COLUMN requester_phone TEXT')
 c.execute('CREATE INDEX IF NOT EXISTS idx_tool_runs_actor ON tool_runs(requester_phone,tool,status,dry_run,id)')
 c.execute('''CREATE TABLE IF NOT EXISTS pending_exceptional_bookings(owner_number TEXT PRIMARY KEY, booking_json TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL)''')
 pending_columns={row[1] for row in c.execute('PRAGMA table_info(pending_day_blocks)').fetchall()}
 if pending_columns and 'proposal_id' not in pending_columns:c.execute('DROP TABLE pending_day_blocks')
 c.execute('''CREATE TABLE IF NOT EXISTS pending_day_blocks(proposal_id TEXT PRIMARY KEY, owner_number TEXT NOT NULL, preview_message_id TEXT NOT NULL, preview_event_timestamp INTEGER NOT NULL DEFAULT 0, block_json TEXT NOT NULL, snapshot_hash TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL, consumed_at TEXT)''')
 pending_columns={row[1] for row in c.execute('PRAGMA table_info(pending_day_blocks)').fetchall()}
 if 'preview_event_timestamp' not in pending_columns:c.execute('ALTER TABLE pending_day_blocks ADD COLUMN preview_event_timestamp INTEGER NOT NULL DEFAULT 0')
 c.execute('CREATE INDEX IF NOT EXISTS idx_pending_day_blocks_owner ON pending_day_blocks(owner_number,consumed_at,expires_at,created_at)')
 c.execute('''CREATE TABLE IF NOT EXISTS day_blocks(
  id INTEGER PRIMARY KEY, provider_id INTEGER NOT NULL, block_date TEXT NOT NULL,
  reason TEXT NOT NULL, unavailability_id INTEGER, owner_number TEXT NOT NULL,
  status TEXT NOT NULL, created_at TEXT NOT NULL, verified_at TEXT,
  ana_summary_sent_at TEXT, UNIQUE(provider_id,block_date))''')
 c.execute('''CREATE TABLE IF NOT EXISTS rebooking_campaigns(
  id INTEGER PRIMARY KEY, block_id INTEGER NOT NULL, appointment_id INTEGER NOT NULL,
  patient_name TEXT NOT NULL, patient_phone TEXT NOT NULL DEFAULT '', service_name TEXT NOT NULL,
  service_id INTEGER, original_start TEXT NOT NULL, original_end TEXT NOT NULL,
  status TEXT NOT NULL, outreach_text TEXT NOT NULL DEFAULT '', whatsapp_message_id TEXT,
  last_error TEXT, new_start TEXT, new_end TEXT, original_fingerprint_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  FOREIGN KEY(block_id) REFERENCES day_blocks(id), UNIQUE(block_id,appointment_id))''')
 campaign_columns={row[1] for row in c.execute('PRAGMA table_info(rebooking_campaigns)').fetchall()}
 if 'original_fingerprint_json' not in campaign_columns:c.execute("ALTER TABLE rebooking_campaigns ADD COLUMN original_fingerprint_json TEXT NOT NULL DEFAULT '{}'")
 c.execute('CREATE INDEX IF NOT EXISTS idx_rebooking_queue ON rebooking_campaigns(status,block_id,id)')
 c.execute('CREATE INDEX IF NOT EXISTS idx_rebooking_phone ON rebooking_campaigns(patient_phone,status,id)')
 c.execute('''CREATE TABLE IF NOT EXISTS mutation_claims(claim_key TEXT PRIMARY KEY,payload_hash TEXT NOT NULL,status TEXT NOT NULL,result_json TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)''')
 cutoff=(datetime.now(TZ)-timedelta(days=90)).isoformat();c.execute('DELETE FROM tool_runs WHERE created_at<?',(cutoff,))
 c.commit()
 try:os.chmod(DB,0o600)
 except OSError:pass
 _INITIALIZED_DBS.add(DB)
 c.close()

def db(readonly=False):
 if readonly:
  c=sqlite3.connect(f'file:{os.path.abspath(DB)}?mode=ro',uri=True)
  c.execute('PRAGMA query_only=ON')
  return c
 init_db()
 c=sqlite3.connect(DB)
 return c

def digits(v): return re.sub(r'\D','',str(v or ''))
def clean_phone(v):
 value=digits(v)
 if len(value)==10 and value.startswith('266'):return '549'+value
 return value
def norm(v): return ''.join(c for c in __import__('unicodedata').normalize('NFD',str(v or '').lower()) if __import__('unicodedata').category(c)!='Mn').strip()
def auth_headers(req:Request):
 a=req.headers.get('authorization','')
 if not a.lower().startswith('basic '): raise HTTPException(401,'Autenticación requerida')
 if EXPECTED_BASIC_AUTH_SHA256:
  actual=hashlib.sha256(a.encode()).hexdigest()
  if not hmac.compare_digest(actual,EXPECTED_BASIC_AUTH_SHA256):raise HTTPException(401,'Credencial inválida')
 return {'Authorization':a,'Accept':'application/json'}
def authorized_admin(x):return x.role=='admin' and x.override_authorized and digits(x.requester_phone) in ADMIN_PHONES
def req_hash(x): return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def audit(message_id,tool,role,dry_run,status,result,payload):
 h=req_hash(payload)
 if dry_run and tool in ('day_block','reschedule'):return h
 c=db();c.execute('INSERT OR IGNORE INTO tool_runs(message_id,tool,request_hash,role,requester_phone,dry_run,status,result_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(message_id,tool,h,role,digits(payload.get('requester_phone')),int(dry_run),status,json.dumps(result,ensure_ascii=False),datetime.now(TZ).isoformat()));c.commit();c.close();return h
def prior(message_id,tool,payload,readonly=False):
 c=db(readonly=readonly)
 if tool in ('book','cancel','day_block','reschedule'):
  statuses=('success','created_unverified') if tool=='book' else ('success',)
  marks=','.join('?' for _ in statuses)
  r=c.execute(f'SELECT result_json,request_hash FROM tool_runs WHERE message_id=? AND tool=? AND status IN ({marks}) ORDER BY id LIMIT 1',(message_id,tool,*statuses)).fetchone()
  c.close()
  if not r:return None
  result=json.loads(r[0])
  if tool=='book' and r[1]!=req_hash(payload):
   return {'ok':False,'confirmed':False,'verified':False,'error':'multiple_bookings_in_one_message','message':'Ya se procesó una reserva con este mensaje. Para otra persona se necesita un mensaje nuevo.','first_booking':result}
  return result
 else:
  h=req_hash(payload);r=c.execute('SELECT result_json FROM tool_runs WHERE message_id=? AND tool=? AND request_hash=? AND status=?',(message_id,tool,h,'success')).fetchone()
  c.close();return json.loads(r[0]) if r else None
async def ea(req,method,path,**kwargs):
 headers=auth_headers(req);headers.update(kwargs.pop('headers',{}))
 async with httpx.AsyncClient(timeout=20,follow_redirects=True) as client:
  r=await client.request(method,EA+path,headers=headers,**kwargs)
 if r.status_code>=400: raise HTTPException(502,f'EasyAppointments respondió HTTP {r.status_code}')
 if r.status_code==204:return None
 try:return r.json()
 except:return {'text':r.text[:500]}
async def validate_ea_auth(req):
 await ea(req,'GET','/appointments',params={'providerId':PROVIDER_ID,'date':'1900-01-01','length':1})
def service_for(name,service_id=None):
 if service_id:
  for v in SERVICES.values():
   if v['id']==int(service_id):return v
 return SERVICES.get(norm(name))
def parse_start(a): return str(a.get('start') or a.get('start_datetime') or '').replace('T',' ')[:19]
def parse_end(a): return str(a.get('end') or a.get('end_datetime') or '').replace('T',' ')[:19]
def person(a):
 c=a.get('customer') or {};return (' '.join([str(c.get('firstName') or c.get('first_name') or ''),str(c.get('lastName') or c.get('last_name') or '')]).strip() or a.get('customerName') or 'Paciente sin nombre')
def svc(a):
 s=a.get('service') or {}
 return (s.get('name') or a.get('serviceName') or 'Turno') if isinstance(s,dict) else (a.get('serviceName') or str(s or 'Turno'))
def customer_phone(a):
 c=a.get('customer') or {}
 return clean_phone(c.get('phone') or c.get('phoneNumber') or c.get('mobileNumber') or c.get('mobile_number') or a.get('customerPhone'))

def phone_candidates(value):
 value=digits(value)
 if not value:return []
 candidates={value}
 if value.startswith('549'):candidates.add('54'+value[3:])
 elif value.startswith('54'):candidates.add('549'+value[2:])
 elif len(value)==10 and value.startswith('266'):candidates.update({'549'+value,'54'+value})
 return sorted(candidates)
def customer_coverage(a):
 c=a.get('customer') or {}
 value=(c.get('customField2') or c.get('custom_field_2') or c.get('coverage') or a.get('customerCoverage') or a.get('coverage'))
 return str(value).strip() if value else 'Sin cobertura registrada'
def appointment_service_id(a):
 s=a.get('service') or {}
 raw=(s.get('id') if isinstance(s,dict) else None) or a.get('serviceId') or a.get('service_id') or a.get('id_services')
 try:return int(raw)
 except (TypeError,ValueError):
  return 6 if norm(svc(a)) in ('tratamiento de conducto / endodoncia','tratamiento de conducto','conducto','endodoncia') else None
def active_appointments(rows):
 return [a for a in rows if isinstance(a,dict) and 'cancel' not in str(a.get('status','')).lower()]
def day_profitability(rows):
 active=active_appointments(rows);profitable=[a for a in active if appointment_service_id(a) in (6,7)]
 if not active:return {'status':'empty_day','has_profitable_treatment':False,'profitable_treatments':0,'appointments':0}
 return {'status':'profitable_treatment_present' if profitable else 'needs_profitable_treatment','has_profitable_treatment':bool(profitable),'profitable_treatments':len(profitable),'appointments':len(active)}
def profitability_by_date(rows):
 grouped={}
 for a in active_appointments(rows):
  day=parse_start(a)[:10]
  if day:grouped.setdefault(day,[]).append(a)
 return {day:day_profitability(items) for day,items in sorted(grouped.items())}
def public_appointment(a):
 return {'id':a.get('id'),'start':parse_start(a),'end':parse_end(a),'patient':person(a),'service':svc(a),'coverage':customer_coverage(a),'status':a.get('status')}

def rebooking_appointment(a):
 item=public_appointment(a)
 item.update({'phone':customer_phone(a),'has_phone':bool(customer_phone(a)),'service_id':appointment_service_id(a)})
 return item

def active_overlaps(rows,start,end):
 out=[]
 for a in rows if isinstance(rows,list) else []:
  if 'cancel' in str(a.get('status','')).lower():continue
  try:
   a_start=datetime.strptime(parse_start(a),'%Y-%m-%d %H:%M:%S').replace(tzinfo=TZ)
   a_end=datetime.strptime(parse_end(a),'%Y-%m-%d %H:%M:%S').replace(tzinfo=TZ)
  except Exception:continue
  if a_start<end and a_end>start:out.append(public_appointment(a))
 return out

def slot_text(v):
 value=str(v or '').replace('T',' ')
 return value if len(value)>=16 else value[:5]

def slot_start(v,date):
 value=str(v or '').replace('T',' ')
 time=value[11:16] if len(value)>=16 else value[:5]
 try:return datetime.strptime(f'{date} {time}','%Y-%m-%d %H:%M').replace(tzinfo=TZ)
 except Exception:return None

def policy_allows(start,s):
 if not start:return False
 weekday=start.weekday();minute=start.hour*60+start.minute;duration=s['duration']
 if weekday in (0,4):
  if duration==120:return minute in (570,720)
  if s['id']==2:return minute==690
  return duration==60 and minute==780
 if weekday in (1,2,3):
  if duration==120:return minute==960
  if s['id']==2:return weekday==3 and minute==1080
  return duration==60 and minute in (960,1020,1080)
 if weekday==5:return duration==120 and minute==600
 return False

def overlap_capacity_allows(rows,start,end,s):
 overlaps=active_overlaps(rows,start,end)
 # Excepción documentada: hasta dos consultas Camioneros lunes/viernes 11:30 o jueves 18:00.
 camioneros_double=(s['id']==2 and ((start.weekday() in (0,4) and start.strftime('%H:%M')=='11:30') or (start.weekday()==3 and start.strftime('%H:%M')=='18:00')))
 return (len(overlaps)<2) if camioneros_double else not overlaps

async def safe_availability(req,s,date,raw=None,limit=3):
 raw_slots=raw if isinstance(raw,list) else await ea(req,'GET','/availabilities',params={'providerId':PROVIDER_ID,'serviceId':s['id'],'date':date})
 rows=await ea(req,'GET','/appointments',params={'providerId':PROVIDER_ID,'aggregates':'1','date':date,'length':1000})
 valid=[]
 for value in raw_slots if isinstance(raw_slots,list) else []:
  start=slot_start(value,date)
  if not policy_allows(start,s):continue
  end=start+timedelta(minutes=s['duration'])
  if not overlap_capacity_allows(rows,start,end,s):continue
  valid.append(slot_text(value))
 unique=[]
 for value in valid:
  if value not in unique:unique.append(value)
 return {'slots':unique[:limit],'total_valid':len(unique),'has_more':len(unique)>limit,'profitability':day_profitability(rows)}

def save_pending_exception(x,reason='outside_configured_availability',conflicts=None):
 now=datetime.now(TZ);expires=now+timedelta(minutes=30);payload=x.model_dump();payload['_warning_reason']=reason;payload['_conflict_ids']=sorted(int(a.get('id')) for a in (conflicts or []) if a.get('id') is not None)
 c=db();c.execute('INSERT INTO pending_exceptional_bookings(owner_number,booking_json,reason,created_at,expires_at) VALUES(?,?,?,?,?) ON CONFLICT(owner_number) DO UPDATE SET booking_json=excluded.booking_json,reason=excluded.reason,created_at=excluded.created_at,expires_at=excluded.expires_at',(digits(x.requester_phone),json.dumps(payload,ensure_ascii=False),reason,now.isoformat(),expires.isoformat()));c.commit();c.close()
 return expires

def load_pending_exception(owner_number):
 c=db();row=c.execute('SELECT booking_json,expires_at FROM pending_exceptional_bookings WHERE owner_number=?',(digits(owner_number),)).fetchone()
 if not row:c.close();return None
 try:expires=datetime.fromisoformat(row[1])
 except Exception:expires=datetime.now(TZ)-timedelta(seconds=1)
 if expires<=datetime.now(TZ):
  c.execute('DELETE FROM pending_exceptional_bookings WHERE owner_number=?',(digits(owner_number),));c.commit();c.close();return None
 c.close();return {'booking':json.loads(row[0]),'expires_at':row[1]}

def clear_pending_exception(owner_number):
 c=db();c.execute('DELETE FROM pending_exceptional_bookings WHERE owner_number=?',(digits(owner_number),));c.commit();c.close()

def save_pending_day_block(owner_number,preview_message_id,preview_event_timestamp,payload):
 now=datetime.now(TZ);expires=now+timedelta(minutes=30);proposal_id=str(uuid.uuid4());snapshot_hash=req_hash(payload.get('appointments',[]))
 c=db();c.execute('INSERT INTO pending_day_blocks(proposal_id,owner_number,preview_message_id,preview_event_timestamp,block_json,snapshot_hash,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?)',(proposal_id,digits(owner_number),str(preview_message_id),int(preview_event_timestamp),json.dumps(payload,ensure_ascii=False),snapshot_hash,now.isoformat(),expires.isoformat()));c.commit();c.close()
 return {'proposal_id':proposal_id,'expires_at':expires.isoformat(),'snapshot_hash':snapshot_hash}

def load_pending_day_block(owner_number,proposal_id,readonly=False):
 if not proposal_id:return None
 c=db(readonly=readonly);params=[digits(owner_number),proposal_id];sql='SELECT proposal_id,preview_message_id,preview_event_timestamp,block_json,snapshot_hash,expires_at FROM pending_day_blocks WHERE owner_number=? AND proposal_id=? AND consumed_at IS NULL'
 row=c.execute(sql,params).fetchone()
 if not row:c.close();return None
 try:expires=datetime.fromisoformat(row[5])
 except Exception:expires=datetime.now(TZ)-timedelta(seconds=1)
 if expires<=datetime.now(TZ):
  if not readonly:c.execute('UPDATE pending_day_blocks SET consumed_at=? WHERE proposal_id=?',(datetime.now(TZ).isoformat(),row[0]));c.commit()
  c.close();return None
 c.close();return {'proposal_id':row[0],'preview_message_id':row[1],'preview_event_timestamp':int(row[2]),'block':json.loads(row[3]),'snapshot_hash':row[4],'expires_at':row[5]}

def consume_pending_day_block(proposal_id):
 c=db();c.execute('UPDATE pending_day_blocks SET consumed_at=? WHERE proposal_id=? AND consumed_at IS NULL',(datetime.now(TZ).isoformat(),proposal_id));c.commit();c.close()

def claim_mutation(claim_key,payload):
 now=datetime.now(TZ).isoformat();payload_hash=req_hash(payload);c=db();c.execute('BEGIN IMMEDIATE')
 row=c.execute('SELECT payload_hash,status,result_json FROM mutation_claims WHERE claim_key=?',(claim_key,)).fetchone()
 if row:
  c.commit();c.close()
  if row[0]!=payload_hash:return {'state':'conflict'}
  if row[1]=='completed' and row[2]:return {'state':'completed','result':json.loads(row[2])}
  return {'state':'in_progress'}
 c.execute("INSERT INTO mutation_claims(claim_key,payload_hash,status,created_at,updated_at) VALUES(?,?,'in_progress',?,?)",(claim_key,payload_hash,now,now));c.commit();c.close();return {'state':'claimed'}

def finish_mutation(claim_key,result,status='completed'):
 c=db();c.execute('UPDATE mutation_claims SET status=?,result_json=?,updated_at=? WHERE claim_key=?',(status,json.dumps(result,ensure_ascii=False),datetime.now(TZ).isoformat(),claim_key));c.commit();c.close()

def release_mutation(claim_key):
 c=db();c.execute("DELETE FROM mutation_claims WHERE claim_key=? AND status='in_progress'",(claim_key,));c.commit();c.close()

def valid_future_date(value):
 try:day=datetime.strptime(str(value or ''),'%Y-%m-%d').date()
 except Exception:return None
 return day if day>=datetime.now(TZ).date() else None

async def day_appointments(request,date):
 raw=await ea(request,'GET','/appointments',params={'providerId':PROVIDER_ID,'aggregates':'1','date':date,'length':1000})
 rows=active_appointments(raw if isinstance(raw,list) else [])
 rows.sort(key=parse_start)
 return rows

def outreach_text(row,reason):
 start=parse_start(row);date=start[8:10]+'/'+start[5:7]+'/'+start[:4];time=start[11:16]
 reason_text=f' por {reason.strip()}' if str(reason or '').strip() else ''
 return (f'Hola {person(row).split()[0] if person(row) else ""}, te escribo desde el consultorio de Ana Maldonado. '
         f'Necesitamos reprogramar tu turno del {date} a las {time}{reason_text}. '
         'Respondeme por acá qué día y franja horaria te convienen, y te paso opciones reales de la agenda. '
         'Tu turno todavía no fue cancelado: primero vamos a acordar con vos el nuevo horario.')

def appointment_payload_for_update(a,start,end):
 service=a.get('service') or {};customer=a.get('customer') or {}
 service_id=(service.get('id') if isinstance(service,dict) else None) or a.get('serviceId') or a.get('id_services')
 customer_id=(customer.get('id') if isinstance(customer,dict) else None) or a.get('customerId') or a.get('id_users_customer')
 provider_id=a.get('providerId') or a.get('id_users_provider') or PROVIDER_ID
 payload={'start':start.strftime('%Y-%m-%d %H:%M:%S'),'end':end.strftime('%Y-%m-%d %H:%M:%S'),'status':a.get('status') or 'Booked','notes':a.get('notes') if a.get('notes') is not None else '','customerId':int(customer_id),'providerId':int(provider_id),'serviceId':int(service_id)}
 for source,target in (('location','location'),('meetingLink','meetingLink'),('color','color')):
  if a.get(source) is not None:payload[target]=a.get(source)
 return payload

def appointment_payload_from_snapshot(snapshot):
 return {key:snapshot[key] for key in ('start','end','status','notes','customerId','providerId','serviceId','location','meetingLink','color') if key in snapshot}

def nested_id(record,key,direct_key):
 value=record.get(direct_key)
 if value is not None:return int(value)
 nested=record.get(key)
 return int(nested.get('id')) if isinstance(nested,dict) and nested.get('id') is not None else 0

def appointment_fingerprint(a):
 fp={'id':int(a.get('id') or 0),'start':parse_start(a),'end':parse_end(a),'status':str(a.get('status') or ''),'notes':str(a.get('notes') or ''),'customerId':nested_id(a,'customer','customerId'),'providerId':nested_id(a,'provider','providerId'),'serviceId':nested_id(a,'service','serviceId')}
 for key in ('location','meetingLink','color'):
  if a.get(key) is not None:fp[key]=a.get(key)
 return fp

class ReadIn(BaseModel):
 operation:Literal['list','next','availability','find','last_booking']
 role:Literal['admin','patient']
 requester_phone:str=''
 message_id:str
 date:Optional[str]=None
 from_date:Optional[str]=None
 till_date:Optional[str]=None
 service_name:Optional[str]=None
 service_id:Optional[int]=None
 patient_name:Optional[str]=None
 dni:Optional[str]=None
 time:Optional[str]=None

class ClinicInfoIn(BaseModel):
 role:Literal['admin','patient']
 requester_phone:str=''
 message_id:str

@app.get('/healthz')
def health():
 c=db();c.close();return {'ok':True}

@app.get('/v1/evidence/{message_id}')
def evidence(message_id:str,request:Request):
 auth_headers(request)
 c=db();rows=c.execute('SELECT tool,status,dry_run,result_json,created_at FROM tool_runs WHERE message_id=? ORDER BY id',(message_id,)).fetchall();c.close()
 return {'message_id':message_id,'runs':[{'tool':r[0],'status':r[1],'dry_run':bool(r[2]),'result':json.loads(r[3]),'created_at':r[4]} for r in rows]}

@app.post('/v1/clinic-info')
def clinic_info_tool(x:ClinicInfoIn,request:Request):
 auth_headers(request)
 payload=x.model_dump();cached=prior(x.message_id,'clinic_info',payload)
 if cached:return cached
 out={
  'ok':True,
  'clinic_name':'Clínica Domínguez D’Agata',
  'address':CLINIC_ADDRESS,
  'maps_url':CLINIC_MAPS_URL,
  'message':f'El consultorio está en {CLINIC_ADDRESS}. Ubicación: {CLINIC_MAPS_URL}',
 }
 audit(x.message_id,'clinic_info',x.role,False,'success',out,payload)
 return out

@app.post('/v1/read')
async def read_tool(x:ReadIn,request:Request):
 payload=x.model_dump();cached=prior(x.message_id,'read',payload)
 if cached:return cached
 if x.operation in ('list','next') and x.role!='admin':
  out={'ok':False,'error':'permission_denied','message':'Los pacientes no pueden consultar la agenda de otras personas.'};audit(x.message_id,'read',x.role,False,'denied',out,payload);return out
 try:
  if x.operation=='availability':
   s=service_for(x.service_name,x.service_id)
   if not s or not x.date:raise HTTPException(400,'Faltan servicio o fecha')
   raw=await ea(request,'GET','/availabilities',params={'providerId':PROVIDER_ID,'serviceId':s['id'],'date':x.date})
   filtered=await safe_availability(request,s,x.date,raw,3)
   out={'ok':True,'operation':'availability','date':x.date,'service':s['name'],'duration_minutes':s['duration'],**filtered}
  elif x.operation=='last_booking':
   actor=digits(x.requester_phone);c=db();row=c.execute("SELECT result_json FROM tool_runs WHERE requester_phone=? AND tool='book' AND status='success' AND dry_run=0 ORDER BY id DESC LIMIT 1",(actor,)).fetchone();c.close()
   previous=json.loads(row[0]) if row else None;appointment_id=(previous or {}).get('appointment_id')
   if not appointment_id:out={'ok':True,'operation':'last_booking','found':False,'reason':'no_successful_booking_for_actor','matches':[]}
   else:
    try:
     basic=await ea(request,'GET',f'/appointments/{int(appointment_id)}');day=parse_start(basic)[:10] or str((previous or {}).get('start',''))[:10]
     enriched=await ea(request,'GET','/appointments',params={'providerId':PROVIDER_ID,'aggregates':'1','date':day,'length':100}) if day else []
     appt=next((a for a in enriched if int(a.get('id') or 0)==int(appointment_id)),basic)
    except HTTPException as err:
     if 'HTTP 404' in str(err.detail):out={'ok':True,'operation':'last_booking','found':False,'reason':'appointment_no_longer_exists','matches':[]}
     else:raise
    else:
     active='cancel' not in str(appt.get('status','')).lower();out={'ok':True,'operation':'last_booking','found':active,'matches':[public_appointment(appt)] if active else [],'appointment_id':appointment_id}
  elif x.operation=='find':
   today=datetime.now(TZ).date();params={'providerId':PROVIDER_ID,'aggregates':'1','sort':'start','from':x.from_date or (today-timedelta(days=180)).isoformat(),'till':x.till_date or (today+timedelta(days=365)).isoformat(),'length':1000}
   if x.date:params['date']=x.date
   raw=await ea(request,'GET','/appointments',params=params);rows=raw if isinstance(raw,list) else []
   rows=[a for a in rows if 'cancel' not in str(a.get('status','')).lower()]
   if x.role=='patient':rows=[a for a in rows if customer_phone(a)==digits(x.requester_phone)]
   if x.patient_name:
    wanted=[t for t in re.split(r'\s+',norm(x.patient_name)) if len(t)>1];rows=[a for a in rows if wanted and all(t in norm(person(a)) for t in wanted)]
   if x.dni:
    wanted_dni=digits(x.dni);rows=[a for a in rows if digits((a.get('customer') or {}).get('customField1') or (a.get('customer') or {}).get('custom_field_1'))==wanted_dni]
   if x.date:rows=[a for a in rows if parse_start(a)[:10]==x.date]
   if x.time:rows=[a for a in rows if parse_start(a)[11:16]==x.time[:5]]
   rows.sort(key=parse_start);matches=[public_appointment(a) for a in rows[:20]]
   out={'ok':True,'operation':'find','found':bool(matches),'matches':matches,'count':len(rows),'criteria':{'patient_name':x.patient_name,'date':x.date,'time':x.time,'dni':digits(x.dni)}}
  else:
   params={'providerId':PROVIDER_ID,'aggregates':'1','sort':'start'}
   if x.operation=='next':
    today=datetime.now(TZ).date();params['from']=today.isoformat();params['till']=(today+timedelta(days=90)).isoformat()
   if x.operation=='list':
    if x.date:params['date']=x.date
    else:
     if x.from_date:params['from']=x.from_date
     if x.till_date:params['till']=x.till_date
   raw=await ea(request,'GET','/appointments',params=params);rows=raw if isinstance(raw,list) else []
   rows=[a for a in rows if 'cancel' not in str(a.get('status','')).lower()];rows.sort(key=parse_start)
   if x.operation=='next':
    now=datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S');rows=[a for a in rows if parse_start(a)>=now][:1]
   out={'ok':True,'operation':x.operation,'appointments':[public_appointment(a) for a in rows[:30]],'count':len(rows),'profitability_by_date':profitability_by_date(rows)}
  audit(x.message_id,'read',x.role,False,'success',out,payload);return out
 except HTTPException:raise
 except Exception:
  out={'ok':False,'error':'calendar_unavailable','message':'No se pudo consultar la agenda real.'};audit(x.message_id,'read',x.role,False,'error',out,payload);return out

class BookIn(BaseModel):
 role:Literal['admin','patient'];requester_phone:str='';message_id:str;dry_run:bool=False
 patient_name:str='';dni:Optional[str]=None;phone:Optional[str]=None;coverage:str=''
 service_name:str='';service_id:Optional[int]=None;date:str='';time:str=''
 override_authorized:bool=False

async def create_booking(x,request,s,start,end,name,dni,phone,exceptional=False,overlap_confirmed=False):
 if x.dry_run:
  return {'ok':True,'confirmed':False,'verified':False,'dry_run':True,'would_book':{'patient':name,'dni':dni or None,'phone':phone or None,'coverage':x.coverage,'service':s['name'],'start':start.strftime('%Y-%m-%d %H:%M:%S'),'end':end.strftime('%Y-%m-%d %H:%M:%S'),'exceptional_outside_availability':exceptional,'exceptional_overlap_confirmed':overlap_confirmed}}
 customers=[]
 if dni:customers=await ea(request,'GET','/customers',params={'q':dni,'length':100})
 elif len(phone)>=8:customers=await ea(request,'GET','/customers',params={'q':phone,'length':100})
 match=None
 for c in customers if isinstance(customers,list) else []:
  same_dni=bool(dni) and digits(c.get('customField1'))==dni
  same_phone=len(phone)>=8 and digits(c.get('phone'))==phone
  if same_dni or same_phone:match=c;break
 created=False
 if not match:
  parts=name.split();identity=dni or (phone if len(phone)>=8 else hashlib.sha256(f'{x.message_id}|{name}'.encode()).hexdigest()[:12]);match=await ea(request,'POST','/customers',json={'firstName':parts[0],'lastName':' '.join(parts[1:]),'email':f'paciente-{identity}@ana.local','phone':phone if len(phone)>=8 else '-','timezone':'America/Argentina/Buenos_Aires','language':'spanish','customField1':dni,'customField2':x.coverage,'customField5':'WhatsApp','notes':'Paciente cargado vía WhatsApp.'});created=True
 notes='Pedido por paciente vía WhatsApp.' if x.role=='patient' else ('Cargado por Ana vía WhatsApp como excepción fuera del horario habitual.' if exceptional else 'Cargado por Ana vía WhatsApp.')
 try:
  appt=await ea(request,'POST','/appointments',json={'start':start.strftime('%Y-%m-%d %H:%M:%S'),'end':end.strftime('%Y-%m-%d %H:%M:%S'),'status':'Booked','notes':notes,'customerId':match['id'],'providerId':PROVIDER_ID,'serviceId':s['id']})
 except Exception:
  if created and match.get('id'):
   try:await ea(request,'DELETE',f"/customers/{match['id']}")
   except:pass
  raise
 appt_id=appt.get('id') if isinstance(appt,dict) else None
 if not appt_id:
  return {'ok':False,'confirmed':False,'verified':False,'error':'booking_creation_unproven','message':'El sistema no devolvió un identificador de turno.'}
 try:
  verified=await ea(request,'GET',f'/appointments/{int(appt_id)}')
 except Exception:
  return {'ok':False,'confirmed':False,'verified':False,'error':'booking_verification_failed','appointment_id':appt_id,'patient':name,'service':s['name'],'start':start.strftime('%Y-%m-%d %H:%M:%S'),'message':'El turno pudo haberse creado, pero no se pudo verificar. No debe reintentarse automáticamente.'}
 verified_start=parse_start(verified);active='cancel' not in str((verified or {}).get('status','')).lower()
 if int((verified or {}).get('id') or 0)!=int(appt_id) or verified_start[:16]!=start.strftime('%Y-%m-%d %H:%M') or not active:
  return {'ok':False,'confirmed':False,'verified':False,'error':'booking_verification_failed','appointment_id':appt_id,'patient':name,'service':s['name'],'start':start.strftime('%Y-%m-%d %H:%M:%S'),'message':'El turno fue creado pero la verificación no coincidió. Requiere revisión manual.'}
 return {'ok':True,'confirmed':True,'verified':True,'dry_run':False,'appointment_id':appt_id,'customer_id':match.get('id'),'patient':name,'service':s['name'],'start':start.strftime('%Y-%m-%d %H:%M:%S'),'end':end.strftime('%Y-%m-%d %H:%M:%S'),'exceptional_outside_availability':exceptional,'exceptional_overlap_confirmed':overlap_confirmed}

def validate_booking(x):
 s=service_for(x.service_name,x.service_id);dni=digits(x.dni);phone=digits(x.requester_phone if x.role=='patient' else x.phone);name=' '.join(x.patient_name.split()).strip();errors=[];missing=[]
 parts=name.split()
 if not s:missing.append('servicio')
 if not parts:missing.append('nombre')
 elif len(parts)<2:missing.append('apellido')
 if not str(x.coverage or '').strip():missing.append('cobertura')
 if x.role=='patient' and not dni:missing.append('dni')
 elif dni and len(dni)<7:errors.append('DNI inválido')
 if x.role=='patient' and not phone:missing.append('telefono')
 elif phone and len(phone)<8:errors.append('teléfono inválido')
 if not str(x.date or '').strip():missing.append('fecha')
 if not str(x.time or '').strip():missing.append('hora')
 start=None
 if 'fecha' not in missing and 'hora' not in missing:
  try:start=datetime.strptime(f'{x.date} {x.time[:5]}','%Y-%m-%d %H:%M').replace(tzinfo=TZ)
  except Exception:errors.append('fecha u hora inválida')
 if start and start<=datetime.now(TZ):errors.append('el horario está en el pasado')
 return s,dni,phone,name,start,missing,errors

@app.post('/v1/book')
async def book_tool(x:BookIn,request:Request):
 payload=x.model_dump();cached=prior(x.message_id,'book',payload)
 if cached:return cached
 s,dni,phone,name,start,missing,errors=validate_booking(x)
 if missing:
  out={'ok':False,'confirmed':False,'error':'missing_data','patient':name or None,'missing_fields':missing,'invalid_fields':errors};audit(x.message_id,'book',x.role,x.dry_run,'denied',out,payload);return out
 if errors:
  out={'ok':False,'confirmed':False,'error':'validation','missing_fields':[],'invalid_fields':errors};audit(x.message_id,'book',x.role,x.dry_run,'denied',out,payload);return out
 try:
  end=start+timedelta(minutes=s['duration'])
  slots=await ea(request,'GET','/availabilities',params={'providerId':PROVIDER_ID,'serviceId':s['id'],'date':x.date})
  filtered=await safe_availability(request,s,x.date,slots,3)
  wanted=x.time[:5];available=any((str(v)[11:16] if len(str(v))>=16 else str(v)[:5])==wanted for v in filtered['slots'])
  if not available:
   rows=await ea(request,'GET','/appointments',params={'providerId':PROVIDER_ID,'aggregates':'1','date':x.date,'length':1000})
   overlaps=active_overlaps(rows,start,end)
   if overlaps:
    if x.role=='admin' and x.override_authorized:
     expires=save_pending_exception(x,'slot_conflict',overlaps)
     out={'ok':False,'confirmed':False,'error':'slot_conflict_confirmation_required','date':x.date,'time':wanted,'service':s['name'],'duration_minutes':s['duration'],'patient':name,'conflicts':overlaps[:5],'alternatives':filtered['slots'],'expires_at':expires.isoformat(),'message':'El horario se superpone con uno o más turnos. Ana puede elegir una alternativa o confirmar explícitamente que desea mantener la superposición.'};audit(x.message_id,'book',x.role,x.dry_run,'confirmation_required',out,payload);return out
    out={'ok':False,'error':'slot_occupied','date':x.date,'time':wanted,'conflicts':overlaps[:5],'alternatives':filtered['slots']};audit(x.message_id,'book',x.role,x.dry_run,'occupied',out,payload);return out
   if x.role=='admin' and x.override_authorized:
    expires=save_pending_exception(x,'outside_configured_availability')
    out={'ok':False,'error':'outside_availability_confirmation_required','date':x.date,'time':wanted,'service':s['name'],'duration_minutes':s['duration'],'patient':name,'expires_at':expires.isoformat(),'alternatives':filtered['slots']};audit(x.message_id,'book',x.role,x.dry_run,'confirmation_required',out,payload);return out
   out={'ok':False,'error':'slot_unavailable','reason':'outside_configured_availability','date':x.date,'time':wanted,'alternatives':filtered['slots']};audit(x.message_id,'book',x.role,x.dry_run,'unavailable',out,payload);return out
  out=await create_booking(x,request,s,start,end,name,dni,phone,False)
  status='success' if out.get('ok') else ('created_unverified' if out.get('appointment_id') else 'error')
  audit(x.message_id,'book',x.role,x.dry_run,status,out,payload);return out
 except HTTPException as e:
  out={'ok':False,'error':'booking_failed','message':e.detail};audit(x.message_id,'book',x.role,x.dry_run,'error',out,payload);return out

class ConfirmExceptionalIn(BaseModel):
 role:Literal['admin','patient'];requester_phone:str='';message_id:str;dry_run:bool=False
 confirmed:bool=False;override_authorized:bool=False

@app.post('/v1/confirm-exception')
async def confirm_exception_tool(x:ConfirmExceptionalIn,request:Request):
 payload=x.model_dump();cached=prior(x.message_id,'confirm_exception',payload)
 if cached:return cached
 if x.role!='admin' or not x.override_authorized or not x.confirmed:
  out={'ok':False,'error':'permission_or_confirmation_required','message':'La excepción requiere confirmación explícita de Ana desde su número autorizado.'};audit(x.message_id,'confirm_exception',x.role,x.dry_run,'denied',out,payload);return out
 pending=load_pending_exception(x.requester_phone)
 if not pending:
  out={'ok':False,'error':'no_pending_exception','message':'No hay una propuesta excepcional vigente para confirmar.'};audit(x.message_id,'confirm_exception',x.role,x.dry_run,'denied',out,payload);return out
 warning_reason=pending['booking'].pop('_warning_reason','outside_configured_availability');warned_ids=set(pending['booking'].pop('_conflict_ids',[]));booking={**pending['booking'],'message_id':x.message_id,'requester_phone':x.requester_phone,'dry_run':x.dry_run,'override_authorized':True,'role':'admin'}
 original=BookIn(**booking);s,dni,phone,name,start,missing,errors=validate_booking(original)
 if missing or errors:
  clear_pending_exception(x.requester_phone);out={'ok':False,'confirmed':False,'error':'missing_data' if missing else 'validation','missing_fields':missing,'invalid_fields':errors};audit(x.message_id,'confirm_exception',x.role,x.dry_run,'denied',out,payload);return out
 try:
  end=start+timedelta(minutes=s['duration'])
  rows=await ea(request,'GET','/appointments',params={'providerId':PROVIDER_ID,'aggregates':'1','date':original.date,'length':1000})
  overlaps=active_overlaps(rows,start,end)
  if overlaps:
   current_ids={int(a['id']) for a in overlaps if a.get('id') is not None}
   if warning_reason!='slot_conflict' or current_ids!=warned_ids:
    expires=save_pending_exception(original,'slot_conflict',overlaps);out={'ok':False,'confirmed':False,'error':'slot_conflict_changed_confirmation_required','date':original.date,'time':original.time[:5],'conflicts':overlaps[:5],'expires_at':expires.isoformat(),'message':'Los conflictos cambiaron desde la advertencia anterior. Revisalos y confirmá nuevamente si querés mantener la superposición.'};audit(x.message_id,'confirm_exception',x.role,x.dry_run,'confirmation_required',out,payload);return out
  out=await create_booking(original,request,s,start,end,name,dni,phone,True,bool(overlaps))
  clear_pending_exception(x.requester_phone);audit(x.message_id,'confirm_exception',x.role,x.dry_run,'success',out,payload);return out
 except HTTPException as e:
  out={'ok':False,'error':'booking_failed','message':e.detail};audit(x.message_id,'confirm_exception',x.role,x.dry_run,'error',out,payload);return out

class CancelIn(BaseModel):
 role:Literal['admin','patient'];requester_phone:str='';message_id:str;dry_run:bool=False;appointment_id:int;confirmed:bool=False
@app.post('/v1/cancel')
async def cancel_tool(x:CancelIn,request:Request):
 payload=x.model_dump();cached=prior(x.message_id,'cancel',payload)
 if cached:return cached
 if x.role!='admin' or not x.confirmed:
  out={'ok':False,'error':'permission_or_confirmation_required','message':'La cancelación requiere un administrador autorizado y confirmación explícita.'};audit(x.message_id,'cancel',x.role,x.dry_run,'denied',out,payload);return out
 try:appt=await ea(request,'GET',f'/appointments/{x.appointment_id}')
 except HTTPException:
  out={'ok':False,'error':'not_found'};audit(x.message_id,'cancel',x.role,x.dry_run,'error',out,payload);return out
 if x.dry_run:
  out={'ok':True,'dry_run':True,'would_cancel':{'appointment_id':x.appointment_id,'start':parse_start(appt),'patient':person(appt)}};audit(x.message_id,'cancel',x.role,True,'success',out,payload);return out
 await ea(request,'DELETE',f'/appointments/{x.appointment_id}')
 out={'ok':True,'dry_run':False,'cancelled_appointment_id':x.appointment_id};audit(x.message_id,'cancel',x.role,False,'success',out,payload);return out

class DayBlockIn(BaseModel):
 action:Literal['preview','confirm','status']
 role:Literal['admin','patient'];requester_phone:str='';message_id:str;dry_run:bool=False
 date:Optional[str]=None;reason:Optional[str]=None;confirmed:bool=False;override_authorized:bool=False;proposal_id:Optional[str]=None;event_timestamp:int=0

def day_block_summary(date,reason,rows,expires_at=None):
 items=[rebooking_appointment(a) for a in rows]
 missing=[a for a in items if not a['has_phone']]
 return {'date':date,'reason':reason,'appointments':items,'appointment_count':len(items),'contactable_count':len(items)-len(missing),'missing_phone_count':len(missing),'missing_phone':missing,'expires_at':expires_at}

@app.post('/v1/day-block')
async def day_block_tool(x:DayBlockIn,request:Request):
 auth_headers(request)
 payload=x.model_dump()
 if not authorized_admin(x):
  out={'ok':False,'error':'permission_denied','message':'Sólo Ana desde su número autorizado puede bloquear una jornada.'}
  if not x.dry_run:audit(x.message_id,'day_block',x.role,False,'denied',out,payload)
  return out
 try:await validate_ea_auth(request)
 except HTTPException:
  out={'ok':False,'error':'authentication_failed','message':'No se pudo validar el acceso a la agenda.'}
  if not x.dry_run:audit(x.message_id,'day_block',x.role,False,'denied',out,payload)
  return out
 if not x.dry_run:
  cached=prior(x.message_id,'day_block',payload)
  if cached:return cached
 if x.action=='status':
  status_date=x.date or None
  c=db(readonly=x.dry_run);rows=c.execute('''SELECT d.id,d.block_date,d.reason,d.unavailability_id,d.status,d.verified_at,d.ana_summary_sent_at,
   SUM(CASE WHEN r.status='contacted' THEN 1 ELSE 0 END),SUM(CASE WHEN r.status='rescheduled' THEN 1 ELSE 0 END),
   SUM(CASE WHEN r.status='missing_phone' THEN 1 ELSE 0 END),SUM(CASE WHEN r.status IN ('send_failed','suppressed','source_changed') THEN 1 ELSE 0 END)
   FROM day_blocks d LEFT JOIN rebooking_campaigns r ON r.block_id=d.id
   WHERE (? IS NULL OR d.block_date=?) GROUP BY d.id ORDER BY d.block_date DESC LIMIT 20''',(status_date,status_date)).fetchall();c.close()
  out={'ok':True,'operation':'status','blocks':[{'block_id':r[0],'date':r[1],'reason':r[2],'unavailability_id':r[3],'status':r[4],'verified_at':r[5],'summary_sent':bool(r[6]),'contacted':r[7] or 0,'rescheduled':r[8] or 0,'missing_phone':r[9] or 0,'failed_or_suppressed':r[10] or 0} for r in rows]}
  if not x.dry_run:audit(x.message_id,'day_block',x.role,False,'success',out,payload)
  return out
 if x.action=='preview':
  if not valid_future_date(x.date):
   out={'ok':False,'error':'invalid_date','message':'La fecha debe tener formato YYYY-MM-DD y no puede estar en el pasado.'}
   if not x.dry_run:audit(x.message_id,'day_block',x.role,False,'denied',out,payload)
   return out
  try:rows=await day_appointments(request,x.date)
  except HTTPException as e:
   out={'ok':False,'error':'calendar_unavailable','message':e.detail}
   if not x.dry_run:audit(x.message_id,'day_block',x.role,False,'error',out,payload)
   return out
  reason=' '.join(str(x.reason or 'indisponibilidad de la profesional').split())[:240]
  snapshot={'date':x.date,'reason':reason,'appointments':[rebooking_appointment(a) for a in rows]}
  if x.dry_run:
   summary=day_block_summary(x.date,reason,rows)
   return {'ok':True,'operation':'preview','dry_run':True,'blocked':False,'verified':False,'would_block':{'date':x.date,'start':f'{x.date} 00:00:00','end':f'{x.date} 23:59:59','reason':reason},'would_queue_contacts':summary['contactable_count'],'would_report_missing_phone':summary['missing_phone']}
  if x.event_timestamp<=0:
   out={'ok':False,'error':'trusted_event_timestamp_required','message':'No se pudo vincular la vista previa al evento entrante.'};audit(x.message_id,'day_block',x.role,False,'denied',out,payload);return out
  proposal=save_pending_day_block(x.requester_phone,x.message_id,x.event_timestamp,snapshot)
  out={'ok':True,'operation':'preview','confirmation_required':True,'proposal_id':proposal['proposal_id'],**day_block_summary(x.date,reason,rows,proposal['expires_at']),'message':'Todavía no se bloqueó el día ni se contactó a nadie. Mostrá el resumen y pedí confirmación explícita a Ana.'}
  audit(x.message_id,'day_block',x.role,False,'confirmation_required',out,payload);return out
 if not x.confirmed:
  out={'ok':False,'error':'confirmation_required','message':'Primero hay que mostrar la vista previa y recibir confirmación explícita de Ana.'}
  if not x.dry_run:audit(x.message_id,'day_block',x.role,False,'denied',out,payload)
  return out
 if not x.proposal_id:
  out={'ok':False,'error':'proposal_id_required','message':'La confirmación debe incluir el identificador exacto de la vista previa mostrada.'}
  if not x.dry_run:audit(x.message_id,'day_block',x.role,False,'denied',out,payload)
  return out
 pending=load_pending_day_block(x.requester_phone,x.proposal_id,readonly=x.dry_run)
 if not pending:
  out={'ok':False,'error':'no_pending_day_block','message':'No hay un bloqueo pendiente vigente. Volvé a pedir la vista previa.'}
  if not x.dry_run:audit(x.message_id,'day_block',x.role,False,'denied',out,payload)
  return out
 if str(x.message_id)==str(pending['preview_message_id']) or x.event_timestamp<=pending['preview_event_timestamp']:
  out={'ok':False,'error':'confirmation_must_be_later_message','message':'La confirmación debe llegar en un mensaje posterior a la vista previa.'}
  if not x.dry_run:audit(x.message_id,'day_block',x.role,False,'denied',out,payload)
  return out
 block=pending['block'];date=block['date'];reason=block['reason']
 if x.date and x.date!=date:
  out={'ok':False,'error':'pending_date_mismatch','message':f'La confirmación pendiente corresponde al {date}, no al {x.date}.'};audit(x.message_id,'day_block',x.role,x.dry_run,'denied',out,payload);return out
 try:rows=await day_appointments(request,date)
 except HTTPException as e:
  out={'ok':False,'error':'calendar_unavailable','message':e.detail};audit(x.message_id,'day_block',x.role,x.dry_run,'error',out,payload);return out
 current_snapshot=[rebooking_appointment(a) for a in rows]
 if req_hash(current_snapshot)!=pending['snapshot_hash']:
  refreshed={'date':date,'reason':reason,'appointments':current_snapshot}
  if not x.dry_run:consume_pending_day_block(pending['proposal_id'])
  proposal=save_pending_day_block(x.requester_phone,x.message_id,x.event_timestamp,refreshed) if not x.dry_run else {'proposal_id':None,'expires_at':None}
  out={'ok':False,'error':'day_block_conflicts_changed_confirmation_required','confirmation_required':not x.dry_run,'proposal_id':proposal['proposal_id'],**day_block_summary(date,reason,rows,proposal['expires_at']),'message':'Los turnos de ese día cambiaron. Mostrá el nuevo resumen y pedí una confirmación nueva.'}
  if not x.dry_run:audit(x.message_id,'day_block',x.role,False,'confirmation_required',out,payload)
  return out
 if x.dry_run:
  summary=day_block_summary(date,reason,rows)
  return {'ok':True,'dry_run':True,'blocked':False,'verified':False,'would_block':{'date':date,'start':f'{date} 00:00:00','end':f'{date} 23:59:59','reason':reason},'would_queue_contacts':summary['contactable_count'],'would_report_missing_phone':summary['missing_phone']}
 claim_key=f'day_block:{PROVIDER_ID}:{date}';claim_payload={'proposal_id':pending['proposal_id'],'snapshot_hash':pending['snapshot_hash'],'date':date,'reason':reason}
 claim=claim_mutation(claim_key,claim_payload)
 if claim['state']=='completed':return claim['result']
 if claim['state']=='conflict':
  out={'ok':False,'blocked':False,'verified':False,'error':'idempotency_conflict','message':'Ya existe otra operación distinta para bloquear esa fecha. Ana debe revisar el estado.'};audit(x.message_id,'day_block',x.role,False,'conflict',out,payload);return out
 if claim['state']=='in_progress':
  out={'ok':False,'blocked':False,'verified':False,'error':'operation_in_progress','message':'El bloqueo ya está en curso. Consultá el estado antes de reintentar.'};audit(x.message_id,'day_block',x.role,False,'pending',out,payload);return out
 mutation_started=False;remote_verified=False
 try:
  existing=await ea(request,'GET','/unavailabilities',params={'providerId':PROVIDER_ID,'date':date,'length':100})
  full=next((u for u in existing if parse_start(u)<=f'{date} 00:00:00' and parse_end(u)>=f'{date} 23:59:00'),None) if isinstance(existing,list) else None
  if full:created=full
  else:
   mutation_started=True;created=await ea(request,'POST','/unavailabilities',json={'start':f'{date} 00:00:00','end':f'{date} 23:59:59','notes':f'Bloqueado por Ana vía WhatsApp. Motivo: {reason}','providerId':PROVIDER_ID})
  unavailability_id=int((created or {}).get('id') or 0)
  if not unavailability_id:raise HTTPException(502,'EasyAppointments no devolvió el ID de la indisponibilidad.')
  verified=await ea(request,'GET',f'/unavailabilities/{unavailability_id}')
  verified_provider=nested_id(verified or {},'provider','providerId')
  record_ok=int((verified or {}).get('id') or 0)==unavailability_id and verified_provider==PROVIDER_ID and parse_start(verified)==f'{date} 00:00:00' and parse_end(verified)>=f'{date} 23:59:00'
  catalog=await ea(request,'GET','/services',params={'length':1000})
  service_ids=sorted({int(s['id']) for s in catalog if isinstance(s,dict) and s.get('id')}) if isinstance(catalog,list) else []
  if not service_ids:raise HTTPException(502,'No se pudo verificar el catálogo activo de servicios.')
  availability_checks=[]
  for service_id in service_ids:
   slots=await ea(request,'GET','/availabilities',params={'providerId':PROVIDER_ID,'serviceId':service_id,'date':date})
   availability_checks.extend(slots if isinstance(slots,list) else [])
  if not record_ok or availability_checks:
   out={'ok':False,'blocked':True,'verified':False,'error':'day_block_verification_failed','unavailability_id':unavailability_id,'message':'La indisponibilidad pudo haberse creado, pero la agenda todavía devolvió disponibilidad. No se contactó a pacientes y requiere revisión.'};finish_mutation(claim_key,out);audit(x.message_id,'day_block',x.role,False,'created_unverified',out,payload);return out
  remote_verified=True
  now=datetime.now(TZ).isoformat();c=db();c.execute('BEGIN IMMEDIATE')
  c.execute('''INSERT INTO day_blocks(provider_id,block_date,reason,unavailability_id,owner_number,status,created_at,verified_at)
   VALUES(?,?,?,?,?,'verified',?,?) ON CONFLICT(provider_id,block_date) DO UPDATE SET reason=excluded.reason,unavailability_id=excluded.unavailability_id,owner_number=excluded.owner_number,status='verified',verified_at=excluded.verified_at''',(PROVIDER_ID,date,reason,unavailability_id,digits(x.requester_phone),now,now))
  block_id=c.execute('SELECT id FROM day_blocks WHERE provider_id=? AND block_date=?',(PROVIDER_ID,date)).fetchone()[0]
  for row in rows:
   phone=customer_phone(row);status='queued' if phone else 'missing_phone';text=outreach_text(row,reason)
   fp=json.dumps(appointment_fingerprint(row),ensure_ascii=False,sort_keys=True)
   c.execute('''INSERT INTO rebooking_campaigns(block_id,appointment_id,patient_name,patient_phone,service_name,service_id,original_start,original_end,status,outreach_text,original_fingerprint_json,created_at,updated_at)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(block_id,appointment_id) DO UPDATE SET patient_name=excluded.patient_name,patient_phone=excluded.patient_phone,service_name=excluded.service_name,service_id=excluded.service_id,original_start=excluded.original_start,original_end=excluded.original_end,status=CASE WHEN rebooking_campaigns.status='rescheduled' THEN 'rescheduled' ELSE excluded.status END,outreach_text=excluded.outreach_text,original_fingerprint_json=excluded.original_fingerprint_json,updated_at=excluded.updated_at''',(block_id,int(row['id']),person(row),phone,svc(row),appointment_service_id(row),parse_start(row),parse_end(row),status,text,fp,now,now))
  c.commit();c.close();consume_pending_day_block(pending['proposal_id'])
  summary=day_block_summary(date,reason,rows)
  out={'ok':True,'dry_run':False,'blocked':True,'verified':True,'date':date,'reason':reason,'unavailability_id':unavailability_id,'block_id':block_id,'appointment_count':summary['appointment_count'],'queued_contact_count':summary['contactable_count'],'missing_phone_count':summary['missing_phone_count'],'missing_phone':summary['missing_phone'],'message':'El día quedó bloqueado y verificado. Los contactos con teléfono quedaron en la cola segura; los casos sin teléfono deben informarse claramente a Ana.'};finish_mutation(claim_key,out);audit(x.message_id,'day_block',x.role,False,'success',out,payload);return out
 except HTTPException as e:
  out={'ok':False,'blocked':bool(locals().get('unavailability_id')),'verified':False,'error':'day_block_update_uncertain' if mutation_started else 'day_block_failed','unavailability_id':locals().get('unavailability_id'),'message':'El bloqueo pudo haberse iniciado y requiere revisión manual.' if mutation_started else e.detail}
  if mutation_started:finish_mutation(claim_key,out)
  else:release_mutation(claim_key)
  audit(x.message_id,'day_block',x.role,False,'error',out,payload);return out
 except Exception:
  proven=bool(locals().get('unavailability_id'))
  out={'ok':False,'blocked':proven,'verified':remote_verified,'error':'verified_tracking_failed' if remote_verified else 'blocked_unknown','unavailability_id':locals().get('unavailability_id'),'message':'El día pudo haber quedado bloqueado, pero no se pudo preparar el seguimiento. No se contactó a pacientes y Ana debe revisar el bloqueo.'}
  try:finish_mutation(claim_key,out)
  except Exception:pass
  try:audit(x.message_id,'day_block',x.role,False,'created_unverified' if proven else 'error',out,payload)
  except Exception:pass
  return out

class RescheduleIn(BaseModel):
 role:Literal['admin','patient'];requester_phone:str='';message_id:str;dry_run:bool=False
 date:Optional[str]=None;time:Optional[str]=None;original_date:Optional[str]=None;appointment_id:Optional[int]=None

def pending_campaigns_for(phone,appointment_id=None,original_date=None,readonly=False):
 candidates=phone_candidates(phone)
 if not candidates:return []
 placeholders=','.join('?' for _ in candidates);params:list[object]=list(candidates)
 sql=f'''SELECT r.id,r.appointment_id,r.patient_name,r.patient_phone,r.service_name,r.service_id,r.original_start,r.original_end,r.status,d.block_date,d.reason
 FROM rebooking_campaigns r JOIN day_blocks d ON d.id=r.block_id
 WHERE r.patient_phone IN ({placeholders}) AND r.status IN ('queued','contacted','send_failed')'''
 if appointment_id:sql+=' AND r.appointment_id=?';params.append(int(appointment_id))
 if original_date:sql+=' AND substr(r.original_start,1,10)=?';params.append(original_date)
 sql+=' ORDER BY r.id DESC'
 c=db(readonly=readonly);rows=c.execute(sql,params).fetchall();c.close()
 return [{'campaign_id':r[0],'appointment_id':r[1],'patient':r[2],'phone':r[3],'service':r[4],'service_id':r[5],'original_start':r[6],'original_end':r[7],'status':r[8],'blocked_date':r[9],'reason':r[10]} for r in rows]

@app.post('/v1/reschedule')
async def reschedule_tool(x:RescheduleIn,request:Request):
 auth_headers(request)
 payload=x.model_dump()
 try:await validate_ea_auth(request)
 except HTTPException:
  out={'ok':False,'confirmed':False,'error':'authentication_failed','message':'No se pudo validar el acceso a la agenda.'};audit(x.message_id,'reschedule',x.role,x.dry_run,'denied',out,payload);return out
 cached=prior(x.message_id,'reschedule',payload,readonly=x.dry_run)
 if cached:return cached
 campaigns=pending_campaigns_for(x.requester_phone,x.appointment_id,x.original_date,readonly=x.dry_run)
 if not campaigns:
  out={'ok':False,'confirmed':False,'error':'no_pending_rebooking','message':'No encontré una reagendación pendiente asociada a este número.'};audit(x.message_id,'reschedule',x.role,x.dry_run,'denied',out,payload);return out
 if len(campaigns)>1:
  out={'ok':False,'confirmed':False,'error':'ambiguous_pending_rebooking','pending':[{'appointment_id':c['appointment_id'],'original_start':c['original_start'],'service':c['service']} for c in campaigns],'message':'Hay más de un turno pendiente. Pedí cuál fecha original quiere mover.'};audit(x.message_id,'reschedule',x.role,x.dry_run,'denied',out,payload);return out
 campaign=campaigns[0]
 try:appt=await ea(request,'GET',f"/appointments/{campaign['appointment_id']}")
 except HTTPException as e:
  out={'ok':False,'confirmed':False,'error':'original_appointment_unavailable','message':e.detail};audit(x.message_id,'reschedule',x.role,x.dry_run,'error',out,payload);return out
 original_fp=appointment_fingerprint(appt)
 same_patient=bool(set(phone_candidates(customer_phone(appt))) & set(phone_candidates(campaign['phone'])))
 if parse_start(appt)[:16]!=campaign['original_start'][:16] or parse_end(appt)[:16]!=campaign['original_end'][:16] or original_fp['providerId']!=PROVIDER_ID or original_fp['serviceId']!=int(campaign['service_id']) or not same_patient or 'cancel' in original_fp['status'].lower():
  out={'ok':False,'confirmed':False,'error':'original_appointment_changed','message':'El turno original cambió desde que se inició la reagendación. Requiere revisión de Ana.'};audit(x.message_id,'reschedule',x.role,x.dry_run,'error',out,payload);return out
 s=service_for(campaign['service'],campaign['service_id'])
 if not s:
  out={'ok':False,'confirmed':False,'error':'unknown_service','message':'No pude identificar la duración del turno original.'};audit(x.message_id,'reschedule',x.role,x.dry_run,'error',out,payload);return out
 base={'ok':True,'operation':'pending_rebooking','appointment_id':campaign['appointment_id'],'patient':campaign['patient'],'service':campaign['service'],'original_start':campaign['original_start'],'blocked_date':campaign['blocked_date']}
 if not x.date:
  out={**base,'confirmed':False,'needs':['date'],'message':'Pedile al paciente qué día le conviene.'};audit(x.message_id,'reschedule',x.role,x.dry_run,'success',out,payload);return out
 if not valid_future_date(x.date):
  out={**base,'ok':False,'confirmed':False,'error':'invalid_date','message':'La nueva fecha no puede estar en el pasado.'};audit(x.message_id,'reschedule',x.role,x.dry_run,'denied',out,payload);return out
 try:available=await safe_availability(request,s,x.date,None,3)
 except HTTPException as e:
  out={**base,'ok':False,'confirmed':False,'error':'calendar_unavailable','message':e.detail};audit(x.message_id,'reschedule',x.role,x.dry_run,'error',out,payload);return out
 if not x.time:
  out={**base,'confirmed':False,'date':x.date,'slots':available['slots'],'duration_minutes':s['duration'],'message':'Mostrá estas opciones reales y pedí que elija una.'};audit(x.message_id,'reschedule',x.role,x.dry_run,'success',out,payload);return out
 wanted=x.time[:5]
 if not any((str(v)[11:16] if len(str(v))>=16 else str(v)[:5])==wanted for v in available['slots']):
  out={**base,'ok':False,'confirmed':False,'error':'slot_unavailable','date':x.date,'time':wanted,'alternatives':available['slots'],'message':'Ese horario ya no está disponible. Ofrecé únicamente las alternativas devueltas.'};audit(x.message_id,'reschedule',x.role,x.dry_run,'denied',out,payload);return out
 start=datetime.strptime(f'{x.date} {wanted}','%Y-%m-%d %H:%M').replace(tzinfo=TZ);end=start+timedelta(minutes=s['duration'])
 if x.dry_run:
  return {**base,'dry_run':True,'confirmed':False,'verified':False,'would_reschedule':{'from':campaign['original_start'],'to':start.strftime('%Y-%m-%d %H:%M:%S'),'end':end.strftime('%Y-%m-%d %H:%M:%S')}}
 claim_key=f"reschedule_campaign:{campaign['campaign_id']}";claim_payload={'campaign_id':campaign['campaign_id'],'appointment_id':campaign['appointment_id'],'original':original_fp,'new_start':start.strftime('%Y-%m-%d %H:%M:%S'),'new_end':end.strftime('%Y-%m-%d %H:%M:%S')}
 claim=claim_mutation(claim_key,claim_payload)
 if claim['state']=='completed':return claim['result']
 if claim['state']=='conflict':
  out={**base,'ok':False,'confirmed':False,'verified':False,'error':'idempotency_conflict','message':'Ya hay otro cambio en curso o completado para este turno. Consultá el estado antes de seguir.'};audit(x.message_id,'reschedule',x.role,False,'conflict',out,payload);return out
 if claim['state']=='in_progress':
  out={**base,'ok':False,'confirmed':False,'verified':False,'error':'operation_in_progress','message':'La reagendación ya está en curso. No la vuelvas a intentar todavía.'};audit(x.message_id,'reschedule',x.role,False,'pending',out,payload);return out
 mutation_started=False
 try:
  before=await ea(request,'GET',f"/appointments/{campaign['appointment_id']}")
  if appointment_fingerprint(before)!=original_fp:
   release_mutation(claim_key);out={**base,'ok':False,'confirmed':False,'verified':False,'error':'original_appointment_changed','message':'El turno cambió antes de guardar. Requiere revisión de Ana.'};audit(x.message_id,'reschedule',x.role,False,'conflict',out,payload);return out
  latest=await ea(request,'GET','/appointments',params={'providerId':PROVIDER_ID,'aggregates':'1','date':x.date,'length':1000})
  latest=[a for a in latest if int(a.get('id') or 0)!=campaign['appointment_id']] if isinstance(latest,list) else []
  if active_overlaps(latest,start,end):
   release_mutation(claim_key);out={**base,'ok':False,'confirmed':False,'error':'slot_conflict_changed','message':'El horario se ocupó antes de guardar. Pedí otra opción.'};audit(x.message_id,'reschedule',x.role,False,'occupied',out,payload);return out
  update_payload=appointment_payload_for_update(before,start,end)
  mutation_started=True;await ea(request,'PUT',f"/appointments/{campaign['appointment_id']}",json=update_payload)
  verified=await ea(request,'GET',f"/appointments/{campaign['appointment_id']}")
  expected={**appointment_fingerprint(before),'start':start.strftime('%Y-%m-%d %H:%M:%S'),'end':end.strftime('%Y-%m-%d %H:%M:%S')};verified_fp=appointment_fingerprint(verified)
  after_rows=await ea(request,'GET','/appointments',params={'providerId':PROVIDER_ID,'aggregates':'1','date':x.date,'length':1000})
  after_others=[a for a in after_rows if int(a.get('id') or 0)!=campaign['appointment_id']] if isinstance(after_rows,list) else []
  verified_ok=verified_fp==expected and not active_overlaps(after_others,start,end)
  if not verified_ok:
   rollback_payload=appointment_payload_from_snapshot(appointment_fingerprint(before))
   await ea(request,'PUT',f"/appointments/{campaign['appointment_id']}",json=rollback_payload)
   rolled_back=await ea(request,'GET',f"/appointments/{campaign['appointment_id']}");rollback_ok=appointment_fingerprint(rolled_back)==appointment_fingerprint(before)
   if rollback_ok:
    release_mutation(claim_key);out={**base,'ok':False,'confirmed':False,'verified':False,'rolled_back':True,'error':'reschedule_verification_failed_rolled_back','message':'El cambio no se pudo verificar y el turno original fue restaurado y verificado. Pedí otra opción.'};audit(x.message_id,'reschedule',x.role,False,'rolled_back',out,payload);return out
   out={**base,'ok':False,'confirmed':False,'verified':False,'rolled_back':False,'error':'rollback_failed_manual_intervention','message':'El resultado de la reagendación es incierto y el rollback no pudo verificarse. No confirmes nada y avisá a Ana.'};finish_mutation(claim_key,out);audit(x.message_id,'reschedule',x.role,False,'update_uncertain',out,payload);return out
  now=datetime.now(TZ).isoformat();c=db();c.execute("UPDATE rebooking_campaigns SET status='rescheduled',new_start=?,new_end=?,updated_at=?,last_error=NULL WHERE id=?",(start.strftime('%Y-%m-%d %H:%M:%S'),end.strftime('%Y-%m-%d %H:%M:%S'),now,campaign['campaign_id']));c.commit();c.close()
  out={**base,'dry_run':False,'confirmed':True,'verified':True,'new_start':start.strftime('%Y-%m-%d %H:%M:%S'),'new_end':end.strftime('%Y-%m-%d %H:%M:%S'),'message':'El mismo turno fue movido y verificado; no se canceló ni se creó un duplicado.'};finish_mutation(claim_key,out);audit(x.message_id,'reschedule',x.role,False,'success',out,payload);return out
 except HTTPException as e:
  if not mutation_started:
   release_mutation(claim_key);out={**base,'ok':False,'confirmed':False,'verified':False,'error':'reschedule_failed','message':e.detail}
  else:
   out={**base,'ok':False,'confirmed':False,'verified':False,'error':'reschedule_update_uncertain','message':'EasyAppointments falló después de iniciar el cambio. No lo reintentes ni lo confirmes; avisá a Ana.'};finish_mutation(claim_key,out)
  audit(x.message_id,'reschedule',x.role,False,'update_uncertain' if mutation_started else 'error',out,payload);return out
 except Exception:
  out={**base,'ok':False,'confirmed':False,'verified':False,'error':'reschedule_tracking_failed','message':'El turno pudo haberse movido, pero no se pudo registrar el resultado. No lo reintentes y avisá a Ana.'}
  try:finish_mutation(claim_key,out)
  except Exception:pass
  try:audit(x.message_id,'reschedule',x.role,False,'update_uncertain',out,payload)
  except Exception:pass
  return out
