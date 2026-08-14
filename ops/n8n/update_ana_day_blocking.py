#!/usr/bin/env python3
"""Add safe day blocking and rebooking tools to AnaAgentFinalV1.

The transform is idempotent and can run against an exported workflow for review.
With --apply it backs up the current workflow, updates it through the n8n API,
and leaves activation unchanged. Secrets are read but never printed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import urllib.request

WORKFLOW_ID = "AnaAgentFinalV1"
DAY_BLOCK_NODE = "gestionar_bloqueo_dia"
RESCHEDULE_NODE = "reagendar_turno_bloqueo"


def load_env() -> dict[str, str]:
    values = dict(os.environ)
    for path in (
        pathlib.Path.home() / ".config/openclaw/n8n-api.env",
        pathlib.Path.home() / ".openclaw/workspace/.n8n-api-config",
    ):
        if not path.exists():
            continue
        for raw in path.read_text(errors="ignore").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values.setdefault(key.strip(), value.strip().strip("\"'"))
    return values


def api_request(method: str, url: str, key: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"X-N8N-API-KEY": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def node(workflow: dict, name: str) -> dict:
    return next(item for item in workflow["nodes"] if item.get("name") == name)


def add_tool_nodes(workflow: dict) -> None:
    credential = node(workflow, "agendar_turno").get("credentials", {})
    workflow["nodes"] = [
        item for item in workflow["nodes"] if item.get("name") not in (DAY_BLOCK_NODE, RESCHEDULE_NODE)
    ]
    workflow["nodes"].extend(
        [
            {
                "parameters": {
                    "toolDescription": (
                        "Bloquea una fecha completa sólo para Ana. Siempre usar action=preview primero: "
                        "consulta turnos, separa pacientes con/sin teléfono y exige mostrar el resumen. "
                        "Sólo después de una confirmación explícita nueva usar action=confirm con confirmed=true. "
                        "Si los turnos cambiaron exige otra confirmación. action=status consulta el seguimiento. "
                        "No afirmar bloqueo salvo blocked=true, verified=true y dry_run=false."
                    ),
                    "method": "POST",
                    "url": "http://ana-agent-tools:8081/v1/day-block",
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpBasicAuth",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": (
                        "={{ { action:$fromAI('action','preview para revisar; confirm sólo después de confirmación explícita de Ana; status para seguimiento','string'), "
                        "role:$json.actor_role, requester_phone:$json.original_number, message_id:$json.message_id, event_timestamp:Number($json.current_message_timestamp||((($json.body||$json).data||($json.body||$json)).messageTimestamp)||0), dry_run:$json.dry_run===true, "
                        "date:$fromAI('date','YYYY-MM-DD o vacío para confirmar el bloqueo pendiente','string',''), "
                        "reason:$fromAI('reason','Motivo breve del bloqueo o vacío','string',''), "
                        "confirmed:$fromAI('confirmed','true sólo si Ana confirmó explícitamente la vista previa vigente','boolean',false), "
                        "proposal_id:$fromAI('proposal_id','UUID exacto devuelto por la vista previa; obligatorio para confirm','string',''), "
                        "override_authorized:$json.actor_role==='admin' && String($json.original_number||'').replace(/\\D/g,'')===String($json.ana_config?.ana_notify_number||'').replace(/\\D/g,'') } }}"
                    ),
                    "options": {"timeout": 30000},
                    "optimizeResponse": True,
                },
                "id": "cc693ab8-6f7b-4575-a8a6-0b25dd87ab01",
                "name": DAY_BLOCK_NODE,
                "type": "n8n-nodes-base.httpRequestTool",
                "typeVersion": 4.4,
                "position": [4768, 432],
                "credentials": credential,
            },
            {
                "parameters": {
                    "toolDescription": (
                        "Gestiona la reagendación pendiente generada por un bloqueo. Para un paciente que responde "
                        "al aviso, llamar primero aunque todavía no haya fecha: devuelve el turno pendiente. Con fecha "
                        "sin hora devuelve hasta tres opciones reales; con fecha y hora actualiza y verifica el mismo turno. "
                        "No cancela ni crea duplicados. Sólo confirmar el cambio con confirmed=true, verified=true y dry_run=false."
                    ),
                    "method": "POST",
                    "url": "http://ana-agent-tools:8081/v1/reschedule",
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpBasicAuth",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": (
                        "={{ { role:$json.actor_role, requester_phone:$json.original_number, message_id:$json.message_id, dry_run:$json.dry_run===true, "
                        "date:$fromAI('date','Nueva fecha YYYY-MM-DD o vacío','string',''), time:$fromAI('time','Nueva hora HH:MM o vacío','string',''), "
                        "original_date:$fromAI('original_date','Fecha original YYYY-MM-DD sólo si hay más de un turno pendiente','string',''), "
                        "appointment_id:$fromAI('appointment_id','ID exacto sólo si la herramienta informó más de uno','number',null) } }}"
                    ),
                    "options": {"timeout": 30000},
                    "optimizeResponse": True,
                },
                "id": "bf4399f2-cb84-4c94-a9cb-d0672ddf99df",
                "name": RESCHEDULE_NODE,
                "type": "n8n-nodes-base.httpRequestTool",
                "typeVersion": 4.4,
                "position": [4928, 512],
                "credentials": credential,
            },
        ]
    )
    workflow.setdefault("connections", {})[DAY_BLOCK_NODE] = {
        "ai_tool": [[{"node": "Agente Ana con herramientas", "type": "ai_tool", "index": 0}]]
    }
    workflow["connections"][RESCHEDULE_NODE] = {
        "ai_tool": [[{"node": "Agente Ana con herramientas", "type": "ai_tool", "index": 0}]]
    }


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"No se encontró el ancla para {label}")
    return text.replace(old, new, 1)


def update_prompts(workflow: dict) -> None:
    context = node(workflow, "Preparar contexto agente directo")
    code = context["parameters"]["jsCode"]
    patient_old = (
        "- La cancelación o reprogramación final debe revisarla Ana. No uses `cancelar_turno` en modo paciente."
    )
    patient_new = """- Si el paciente responde a un aviso de cierre/bloqueo para mover su turno, usá `reagendar_turno_bloqueo` antes de responder, aunque todavía no haya elegido fecha. La herramienta identifica únicamente pendientes vinculados a su número.
- Si un paciente envía sólo una preferencia breve de día/hora (por ejemplo “martes a la tarde” o “el jueves a las 16”) y el contexto no es claro, consultá primero `reagendar_turno_bloqueo` sin inventar el motivo. Si devuelve `no_pending_rebooking`, seguí con el flujo normal de disponibilidad.
- Si devuelve `needs: [date]`, pedí el día o rango que le conviene. Con fecha y sin hora, volvé a usarla y ofrecé únicamente `slots`. Con fecha y hora elegidas, volvé a usarla para mover el mismo turno.
- Confirmá una reagendación sólo con `ok=true`, `confirmed=true`, `verified=true`, `dry_run=false` y `new_start`. Si falla la verificación, explicá que necesita revisión de Ana.
- Para pedidos de reprogramación que no provienen de una campaña de bloqueo, mantené el flujo de revisión de Ana y no uses `cancelar_turno` en modo paciente."""
    code = replace_once(code, patient_old, patient_new.replace("\n", "\\n"), "prompt paciente")
    admin_old = (
        "- Reprogramar implica dos cambios sensibles. No canceles el turno original ni crees uno nuevo sin identificar ambos horarios y obtener confirmación explícita. Si el flujo no puede completar ambos de forma segura, informá que requiere revisión manual."
    )
    admin_new = """- Para bloquear un día completo usá `gestionar_bloqueo_dia` con `action=preview`. Mostrá fecha, motivo, cantidad de turnos, cuántos tienen teléfono, el detalle de cada turno sin teléfono y el `proposal_id` exacto como código de vista previa. Aclarale que todavía no se cambió nada y pedí confirmación explícita.
- Sólo después de esa confirmación usá `action=confirm`, `confirmed=true` y copiá exactamente el `proposal_id` devuelto por la vista previa. Nunca confirmes sin ese UUID ni elijas otra propuesta. Si los turnos cambiaron desde la vista previa, mostrá el nuevo resumen y pedí una confirmación nueva.
- Confirmá que el día quedó bloqueado únicamente con `blocked=true`, `verified=true`, `dry_run=false` y `unavailability_id`. No digas que ya se enviaron mensajes: informá que los contactos quedaron en curso. El proceso de salida enviará luego a Ana un resumen verificable.
- Si `missing_phone` contiene turnos, decile claramente a Ana que no se pueden reagendar automáticamente porque no hay número de teléfono; incluí paciente, hora y servicio.
- `action=status` permite consultar cuántos pacientes fueron contactados, reagendados o requieren revisión.
- Para pacientes incluidos en una campaña de bloqueo, `reagendar_turno_bloqueo` actualiza el mismo turno con controles pre/post y rollback verificado ante inconsistencias. No uses cancelar + crear. Confirmá el cambio sólo con `confirmed=true`, `verified=true` y `new_start`.
- Para reprogramaciones ajenas a un bloqueo, no canceles el turno original ni crees uno nuevo sin identificar ambos horarios y obtener confirmación explícita. Si no hay una operación segura aplicable, requiere revisión manual."""
    code = replace_once(code, admin_old, admin_new.replace("\n", "\\n"), "prompt administrador")
    context["parameters"]["jsCode"] = code


def update_validator(workflow: dict) -> None:
    validator = node(workflow, "Validar respuesta y evidencia")
    code = validator["parameters"]["jsCode"]
    runs_old = "const runs=Array.isArray(e.runs)?e.runs:[],missingRun="
    runs_new = """const runs=Array.isArray(e.runs)?e.runs:[];
const dayBlockRun=[...runs].reverse().find(x=>x.tool==='day_block');
const rescheduleRun=[...runs].reverse().find(x=>x.tool==='reschedule');
const missingRun="""
    code = replace_once(code, runs_old, runs_new, "evidencia de herramientas")
    marker = "const positivePaymentClaim="
    enforcement = r"""const formatBlockDate=value=>{const s=String(value||'');return s.length>=10?s.slice(8,10)+'/'+s.slice(5,7)+'/'+s.slice(0,4):s;};
if(dayBlockRun?.result?.operation==='preview'||dayBlockRun?.result?.error==='day_block_conflicts_changed_confirmation_required'){
 const x=dayBlockRun.result,missing=Array.isArray(x.missing_phone)?x.missing_phone:[];
 r=`Vista previa para bloquear el ${formatBlockDate(x.date)}${x.reason?' ('+x.reason+')':''}:\n\n- Turnos existentes: ${x.appointment_count||0}\n- Con teléfono: ${x.contactable_count||0}\n- Sin teléfono: ${x.missing_phone_count||0}`;
 if(missing.length)r+='\n\nNo voy a poder reagendar automáticamente estos turnos porque no tienen número de teléfono:\n'+missing.map(m=>`- ${String(m.start||'').slice(11,16)} — ${m.patient||'Paciente'} (${m.service||'Turno'})`).join('\n');
 if(x.proposal_id)r+=`\n\nCódigo de vista previa: ${x.proposal_id}`;
 r+='\n\nTodavía no bloqueé el día ni contacté a nadie. Si confirmás explícitamente, bloqueo la fecha e inicio los contactos posibles.';
}
if(dayBlockRun?.result?.ok===true&&dayBlockRun.result.blocked===true&&dayBlockRun.result.verified===true&&dayBlockRun.result.dry_run===false){
 const x=dayBlockRun.result,missing=Array.isArray(x.missing_phone)?x.missing_phone:[];
 r=`El ${formatBlockDate(x.date)} quedó bloqueado y verificado. Encontré ${x.appointment_count||0} turnos; dejé en curso el contacto de ${x.queued_contact_count||0} pacientes con teléfono.`;
 if(missing.length)r+='\n\nNo puedo reagendar automáticamente estos turnos porque no tienen número de teléfono:\n'+missing.map(m=>`- ${String(m.start||'').slice(11,16)} — ${m.patient||'Paciente'} (${m.service||'Turno'})`).join('\n');
 r+='\n\nTe llegará un resumen cuando termine el intento de contacto.';
}
if(dayBlockRun?.result?.dry_run===true&&dayBlockRun.result.would_block){
 const x=dayBlockRun.result;r=`Prueba realizada: se habría bloqueado el ${formatBlockDate(x.would_block.date)} y puesto en curso ${x.would_queue_contacts||0} contactos, pero no se modificó la agenda ni se envió ningún mensaje.`;
}
const positiveBlockClaim=/(bloque[eé]\s+(?:el\s+)?d[ií]a|(?:d[ií]a|fecha|jornada).{0,35}(qued[oó]|est[aá]|fue).{0,25}(bloquead|cerrad|indisponible))/i.test(r)&&!/(todav[ií]a no|a[uú]n no|no se).{0,30}(bloque|cerr|marc).{0,20}(d[ií]a|fecha|jornada)/i.test(r);
const blockEvidence=dayBlockRun?.result?.ok===true&&dayBlockRun.result.blocked===true&&dayBlockRun.result.verified===true&&dayBlockRun.result.dry_run===false;
if(positiveBlockClaim&&!blockEvidence&&!b.dry_run)r='Todavía no pude confirmar que el día haya quedado bloqueado en la agenda.';
if(rescheduleRun?.result?.ok===true&&rescheduleRun.result.confirmed===true&&rescheduleRun.result.verified===true&&rescheduleRun.result.dry_run===false){
 const x=rescheduleRun.result,st=String(x.new_start||''),d=formatBlockDate(st.slice(0,10)),h=st.slice(11,16);r=`Listo, moví y verifiqué el mismo turno para el ${d} a las ${h}. El turno original no fue cancelado por separado ni se creó un duplicado.`;
}
if(rescheduleRun?.result?.dry_run===true&&rescheduleRun.result.would_reschedule){
 const x=rescheduleRun.result;r=`Prueba realizada: se habría movido el mismo turno a ${x.would_reschedule.to}, pero no se modificó la agenda ni se envió ningún mensaje.`;
}
const positiveRescheduleClaim=/(turno|reserva).{0,35}(reagendad|reprogramad|movid)|(?:reagend[eé]|reprogram[eé]|mov[ií])\s+(?:el\s+)?turno/i.test(r);
const rescheduleEvidence=rescheduleRun?.result?.ok===true&&rescheduleRun.result.confirmed===true&&rescheduleRun.result.verified===true&&rescheduleRun.result.dry_run===false;
if(positiveRescheduleClaim&&!rescheduleEvidence&&!b.dry_run)r='Todavía no pude confirmar la reagendación en la agenda.';
"""
    if enforcement not in code:
        if marker not in code:
            raise RuntimeError("No se encontró el ancla del validador")
        code = code.replace(marker, enforcement + marker, 1)
    validator["parameters"]["jsCode"] = code


def transform(workflow: dict) -> dict:
    add_tool_nodes(workflow)
    update_prompts(workflow)
    update_validator(workflow)
    config = node(workflow, "Configurar testing y avisos")
    config["parameters"]["jsCode"] = config["parameters"]["jsCode"].replace(
        "version: 'v1.0-production-ana'", "version: 'v1.1-day-blocking-rebooking'"
    )
    return workflow


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    env = load_env()
    if args.apply:
        base = (env.get("N8N_API_URL") or env.get("N8N_URL") or "http://127.0.0.1:5678").rstrip("/")
        if not base.endswith("/api/v1"):
            base += "/api/v1"
        key = env.get("N8N_API_KEY", "")
        if not key:
            raise SystemExit("Falta N8N_API_KEY")
        workflow = api_request("GET", f"{base}/workflows/{WORKFLOW_ID}", key)
        backup_dir = pathlib.Path.home() / "backups" / f"ana-day-block-{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup_dir.chmod(0o700)
        backup_file = backup_dir / "workflow-before.json"
        backup_file.write_text(json.dumps(workflow, ensure_ascii=False, indent=2))
        backup_file.chmod(0o600)
        transformed = transform(workflow)
        payload = {key_name: transformed[key_name] for key_name in ("name", "nodes", "connections", "settings") if key_name in transformed}
        result = api_request("PUT", f"{base}/workflows/{WORKFLOW_ID}", key, payload)
        print(json.dumps({"updated": result.get("id") == WORKFLOW_ID, "active": result.get("active"), "backup": str(backup_dir / 'workflow-before.json'), "nodes": len(result.get("nodes", []))}))
        return 0
    if not args.input or not args.output:
        parser.error("Usá --input y --output, o --apply")
    workflow = json.loads(args.input.read_text())
    transformed = transform(workflow)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(transformed, ensure_ascii=False, indent=2))
    print(json.dumps({"output": str(args.output), "nodes": len(transformed["nodes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
