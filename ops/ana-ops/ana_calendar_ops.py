#!/usr/bin/env python3
"""
Ana calendar/reminder operations.

Modes:
  sync                    Run EasyAppointments -> Google/Google -> EA native sync.
  send-reminders           Send day-before WhatsApp confirmation reminders.
  alert-no-response        Alert Ana for pending confirmations not answered by cutoff.
  dry-run-all              Run sync + reminder + no-response in dry-run mode.
  process-rebooking-outreach Send queued day-block contacts and alert Ana.

Security: this script reads secrets from local env files but never prints them.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

EA_DIR = Path(os.environ.get("EA_DIR", "/home/salini/research/repos/easyappointments"))
N8N_PG_CONTAINER = os.environ.get("N8N_PG_CONTAINER", "n8n-postgres")
N8N_DB_USER = os.environ.get("N8N_DB_USER", "n8n")
N8N_DB_NAME = os.environ.get("N8N_DB_NAME", "n8n")
EVOLUTION_DIR = Path(os.environ.get("EVOLUTION_DIR", "/opt/nolapenses/evolution"))
EVOLUTION_URL = os.environ.get("EVOLUTION_URL", "http://127.0.0.1:8080")
EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "Ana-Maldonado")
ANA_ALERT_JID = os.environ.get("ANA_ALERT_JID", "")  # Prefer exact inbound @lid when known.
ANA_ALERT_NUMBER = re.sub(r"\D", "", os.environ.get("ANA_ALERT_NUMBER", "5492665068339"))
REMINDER_CUTOFF_HOUR = int(os.environ.get("ANA_REMINDER_NO_RESPONSE_CUTOFF_HOUR", "18"))
TOOLS_DB = Path(os.environ.get("ANA_TOOLS_DB", "/opt/nolapenses/ana-agent-tools/data/ana_tools.db"))
TZ = dt.timezone(dt.timedelta(hours=-3), name="America/Argentina/Buenos_Aires")

REMINDER_TYPE = "day_before_confirmation"

REMINDER_TEXT = """Estimado paciente, te recuerdo tu turno de mañana a las {hora} hs.
Es necesario que me envíes confirmación de asistencia por favor 🙏🏼 así de esta forma tu turno permanecerá agendado!

Lamentablemente de no recibir confirmación tu turno quedará libre para ser asignado a otro paciente.

Te agradezco tu comprensión 🌸
Te envío un cordial saludo 🙌🏽"""


def run(cmd: list[str], *, cwd: Path | None = None, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=check,
    )


def log(msg: str) -> None:
    print(f"[{dt.datetime.now(TZ).isoformat(timespec='seconds')}] {msg}")


def load_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def n8n_psql(sql: str) -> str:
    cp = run([
        "docker", "exec", "-i", N8N_PG_CONTAINER,
        "psql", "-U", N8N_DB_USER, "-d", N8N_DB_NAME, "-t", "-A", "-F", "\t", "-v", "ON_ERROR_STOP=1", "-c", sql,
    ])
    return cp.stdout


def ea_mysql(sql: str) -> str:
    shell = (
        "DB=${MYSQL_DATABASE:-easyappointments}; "
        "USER=${MYSQL_USER:-root}; "
        "PASS=${MYSQL_PASSWORD:-$MYSQL_ROOT_PASSWORD}; "
        "mysql --default-character-set=utf8mb4 -u\"$USER\" -p\"$PASS\" --batch --raw --skip-column-names \"$DB\""
    )
    cp = run(["docker", "compose", "exec", "-T", "mysql", "sh", "-lc", shell], cwd=EA_DIR, input_text=sql)
    return cp.stdout


def record_run(job: str, status: str, details: dict | None = None, error: str | None = None) -> None:
    details_json = json.dumps(details or {}, ensure_ascii=False).replace("'", "''")
    err = "NULL" if not error else "'" + error.replace("'", "''")[:2000] + "'"
    sql = f"INSERT INTO ana_ops_runs(job_name,status,finished_at,details,error) VALUES ('{job}','{status}',now(),'{details_json}'::jsonb,{err});"
    try:
        n8n_psql(sql)
    except Exception as e:
        log(f"WARN could not record run {job}: {e}")


def run_sync(dry_run: bool = False) -> int:
    log("starting EasyAppointments console sync")
    if dry_run:
        log("DRY-RUN sync: would run php index.php console sync")
        record_run("ea_google_sync", "dry_run", {"command": "php index.php console sync"})
        return 0
    cp = run(["docker", "compose", "exec", "-T", "php-fpm", "php", "index.php", "console", "sync"], cwd=EA_DIR, check=False)
    status = "ok" if cp.returncode == 0 else "error"
    details = {"returncode": cp.returncode, "stdout_tail": cp.stdout[-1000:]}
    record_run("ea_google_sync", status, details, cp.stderr[-2000:] if cp.returncode else None)
    if cp.returncode != 0:
        log("sync failed; stderr redacted-length=" + str(len(cp.stderr)))
    else:
        log("sync ok")
    return cp.returncode


def get_evolution_key() -> str:
    env = load_env_file(EVOLUTION_DIR / ".env")
    return env.get("AUTHENTICATION_API_KEY") or env.get("AUTHENTICATION_APIKEY") or env.get("API_KEY") or ""


def send_whatsapp(to: str, text: str, *, dry_run: bool = False) -> tuple[bool, str]:
    to = str(to).strip()
    if not to:
        return False, "missing_destination"
    if dry_run:
        return True, "dry_run"
    key = get_evolution_key()
    if not key:
        return False, "missing_evolution_key"
    url = f"{EVOLUTION_URL.rstrip('/')}/message/sendText/{EVOLUTION_INSTANCE}"
    payload = {"number": to, "text": text, "delay": 800, "linkPreview": False}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json", "apikey": key})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            body = r.read().decode(errors="replace")
            msg_id = ""
            try:
                obj = json.loads(body)
                msg_id = obj.get("key", {}).get("id") or obj.get("id") or obj.get("messageId") or "sent"
            except Exception:
                msg_id = "sent"
            return 200 <= r.status < 300, msg_id
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        return False, f"http_{e.code}:{body}"
    except Exception as e:
        return False, f"error:{type(e).__name__}"


def clean_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return ""
    if digits.startswith("549"):
        return digits
    if digits.startswith("54"):
        return digits
    # Argentina/San Luis local fallback; keep conservative.
    if len(digits) == 10 and digits.startswith("266"):
        return "549" + digits
    return digits


def blocklist_candidates(raw: str) -> list[str]:
    digits = clean_phone(raw)
    if not digits:
        return []
    candidates = {digits}
    if digits.startswith("549"):
        candidates.add("54" + digits[3:])
    elif digits.startswith("54"):
        candidates.add("549" + digits[2:])
    return sorted(candidates)


def blocked_contact(raw: str) -> bool:
    candidates = blocklist_candidates(raw)
    if not candidates:
        return False
    quoted = ",".join("'" + value + "'" for value in candidates)
    out = n8n_psql(
        "SELECT 1 FROM ana_bot_blocklist "
        f"WHERE active=true AND canonical_phone IN ({quoted}) LIMIT 1;"
    )
    return bool(out.strip())


def tomorrow_bounds() -> tuple[str, str]:
    now = dt.datetime.now(TZ)
    tomorrow = (now + dt.timedelta(days=1)).date()
    return f"{tomorrow} 00:00:00", f"{tomorrow} 23:59:59"


def fetch_tomorrow_appointments() -> list[dict]:
    start, end = tomorrow_bounds()
    sql = f"""
SELECT a.id, a.start_datetime, a.end_datetime, COALESCE(s.name,''), COALESCE(u.first_name,''), COALESCE(u.last_name,''), COALESCE(u.mobile_number,''), COALESCE(u.phone_number,''), COALESCE(u.custom_field_1,''), COALESCE(a.status,'')
FROM ea_appointments a
JOIN ea_users u ON u.id = a.id_users_customer
LEFT JOIN ea_services s ON s.id = a.id_services
WHERE a.is_unavailability = 0
  AND a.id_users_provider = 2
  AND a.start_datetime >= '{start}'
  AND a.start_datetime <= '{end}'
ORDER BY a.start_datetime;
"""
    rows = []
    for line in ea_mysql(sql).splitlines():
        cols = line.split("\t")
        if len(cols) < 10:
            continue
        aid, st, en, service, first, last, mobile, phone, dni, status = cols[:10]
        patient_phone = clean_phone(mobile or phone)
        rows.append({
            "appointment_id": int(aid), "start": st, "end": en, "service": service,
            "patient_name": (first + " " + last).strip(), "patient_phone": patient_phone,
            "dni": dni, "status": status,
        })
    return rows


def reminder_exists(appointment_id: int) -> bool:
    out = n8n_psql(f"SELECT 1 FROM ana_appointment_reminders WHERE appointment_id={appointment_id} AND reminder_type='{REMINDER_TYPE}' AND sent_at IS NOT NULL LIMIT 1;")
    return bool(out.strip())


def upsert_reminder(appt: dict, *, sent: bool, msg_id: str = "", error: str = "") -> None:
    patient_name = appt["patient_name"].replace("'", "''")
    service = appt["service"].replace("'", "''")
    phone = appt["patient_phone"].replace("'", "''")
    msg = msg_id.replace("'", "''")[:512]
    err = error.replace("'", "''")[:1500]
    status = "pending" if sent else "send_failed"
    sent_sql = "now()" if sent else "NULL"
    sql = f"""
INSERT INTO ana_appointment_reminders
(appointment_id, reminder_type, patient_phone, patient_name, appointment_start, appointment_end, service_name, status, sent_at, whatsapp_message_id, last_error, updated_at)
VALUES ({appt['appointment_id']}, '{REMINDER_TYPE}', '{phone}', '{patient_name}', '{appt['start']}', '{appt['end']}', '{service}', '{status}', {sent_sql}, '{msg}', '{err}', now())
ON CONFLICT (appointment_id, reminder_type) DO UPDATE SET
  patient_phone=EXCLUDED.patient_phone,
  patient_name=EXCLUDED.patient_name,
  appointment_start=EXCLUDED.appointment_start,
  appointment_end=EXCLUDED.appointment_end,
  service_name=EXCLUDED.service_name,
  status=CASE WHEN ana_appointment_reminders.status IN ('confirmed','cancelled') THEN ana_appointment_reminders.status ELSE EXCLUDED.status END,
  sent_at=COALESCE(ana_appointment_reminders.sent_at, EXCLUDED.sent_at),
  whatsapp_message_id=COALESCE(NULLIF(ana_appointment_reminders.whatsapp_message_id,''), EXCLUDED.whatsapp_message_id),
  last_error=EXCLUDED.last_error,
  updated_at=now();
"""
    n8n_psql(sql)


def send_reminders(dry_run: bool = False) -> int:
    # Always sync before reminder lookup.
    sync_rc = run_sync(dry_run=dry_run)
    if sync_rc != 0 and not dry_run:
        record_run("ana_day_before_reminders", "blocked", {"reason": "sync_failed"}, "sync_failed")
        return sync_rc
    appts = fetch_tomorrow_appointments()
    sent_count = 0
    skipped = 0
    blocked = 0
    failed = 0
    for appt in appts:
        if reminder_exists(appt["appointment_id"]):
            skipped += 1
            continue
        if not appt["patient_phone"]:
            failed += 1
            if not dry_run:
                upsert_reminder(appt, sent=False, error="missing_patient_phone")
            continue
        if blocked_contact(appt["patient_phone"]):
            blocked += 1
            continue
        start_dt = dt.datetime.strptime(appt["start"], "%Y-%m-%d %H:%M:%S")
        text = REMINDER_TEXT.format(hora=start_dt.strftime("%H:%M"))
        ok, msg_id = send_whatsapp(appt["patient_phone"], text, dry_run=dry_run)
        if ok:
            sent_count += 1
            if not dry_run:
                upsert_reminder(appt, sent=True, msg_id=msg_id)
        else:
            failed += 1
            if not dry_run:
                upsert_reminder(appt, sent=False, error=msg_id)
    details = {"appointments": len(appts), "sent": sent_count, "skipped": skipped, "blocked": blocked, "failed": failed, "dry_run": dry_run}
    record_run("ana_day_before_reminders", "ok" if failed == 0 else "partial", details)
    log(f"reminders done {details}")
    return 0 if failed == 0 else 2


def pending_no_response_rows() -> list[dict]:
    now = dt.datetime.now(TZ)
    if now.hour < REMINDER_CUTOFF_HOUR:
        return []
    sql = """
SELECT id, appointment_id, patient_phone, COALESCE(patient_name,''), appointment_start::text, COALESCE(service_name,'')
FROM ana_appointment_reminders
WHERE reminder_type='day_before_confirmation'
  AND status='pending'
  AND sent_at IS NOT NULL
  AND ana_alert_sent_at IS NULL
  AND appointment_start::date = (now() AT TIME ZONE 'America/Argentina/Buenos_Aires' + interval '1 day')::date
ORDER BY appointment_start;
"""
    rows = []
    for line in n8n_psql(sql).splitlines():
        cols = line.split("\t")
        if len(cols) < 6:
            continue
        rows.append({"id": int(cols[0]), "appointment_id": int(cols[1]), "phone": cols[2], "name": cols[3], "start": cols[4], "service": cols[5]})
    return rows


def alert_destination() -> str:
    return ANA_ALERT_JID.strip() or (ANA_ALERT_NUMBER + "@s.whatsapp.net" if ANA_ALERT_NUMBER else "")


def alert_no_response(dry_run: bool = False) -> int:
    rows = pending_no_response_rows()
    if not rows:
        record_run("ana_no_response_alert", "ok", {"pending": 0, "dry_run": dry_run})
        log("no pending no-response alerts")
        return 0
    lines = ["Ana, estos pacientes todavía no confirmaron el turno de mañana:", ""]
    for r in rows:
        t = dt.datetime.strptime(r["start"][:19], "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
        lines.append(f"• {t} — {r['name'] or 'Paciente'} ({r['service'] or 'turno'})")
    lines += ["", "Conviene revisarlos por si querés liberar o reacomodar esos horarios."]
    ok, msg_id = send_whatsapp(alert_destination(), "\n".join(lines), dry_run=dry_run)
    if ok:
        if not dry_run:
            ids = ",".join(str(r["id"]) for r in rows)
            n8n_psql(f"UPDATE ana_appointment_reminders SET ana_alert_sent_at=now(), updated_at=now() WHERE id IN ({ids});")
        record_run("ana_no_response_alert", "ok", {"pending": len(rows), "message_id": msg_id, "dry_run": dry_run})
        log(f"alerted Ana for {len(rows)} pending confirmations")
        return 0
    record_run("ana_no_response_alert", "error", {"pending": len(rows), "dry_run": dry_run}, msg_id)
    log("failed alerting Ana: " + msg_id[:120])
    return 3


def tools_db() -> sqlite3.Connection:
    connection = sqlite3.connect(TOOLS_DB, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=15000")
    return connection


def mark_outreach(campaign_id: int, status: str, *, message_id: str = "", error: str = "") -> None:
    connection = tools_db()
    connection.execute(
        "UPDATE rebooking_campaigns SET status=?, whatsapp_message_id=?, last_error=?, updated_at=? WHERE id=?",
        (status, message_id[:512] or None, error[:1500] or None, dt.datetime.now(TZ).isoformat(), campaign_id),
    )
    connection.commit()
    connection.close()


def claim_queued_outreach() -> list[dict]:
    connection = tools_db()
    connection.execute("BEGIN IMMEDIATE")
    rows = connection.execute(
        """SELECT r.id,r.block_id,r.appointment_id,r.patient_name,r.patient_phone,r.service_name,r.service_id,
                  r.original_start,r.original_end,r.original_fingerprint_json,r.outreach_text,d.block_date
             FROM rebooking_campaigns r JOIN day_blocks d ON d.id=r.block_id
            WHERE r.status='queued' ORDER BY d.block_date,r.original_start,r.id LIMIT 50"""
    ).fetchall()
    ids = [int(row["id"]) for row in rows]
    if ids:
        placeholders = ",".join("?" for _ in ids)
        connection.execute(
            f"UPDATE rebooking_campaigns SET status='sending',updated_at=? WHERE status='queued' AND id IN ({placeholders})",
            (dt.datetime.now(TZ).isoformat(), *ids),
        )
    connection.commit()
    connection.close()
    return [dict(row) for row in rows]


def live_appointment_for_outreach(appointment_id: int) -> dict | None:
    appointment_id = int(appointment_id)
    sql = f"""SELECT JSON_OBJECT(
      'id',a.id,'start',DATE_FORMAT(a.start_datetime,'%Y-%m-%d %H:%i:%s'),
      'end',DATE_FORMAT(a.end_datetime,'%Y-%m-%d %H:%i:%s'),'status',a.status,
      'customerId',a.id_users_customer,'providerId',a.id_users_provider,'serviceId',a.id_services,
      'phone',COALESCE(NULLIF(u.mobile_number,''),NULLIF(u.phone_number,''),''))
    FROM ea_appointments a LEFT JOIN ea_users u ON u.id=a.id_users_customer
    WHERE a.id={appointment_id} LIMIT 1;"""
    raw = ea_mysql(sql).strip()
    if not raw:
        return None
    return json.loads(raw.splitlines()[-1])


def outreach_source_matches(row: dict, live: dict | None) -> bool:
    if not live or "cancel" in str(live.get("status", "")).lower():
        return False
    try:
        expected = json.loads(row.get("original_fingerprint_json") or "{}")
    except json.JSONDecodeError:
        return False
    for key in ("id", "start", "end", "customerId", "providerId", "serviceId", "status"):
        if str(live.get(key, "")) != str(expected.get(key, "")):
            return False
    live_phone = re.sub(r"\D", "", str(live.get("phone") or ""))
    expected_phone = re.sub(r"\D", "", str(row.get("patient_phone") or ""))
    return bool(live_phone and expected_phone and set(blocklist_candidates(live_phone)) & set(blocklist_candidates(expected_phone)))


def recover_stale_outreach() -> int:
    cutoff = (dt.datetime.now(TZ) - dt.timedelta(minutes=15)).isoformat()
    connection = tools_db()
    cursor = connection.execute(
        """UPDATE rebooking_campaigns
              SET status='send_failed',last_error='stale_sending_state_requires_manual_review',updated_at=?
            WHERE status='sending' AND updated_at<?""",
        (dt.datetime.now(TZ).isoformat(), cutoff),
    )
    connection.commit()
    count = cursor.rowcount
    connection.close()
    return count


def pending_block_summaries() -> list[dict]:
    connection = tools_db()
    blocks = connection.execute(
        """SELECT d.id,d.block_date,d.reason
             FROM day_blocks d
            WHERE d.status='verified' AND d.ana_summary_sent_at IS NULL
              AND NOT EXISTS (SELECT 1 FROM rebooking_campaigns r WHERE r.block_id=d.id AND r.status IN ('queued','sending'))
            ORDER BY d.block_date,d.id"""
    ).fetchall()
    result = []
    for block in blocks:
        campaigns = connection.execute(
            """SELECT patient_name,original_start,service_name,status,last_error
                 FROM rebooking_campaigns WHERE block_id=? ORDER BY original_start,id""",
            (block["id"],),
        ).fetchall()
        result.append({**dict(block), "campaigns": [dict(row) for row in campaigns]})
    connection.close()
    return result


def outreach_summary_text(block: dict) -> str:
    rows = block["campaigns"]
    contacted = sum(row["status"] in ("contacted", "rescheduled") for row in rows)
    lines = [f"Bloqueo de agenda — {block['block_date'][8:10]}/{block['block_date'][5:7]}/{block['block_date'][:4]}", ""]
    if not rows:
        lines.append("El día quedó bloqueado y no tenía turnos existentes.")
    else:
        lines.append(f"Turnos existentes: {len(rows)}. Contactados por WhatsApp: {contacted}.")
    missing = [row for row in rows if row["status"] == "missing_phone"]
    if missing:
        lines += ["", "No pude iniciar la reagendación de estos turnos porque no tienen número de teléfono:"]
        for row in missing:
            lines.append(f"• {row['original_start'][11:16]} — {row['patient_name']} ({row['service_name']})")
    failed = [row for row in rows if row["status"] in ("send_failed", "suppressed", "source_changed")]
    if failed:
        lines += ["", "También requieren revisión manual:"]
        for row in failed:
            reason = "contacto bloqueado" if row["status"] == "suppressed" else ("el turno cambió o ya no existe" if row["status"] == "source_changed" else "falló el envío")
            lines.append(f"• {row['original_start'][11:16]} — {row['patient_name']}: {reason}")
    pending = [row for row in rows if row["status"] == "contacted"]
    if pending:
        lines += ["", f"Quedaron {len(pending)} conversaciones pendientes de acordar un nuevo horario."]
    return "\n".join(lines)


def mark_block_summary_sent(block_id: int) -> None:
    connection = tools_db()
    connection.execute("UPDATE day_blocks SET ana_summary_sent_at=? WHERE id=?", (dt.datetime.now(TZ).isoformat(), block_id))
    connection.commit()
    connection.close()


def process_rebooking_outreach(dry_run: bool = False) -> int:
    if dry_run:
        return 0
    if not TOOLS_DB.exists():
        record_run("ana_rebooking_outreach", "blocked", {"reason": "tools_db_missing", "dry_run": dry_run})
        log("rebooking outreach blocked: tools DB missing")
        return 4
    stale = 0 if dry_run else recover_stale_outreach()
    queued = claim_queued_outreach() if not dry_run else []
    contacted = suppressed = failed = 0
    for row in queued:
        try:
            if not outreach_source_matches(row, live_appointment_for_outreach(row["appointment_id"])):
                failed += 1
                mark_outreach(row["id"], "source_changed", error="authoritative_appointment_changed_or_missing")
                continue
            if blocked_contact(row["patient_phone"]):
                suppressed += 1
                mark_outreach(row["id"], "suppressed", error="contact_blocklisted")
                continue
            ok, message_id = send_whatsapp(row["patient_phone"], row["outreach_text"], dry_run=False)
            if ok:
                contacted += 1
                mark_outreach(row["id"], "contacted", message_id=message_id)
            else:
                failed += 1
                mark_outreach(row["id"], "send_failed", error=message_id)
        except Exception as exc:
            failed += 1
            try:
                mark_outreach(row["id"], "send_failed", error=f"worker_error:{type(exc).__name__}")
            except Exception:
                pass
    alerts = alert_failures = 0
    summaries = pending_block_summaries() if not dry_run else []
    for block in summaries:
        try:
            ok, message_id = send_whatsapp(alert_destination(), outreach_summary_text(block), dry_run=False)
            if ok:
                alerts += 1
                mark_block_summary_sent(block["id"])
            else:
                alert_failures += 1
        except Exception:
            alert_failures += 1
    if not dry_run and not queued and not summaries and stale == 0:
        return 0
    details = {"queued": len(queued), "contacted": contacted, "suppressed": suppressed, "failed": failed, "stale": stale, "ana_alerts": alerts, "ana_alert_failures": alert_failures, "dry_run": dry_run}
    status = "ok" if failed == 0 and alert_failures == 0 and stale == 0 else "partial"
    record_run("ana_rebooking_outreach", status, details)
    log(f"rebooking outreach done {details}")
    return 0 if status == "ok" else 2


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["sync", "send-reminders", "alert-no-response", "process-rebooking-outreach", "dry-run-all"])
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.mode == "sync":
        return run_sync(dry_run=args.dry_run)
    if args.mode == "send-reminders":
        return send_reminders(dry_run=args.dry_run)
    if args.mode == "alert-no-response":
        return alert_no_response(dry_run=args.dry_run)
    if args.mode == "process-rebooking-outreach":
        return process_rebooking_outreach(dry_run=args.dry_run)
    if args.mode == "dry-run-all":
        rc1 = run_sync(dry_run=True)
        rc2 = send_reminders(dry_run=True)
        rc3 = alert_no_response(dry_run=True)
        return max(rc1, rc2, rc3)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
