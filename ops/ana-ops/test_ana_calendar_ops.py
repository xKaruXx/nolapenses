import importlib.util
import json
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

MODULE_PATH = pathlib.Path(__file__).with_name("ana_calendar_ops.py")
spec = importlib.util.spec_from_file_location("ana_calendar_ops", MODULE_PATH)
ops = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ops)


def appointment(phone="5492665111111"):
    return {
        "appointment_id": 999001,
        "start": "2026-08-12 10:00:00",
        "end": "2026-08-12 10:30:00",
        "service": "Consulta",
        "patient_name": "Paciente de prueba",
        "patient_phone": phone,
        "dni": "",
        "status": "booked",
    }


class AnaCalendarOpsTests(unittest.TestCase):
    def setUp(self):
        self.tools_db = pathlib.Path(tempfile.mktemp(prefix="ana-outreach-test-", suffix=".db"))
        ops.TOOLS_DB = self.tools_db
        connection = sqlite3.connect(self.tools_db)
        connection.executescript("""
        CREATE TABLE day_blocks(id INTEGER PRIMARY KEY,block_date TEXT,reason TEXT,status TEXT,ana_summary_sent_at TEXT);
        CREATE TABLE rebooking_campaigns(
          id INTEGER PRIMARY KEY,block_id INTEGER,appointment_id INTEGER,patient_name TEXT,patient_phone TEXT,
          service_name TEXT,service_id INTEGER,original_start TEXT,original_end TEXT,original_fingerprint_json TEXT,status TEXT,outreach_text TEXT,whatsapp_message_id TEXT,
          last_error TEXT,updated_at TEXT);
        """)
        connection.commit(); connection.close()

    def tearDown(self):
        self.tools_db.unlink(missing_ok=True)

    def seed_block_campaigns(self):
        connection = sqlite3.connect(self.tools_db)
        connection.execute("INSERT INTO day_blocks(id,block_date,reason,status) VALUES(1,'2026-08-21','curso','verified')")
        def fp(appointment_id, start, customer_id):
            return json.dumps({"id": appointment_id, "start": start, "end": start[:11] + f"{int(start[11:13])+1:02d}:00:00", "status": "Booked", "customerId": customer_id, "providerId": 2, "serviceId": 1})
        rows = [
            (1, 1, 1001, "Paciente Contactable", "5492665111111", "Consulta", 1, "2026-08-21 10:00:00", "2026-08-21 11:00:00", fp(1001,"2026-08-21 10:00:00",11), "queued", "mensaje uno"),
            (2, 1, 1002, "Paciente Bloqueado", "5492665222222", "Limpieza", 1, "2026-08-21 11:00:00", "2026-08-21 12:00:00", fp(1002,"2026-08-21 11:00:00",12), "queued", "mensaje dos"),
            (3, 1, 1003, "Paciente Sin Teléfono", "", "Consulta", 1, "2026-08-21 12:00:00", "2026-08-21 13:00:00", fp(1003,"2026-08-21 12:00:00",13), "missing_phone", ""),
        ]
        connection.executemany("""INSERT INTO rebooking_campaigns
          (id,block_id,appointment_id,patient_name,patient_phone,service_name,service_id,original_start,original_end,original_fingerprint_json,status,outreach_text,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""", rows)
        connection.commit(); connection.close()

    def live_campaign(self, appointment_id):
        mapping = {1001: ("2026-08-21 10:00:00", "2026-08-21 11:00:00", 11, "5492665111111"), 1002: ("2026-08-21 11:00:00", "2026-08-21 12:00:00", 12, "5492665222222")}
        start, end, customer_id, phone = mapping[appointment_id]
        return {"id": appointment_id, "start": start, "end": end, "status": "Booked", "customerId": customer_id, "providerId": 2, "serviceId": 1, "phone": phone}

    def test_invalid_utf8_subprocess_output_is_replaced_not_crashed(self):
        result = ops.run([
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(bytes([0xe1]))",
        ])
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout)

    def test_argentina_mobile_blocklist_candidates_include_both_forms(self):
        self.assertEqual(
            set(ops.blocklist_candidates("+54 9 266 511-1111")),
            {"5492665111111", "542665111111"},
        )

    def test_blocked_contact_is_never_sent_or_persisted(self):
        record = Mock()
        with (
            patch.object(ops, "run_sync", return_value=0),
            patch.object(ops, "fetch_tomorrow_appointments", return_value=[appointment()]),
            patch.object(ops, "reminder_exists", return_value=False),
            patch.object(ops, "blocked_contact", return_value=True),
            patch.object(ops, "send_whatsapp") as send,
            patch.object(ops, "upsert_reminder") as upsert,
            patch.object(ops, "record_run", record),
            patch.object(ops, "log"),
        ):
            self.assertEqual(ops.send_reminders(dry_run=False), 0)
        send.assert_not_called()
        upsert.assert_not_called()
        details = record.call_args.args[2]
        self.assertEqual(details["blocked"], 1)
        self.assertEqual(details["sent"], 0)

    def test_dry_run_never_persists_reminder(self):
        record = Mock()
        with (
            patch.object(ops, "run_sync", return_value=0),
            patch.object(ops, "fetch_tomorrow_appointments", return_value=[appointment()]),
            patch.object(ops, "reminder_exists", return_value=False),
            patch.object(ops, "blocked_contact", return_value=False),
            patch.object(ops, "send_whatsapp", return_value=(True, "dry_run")) as send,
            patch.object(ops, "upsert_reminder") as upsert,
            patch.object(ops, "record_run", record),
            patch.object(ops, "log"),
        ):
            self.assertEqual(ops.send_reminders(dry_run=True), 0)
        send.assert_called_once()
        self.assertTrue(send.call_args.kwargs["dry_run"])
        upsert.assert_not_called()
        self.assertTrue(record.call_args.args[2]["dry_run"])

    def test_no_response_dry_run_does_not_mark_alerted(self):
        row = {
            "id": 1,
            "appointment_id": 2,
            "phone": "5492665111111",
            "name": "Paciente",
            "start": "2026-08-12 10:00:00",
            "service": "Consulta",
        }
        with (
            patch.object(ops, "pending_no_response_rows", return_value=[row]),
            patch.object(ops, "send_whatsapp", return_value=(True, "dry_run")),
            patch.object(ops, "n8n_psql") as sql,
            patch.object(ops, "record_run"),
            patch.object(ops, "log"),
        ):
            self.assertEqual(ops.alert_no_response(dry_run=True), 0)
        sql.assert_not_called()

    def test_rebooking_outreach_sends_contactable_suppresses_blocked_and_alerts_missing_phone(self):
        self.seed_block_campaigns()
        sent = []
        def fake_send(to, text, *, dry_run=False):
            sent.append((to, text, dry_run))
            return True, f"msg-{len(sent)}"
        with (
            patch.object(ops, "blocked_contact", side_effect=lambda phone: phone.endswith("222222")),
            patch.object(ops, "live_appointment_for_outreach", side_effect=self.live_campaign),
            patch.object(ops, "send_whatsapp", side_effect=fake_send),
            patch.object(ops, "alert_destination", return_value="ana@lid"),
            patch.object(ops, "record_run"),
            patch.object(ops, "log"),
        ):
            self.assertEqual(ops.process_rebooking_outreach(dry_run=False), 0)
        connection = sqlite3.connect(self.tools_db)
        statuses = dict(connection.execute("SELECT appointment_id,status FROM rebooking_campaigns"))
        alerted = connection.execute("SELECT ana_summary_sent_at FROM day_blocks WHERE id=1").fetchone()[0]
        connection.close()
        self.assertEqual(statuses, {1001: "contacted", 1002: "suppressed", 1003: "missing_phone"})
        self.assertIsNotNone(alerted)
        self.assertEqual(sent[0][0], "5492665111111")
        self.assertEqual(sent[-1][0], "ana@lid")
        self.assertIn("no tienen número de teléfono", sent[-1][1])
        self.assertIn("Paciente Sin Teléfono", sent[-1][1])
        self.assertNotIn("mensaje dos", "\n".join(text for _, text, _ in sent))

    def test_rebooking_outreach_dry_run_has_no_side_effects(self):
        self.seed_block_campaigns()
        record = Mock()
        with (
            patch.object(ops, "send_whatsapp") as send,
            patch.object(ops, "record_run", record),
            patch.object(ops, "log"),
        ):
            self.assertEqual(ops.process_rebooking_outreach(dry_run=True), 0)
        send.assert_not_called()
        connection = sqlite3.connect(self.tools_db)
        statuses = dict(connection.execute("SELECT appointment_id,status FROM rebooking_campaigns"))
        alerted = connection.execute("SELECT ana_summary_sent_at FROM day_blocks WHERE id=1").fetchone()[0]
        connection.close()
        self.assertEqual(statuses, {1001: "queued", 1002: "queued", 1003: "missing_phone"})
        self.assertIsNone(alerted)
        record.assert_not_called()

    def test_blocklist_failure_is_isolated_per_recipient(self):
        self.seed_block_campaigns()
        checks = iter([RuntimeError("postgres unavailable"), False])
        def check(_phone):
            value = next(checks)
            if isinstance(value, Exception): raise value
            return value
        with (
            patch.object(ops, "blocked_contact", side_effect=check),
            patch.object(ops, "live_appointment_for_outreach", side_effect=self.live_campaign),
            patch.object(ops, "send_whatsapp", return_value=(True, "message-id")),
            patch.object(ops, "record_run"),
            patch.object(ops, "log"),
        ):
            self.assertEqual(ops.process_rebooking_outreach(dry_run=False), 2)
        connection = sqlite3.connect(self.tools_db)
        statuses = dict(connection.execute("SELECT appointment_id,status FROM rebooking_campaigns"))
        connection.close()
        self.assertEqual(statuses[1001], "send_failed")
        self.assertEqual(statuses[1002], "contacted")

    def test_changed_appointment_is_not_contacted(self):
        self.seed_block_campaigns()
        changed = self.live_campaign(1001); changed["start"] = "2026-08-21 09:00:00"
        with (
            patch.object(ops, "live_appointment_for_outreach", side_effect=lambda appointment_id: changed if appointment_id == 1001 else self.live_campaign(appointment_id)),
            patch.object(ops, "blocked_contact", return_value=True),
            patch.object(ops, "send_whatsapp", return_value=(True, "message-id")) as send,
            patch.object(ops, "alert_destination", return_value="ana@lid"),
            patch.object(ops, "record_run"), patch.object(ops, "log"),
        ):
            self.assertEqual(ops.process_rebooking_outreach(dry_run=False), 2)
        connection = sqlite3.connect(self.tools_db)
        status = connection.execute("SELECT status FROM rebooking_campaigns WHERE appointment_id=1001").fetchone()[0]
        connection.close()
        self.assertEqual(status, "source_changed")
        self.assertFalse(any(call.args and call.args[0] == "5492665111111" for call in send.call_args_list))

    def test_idle_rebooking_worker_is_silent_and_does_not_record_runs(self):
        record = Mock()
        with (
            patch.object(ops, "record_run", record),
            patch.object(ops, "send_whatsapp") as send,
            patch.object(ops, "log") as log,
        ):
            self.assertEqual(ops.process_rebooking_outreach(dry_run=False), 0)
        record.assert_not_called()
        send.assert_not_called()
        log.assert_not_called()


if __name__ == "__main__":
    unittest.main()
