import os
import hashlib
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

os.environ.setdefault("TOOLS_DB", tempfile.mktemp(prefix="ana-tools-test-", suffix=".db"))
os.environ.setdefault("ADMIN_PHONES", "5493517000000")

import app
from starlette.requests import Request


def request():
    return Request({"type": "http", "headers": [(b"authorization", b"Basic test")]})


def unauthenticated_request():
    return Request({"type": "http", "headers": []})


def future_date(days=10):
    return (datetime.now(app.TZ) + timedelta(days=days)).strftime("%Y-%m-%d")


def booking(**overrides):
    data = {
        "role": "admin",
        "requester_phone": "5493517000000",
        "message_id": "msg-default",
        "dry_run": True,
        "patient_name": "Paciente Prueba",
        "coverage": "Particular",
        "service_name": "consulta",
        "date": future_date(),
        "time": "14:00",
        "override_authorized": True,
    }
    data.update(overrides)
    return app.BookIn(**data)


class ExceptionalBookingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        app.DB = tempfile.mktemp(prefix="ana-tools-test-", suffix=".db")

    async def test_camioneros_duration_is_15_minutes(self):
        self.assertEqual(app.service_for("camioneros")["duration"], 15)

    async def test_clinic_info_returns_canonical_address_and_maps_link(self):
        item = app.ClinicInfoIn(
            role="patient",
            requester_phone="5492665000000",
            message_id="clinic-location",
        )
        result = app.clinic_info_tool(item, request())
        self.assertTrue(result["ok"])
        self.assertEqual(result["address"], "Junín 383, Clínica Domínguez D’Agata")
        self.assertEqual(result["maps_url"], "https://maps.app.goo.gl/DFzPyGhUfcVSd5qN8")
        self.assertIn(result["address"], result["message"])
        self.assertIn(result["maps_url"], result["message"])

    async def test_free_but_outside_schedule_requires_owner_confirmation(self):
        async def fake_ea(req, method, path, **kwargs):
            if path == "/availabilities":
                return []
            if path == "/appointments":
                return []
            raise AssertionError(path)

        item = booking(message_id="outside-1")
        with patch.object(app, "ea", side_effect=fake_ea):
            result = await app.book_tool(item, request())
        self.assertEqual(result["error"], "outside_availability_confirmation_required")
        self.assertIsNotNone(app.load_pending_exception(item.requester_phone))

    async def test_confirmed_exception_is_simulated_and_marked(self):
        async def fake_ea(req, method, path, **kwargs):
            if path in ("/availabilities", "/appointments"):
                return []
            raise AssertionError(path)

        item = booking(message_id="outside-2")
        with patch.object(app, "ea", side_effect=fake_ea):
            first = await app.book_tool(item, request())
            self.assertEqual(first["error"], "outside_availability_confirmation_required")
            confirmation = app.ConfirmExceptionalIn(
                role="admin",
                requester_phone=item.requester_phone,
                message_id="confirm-2",
                dry_run=True,
                confirmed=True,
                override_authorized=True,
            )
            result = await app.confirm_exception_tool(confirmation, request())
        self.assertTrue(result["ok"])
        self.assertTrue(result["dry_run"])
        self.assertTrue(result["would_book"]["exceptional_outside_availability"])
        self.assertIsNone(app.load_pending_exception(item.requester_phone))

    async def test_admin_is_warned_and_can_confirm_same_known_overlap(self):
        date = future_date()
        conflict = {
            "id": 603, "start": f"{date} 13:45:00", "end": f"{date} 14:30:00",
            "status": "Booked", "serviceId": 1, "serviceName": "Consulta odontológica",
            "customerName": "Paciente existente",
        }

        async def fake_ea(req, method, path, **kwargs):
            if path == "/availabilities": return []
            if path == "/appointments": return [conflict]
            raise AssertionError(path)

        item = booking(message_id="overlap-warning", date=date, time="14:00")
        with patch.object(app, "ea", side_effect=fake_ea):
            first = await app.book_tool(item, request())
            self.assertEqual(first["error"], "slot_conflict_confirmation_required")
            self.assertEqual([x["id"] for x in first["conflicts"]], [603])
            self.assertIsNotNone(app.load_pending_exception(item.requester_phone))
            confirmation = app.ConfirmExceptionalIn(
                role="admin", requester_phone=item.requester_phone,
                message_id="overlap-confirm", dry_run=True,
                confirmed=True, override_authorized=True,
            )
            result = await app.confirm_exception_tool(confirmation, request())
        self.assertTrue(result["ok"])
        self.assertTrue(result["dry_run"])
        self.assertTrue(result["would_book"]["exceptional_overlap_confirmed"])
        self.assertIsNone(app.load_pending_exception(item.requester_phone))

    async def test_new_overlap_after_warning_requires_fresh_confirmation(self):
        date = future_date()
        old = {"id": 604, "start": f"{date} 13:45:00", "end": f"{date} 14:30:00", "status": "Booked", "serviceName": "Consulta", "customerName": "Paciente uno"}
        new = {"id": 605, "start": f"{date} 14:00:00", "end": f"{date} 15:00:00", "status": "Booked", "serviceName": "Arreglo", "customerName": "Paciente dos"}
        state = {"rows": [old]}
        async def fake_ea(req, method, path, **kwargs):
            if path == "/availabilities": return []
            if path == "/appointments": return state["rows"]
            raise AssertionError(path)
        item = booking(message_id="overlap-race-warning", date=date, time="14:00")
        with patch.object(app, "ea", side_effect=fake_ea):
            first = await app.book_tool(item, request())
            self.assertEqual(first["error"], "slot_conflict_confirmation_required")
            state["rows"] = [old, new]
            confirmation = app.ConfirmExceptionalIn(role="admin", requester_phone=item.requester_phone, message_id="overlap-race-confirm", dry_run=True, confirmed=True, override_authorized=True)
            result = await app.confirm_exception_tool(confirmation, request())
        self.assertEqual(result["error"], "slot_conflict_changed_confirmation_required")
        self.assertEqual({x["id"] for x in result["conflicts"]}, {604, 605})
        self.assertIsNotNone(app.load_pending_exception(item.requester_phone))

    async def test_patient_overlap_remains_blocked(self):
        date = future_date()
        conflict = {"id": 99, "start": f"{date} 13:45:00", "end": f"{date} 14:30:00", "status": "Booked", "customerName": "Otro paciente", "serviceName": "Consulta odontológica"}
        async def fake_ea(req, method, path, **kwargs):
            if path == "/availabilities": return []
            if path == "/appointments": return [conflict]
            raise AssertionError(path)
        item = booking(role="patient", requester_phone="5492665000000", phone="", dni="30123456", override_authorized=False, message_id="patient-overlap", date=date)
        with patch.object(app, "ea", side_effect=fake_ea):
            result = await app.book_tool(item, request())
        self.assertEqual(result["error"], "slot_occupied")
        self.assertIsNone(app.load_pending_exception(item.requester_phone))

    async def test_patient_and_unauthorized_admin_cannot_request_override(self):
        async def fake_ea(req, method, path, **kwargs):
            return []

        patient = booking(
            role="patient",
            requester_phone="5492665000000",
            phone="",
            dni="30123456",
            message_id="patient-outside",
            override_authorized=False,
        )
        unauthorized = booking(
            requester_phone="5492665111111",
            message_id="admin-outside",
            override_authorized=False,
        )
        with patch.object(app, "ea", side_effect=fake_ea):
            patient_result = await app.book_tool(patient, request())
            admin_result = await app.book_tool(unauthorized, request())
        self.assertEqual(patient_result["error"], "slot_unavailable")
        self.assertEqual(admin_result["error"], "slot_unavailable")

    async def test_availability_limits_to_three_policy_compliant_slots(self):
        date = future_date()
        while datetime.strptime(date, "%Y-%m-%d").weekday() not in (1, 2, 3):
            date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

        async def fake_ea(req, method, path, **kwargs):
            if path == "/availabilities":
                return [
                    f"{date} 16:00:00", f"{date} 17:00:00", f"{date} 18:00:00",
                    f"{date} 19:00:00", f"{date} 20:00:00",
                ]
            if path == "/appointments":
                return []
            raise AssertionError(path)

        item = app.ReadIn(
            operation="availability", role="patient", requester_phone="5492665000000",
            message_id="availability-limit", date=date, service_name="arreglo",
        )
        with patch.object(app, "ea", side_effect=fake_ea):
            result = await app.read_tool(item, request())
        self.assertEqual(result["slots"], [f"{date} 16:00:00", f"{date} 17:00:00", f"{date} 18:00:00"])
        self.assertEqual(result["duration_minutes"], 60)
        self.assertFalse(result["has_more"])

    async def test_long_treatment_at_16_blocks_short_slot_at_17(self):
        date = future_date()
        while datetime.strptime(date, "%Y-%m-%d").weekday() not in (1, 2, 3):
            date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        conflict = {
            "id": 200,
            "start": f"{date} 16:00:00",
            "end": f"{date} 18:00:00",
            "status": "Booked",
            "customerName": "Paciente tratamiento",
            "serviceName": "Tratamiento de conducto / Endodoncia",
        }

        async def fake_ea(req, method, path, **kwargs):
            if path == "/availabilities":
                return [f"{date} 16:00:00", f"{date} 17:00:00", f"{date} 18:00:00"]
            if path == "/appointments":
                return [conflict]
            raise AssertionError(path)

        item = app.ReadIn(
            operation="availability", role="patient", requester_phone="5492665000000",
            message_id="availability-overlap", date=date, service_name="arreglo",
        )
        with patch.object(app, "ea", side_effect=fake_ea):
            result = await app.read_tool(item, request())
        self.assertEqual(result["slots"], [f"{date} 18:00:00"])

    async def test_existing_root_canal_does_not_block_non_overlapping_second_one(self):
        date = future_date()
        while datetime.strptime(date, "%Y-%m-%d").weekday() not in (1, 2, 3):
            date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        existing = {"id": 600, "start": f"{date} 10:00:00", "end": f"{date} 12:00:00", "status": "Booked", "service": {"id": 6, "name": "Tratamiento de conducto / Endodoncia"}, "customerName": "Paciente existente"}
        async def fake_ea(req, method, path, **kwargs):
            if path == "/availabilities": return [f"{date} 16:00:00"]
            if path == "/appointments": return [existing]
            raise AssertionError(path)
        item = app.ReadIn(operation="availability", role="patient", requester_phone="5492665000000", message_id="second-root-canal-allowed", date=date, service_name="conducto")
        with patch.object(app, "ea", side_effect=fake_ea): result = await app.read_tool(item, request())
        self.assertEqual(result["slots"], [f"{date} 16:00:00"])
        self.assertEqual(result["profitability"]["status"], "profitable_treatment_present")

    async def test_day_with_only_consultations_and_cleanings_needs_profitable_treatment(self):
        date = future_date()
        rows = [
            {"id": 610, "start": f"{date} 16:00:00", "end": f"{date} 17:00:00", "status": "Booked", "serviceId": 1, "serviceName": "Consulta"},
            {"id": 611, "start": f"{date} 17:00:00", "end": f"{date} 18:00:00", "status": "Booked", "serviceId": 4, "serviceName": "Limpieza"},
        ]
        status=app.day_profitability(rows)
        self.assertEqual(status["status"], "needs_profitable_treatment")
        self.assertFalse(status["has_profitable_treatment"])

    async def test_root_canal_or_inlay_makes_day_profitable(self):
        date = future_date()
        for service_id, name in ((6, "Conducto"), (7, "Incrustación")):
            rows=[{"id":service_id, "start":f"{date} 16:00:00", "end":f"{date} 18:00:00", "status":"Booked", "serviceId":service_id, "serviceName":name}]
            status=app.day_profitability(rows)
            self.assertEqual(status["status"], "profitable_treatment_present")
            self.assertTrue(status["has_profitable_treatment"])

    async def test_agenda_list_includes_patient_coverage(self):
        date = future_date()
        rows = [{
            "id": 700,
            "start": f"{date} 16:00:00",
            "end": f"{date} 17:00:00",
            "status": "Booked",
            "serviceName": "Arreglo dental",
            "customer": {
                "firstName": "Carla",
                "lastName": "Barbajelata",
                "customField2": "OSDE 210",
            },
        }, {
            "id": 701,
            "start": f"{date} 17:00:00",
            "end": f"{date} 18:00:00",
            "status": "Booked",
            "serviceName": "Consulta",
            "customerName": "Paciente sin dato",
        }]

        async def fake_ea(req, method, path, **kwargs):
            if path == "/appointments":
                return rows
            raise AssertionError(path)

        item = app.ReadIn(
            operation="list", role="admin", requester_phone="5493517000000",
            message_id="agenda-with-coverage", date=date,
        )
        with patch.object(app, "ea", side_effect=fake_ea):
            result = await app.read_tool(item, request())
        self.assertEqual(result["appointments"][0]["coverage"], "OSDE 210")
        self.assertEqual(result["appointments"][1]["coverage"], "Sin cobertura registrada")

    async def test_validation_reports_named_missing_fields(self):
        patient = booking(
            role="patient", requester_phone="", phone="", dni=None,
            patient_name="Fernanda", coverage="", message_id="missing-fields",
        )
        with patch.object(app, "ea", side_effect=AssertionError("EA must not be called")):
            result = await app.book_tool(patient, request())
        self.assertEqual(result["error"], "missing_data")
        self.assertEqual(set(result["missing_fields"]), {"apellido", "dni", "telefono", "cobertura"})
        self.assertFalse(result["confirmed"])

    async def test_validation_reports_missing_date_time_and_service(self):
        patient = app.BookIn(
            role="patient", requester_phone="5492665000000", message_id="missing-core",
            dry_run=True, patient_name="Fernanda Márquez", dni="30123456",
            coverage="OSDE", service_name="", date="", time="",
        )
        with patch.object(app, "ea", side_effect=AssertionError("EA must not be called")):
            result = await app.book_tool(patient, request())
        self.assertEqual(result["error"], "missing_data")
        self.assertEqual(set(result["missing_fields"]), {"servicio", "fecha", "hora"})
        self.assertFalse(result["confirmed"])

    async def test_camioneros_is_not_offered_in_generic_afternoon_slots(self):
        date = future_date()
        while datetime.strptime(date, "%Y-%m-%d").weekday() not in (1, 2):
            date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        async def fake_ea(req, method, path, **kwargs):
            if path == "/availabilities": return [f"{date} 16:00:00", f"{date} 17:00:00", f"{date} 18:00:00"]
            if path == "/appointments": return []
            raise AssertionError(path)
        item = app.ReadIn(operation="availability", role="patient", requester_phone="5492665000000", message_id="camioneros-wrong-day", date=date, service_name="camioneros")
        with patch.object(app, "ea", side_effect=fake_ea):
            result = await app.read_tool(item, request())
        self.assertEqual(result["slots"], [])

    async def test_thursday_18_allows_second_camioneros_consultation_only(self):
        date = future_date()
        while datetime.strptime(date, "%Y-%m-%d").weekday() != 3:
            date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        existing = {"id": 501, "start": f"{date} 18:00:00", "end": f"{date} 18:15:00", "status": "Booked", "customerName": "Consulta uno", "serviceName": "Consulta OS Camioneros"}
        async def fake_ea(req, method, path, **kwargs):
            if path == "/availabilities": return [f"{date} 18:00:00"]
            if path == "/appointments": return [existing]
            raise AssertionError(path)
        camioneros = app.ReadIn(operation="availability", role="patient", requester_phone="5492665000000", message_id="camioneros-capacity", date=date, service_name="camioneros")
        consulta = app.ReadIn(operation="availability", role="patient", requester_phone="5492665000000", message_id="normal-capacity", date=date, service_name="consulta")
        with patch.object(app, "ea", side_effect=fake_ea):
            allowed = await app.read_tool(camioneros, request())
            blocked = await app.read_tool(consulta, request())
        self.assertEqual(allowed["slots"], [f"{date} 18:00:00"])
        self.assertEqual(blocked["slots"], [])

    async def test_second_patient_in_same_message_cannot_reuse_first_confirmation(self):
        first_payload = booking(message_id="two-patients", patient_name="Fernanda Márquez").model_dump()
        app.audit("two-patients", "book", "admin", False, "success", {
            "ok": True, "confirmed": True, "verified": True, "dry_run": False,
            "appointment_id": 777, "patient": "Fernanda Márquez",
        }, first_payload)
        second = booking(message_id="two-patients", patient_name="Matías Moyano")
        with patch.object(app, "ea", side_effect=AssertionError("second booking must be blocked")):
            result = await app.book_tool(second, request())
        self.assertEqual(result["error"], "multiple_bookings_in_one_message")
        self.assertFalse(result["confirmed"])
        self.assertNotEqual(result.get("patient"), "Matías Moyano")

    async def test_creation_is_verified_before_confirmation(self):
        date = future_date()
        while datetime.strptime(date, "%Y-%m-%d").weekday() not in (1, 2, 3):
            date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        state = {"created": False}

        async def fake_ea(req, method, path, **kwargs):
            if path == "/availabilities":
                return [f"{date} 16:00:00"]
            if path == "/appointments" and method == "GET":
                return []
            if path == "/customers" and method == "GET":
                return [{"id": 10, "customField1": "30123456", "phone": "5492665000000"}]
            if path == "/appointments" and method == "POST":
                state["created"] = True
                return {"id": 321}
            if path == "/appointments/321" and method == "GET":
                return {"id": 321, "start": f"{date} 16:00:00", "end": f"{date} 17:00:00", "status": "Booked"}
            raise AssertionError((method, path))

        item = booking(
            role="patient", requester_phone="5492665000000", dni="30123456",
            phone="5492665000000", message_id="verified-create", date=date, time="16:00",
            dry_run=False, override_authorized=False,
        )
        with patch.object(app, "ea", side_effect=fake_ea):
            result = await app.book_tool(item, request())
        self.assertTrue(state["created"])
        self.assertTrue(result["confirmed"])
        self.assertTrue(result["verified"])
        self.assertEqual(result["appointment_id"], 321)

    async def test_creation_without_readback_is_not_confirmed(self):
        date = future_date()
        while datetime.strptime(date, "%Y-%m-%d").weekday() not in (1, 2, 3):
            date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

        async def fake_ea(req, method, path, **kwargs):
            if path == "/availabilities":
                return [f"{date} 16:00:00"]
            if path == "/appointments" and method == "GET":
                return []
            if path == "/customers" and method == "GET":
                return [{"id": 10, "customField1": "30123456", "phone": "5492665000000"}]
            if path == "/appointments" and method == "POST":
                return {"id": 322}
            if path == "/appointments/322" and method == "GET":
                raise app.HTTPException(502, "No se pudo releer")
            raise AssertionError((method, path))

        item = booking(
            role="patient", requester_phone="5492665000000", dni="30123456",
            phone="5492665000000", message_id="unverified-create", date=date, time="16:00",
            dry_run=False, override_authorized=False,
        )
        with patch.object(app, "ea", side_effect=fake_ea):
            result = await app.book_tool(item, request())
        self.assertFalse(result["confirmed"])
        self.assertEqual(result["error"], "booking_verification_failed")
        self.assertEqual(result["appointment_id"], 322)

    async def test_confirmation_rechecks_conflicts(self):
        date = future_date()
        state = {"occupied": False}

        async def fake_ea(req, method, path, **kwargs):
            if path == "/availabilities":
                return []
            if path == "/appointments" and not state["occupied"]:
                return []
            if path == "/appointments":
                return [{
                    "id": 101,
                    "start": f"{date} 14:00:00",
                    "end": f"{date} 15:00:00",
                    "status": "Booked",
                    "customerName": "Turno nuevo",
                    "serviceName": "Consulta odontológica",
                }]
            raise AssertionError(path)

        item = booking(message_id="outside-race", date=date)
        with patch.object(app, "ea", side_effect=fake_ea):
            first = await app.book_tool(item, request())
            self.assertEqual(first["error"], "outside_availability_confirmation_required")
            state["occupied"] = True
            confirmation = app.ConfirmExceptionalIn(
                role="admin",
                requester_phone=item.requester_phone,
                message_id="confirm-race",
                dry_run=True,
                confirmed=True,
                override_authorized=True,
            )
            result = await app.confirm_exception_tool(confirmation, request())
        self.assertEqual(result["error"], "slot_conflict_changed_confirmation_required")
        self.assertFalse(result["confirmed"])
        self.assertIsNotNone(app.load_pending_exception(item.requester_phone))

    def day_block(self, **overrides):
        data = {
            "action": "preview", "role": "admin", "requester_phone": "5493517000000",
            "message_id": "block-preview", "dry_run": False, "date": future_date(),
            "reason": "curso", "confirmed": False, "override_authorized": True,
            "event_timestamp": 101 if overrides.get("action") == "confirm" else 100,
        }
        data.update(overrides)
        return app.DayBlockIn(**data)

    def seeded_campaign(self, date, phone="5492665111111"):
        now = datetime.now(app.TZ).isoformat()
        c = app.db()
        c.execute("INSERT INTO day_blocks(provider_id,block_date,reason,unavailability_id,owner_number,status,created_at,verified_at) VALUES(2,?,'curso',55,'5493517000000','verified',?,?)", (date, now, now))
        block_id = c.execute("SELECT id FROM day_blocks WHERE block_date=?", (date,)).fetchone()[0]
        c.execute("""INSERT INTO rebooking_campaigns(block_id,appointment_id,patient_name,patient_phone,service_name,service_id,original_start,original_end,status,outreach_text,created_at,updated_at)
                     VALUES(?,901,'Paciente Prueba',?,'Consulta odontológica',1,?,?,'contacted','mensaje',?,?)""",
                  (block_id, phone, f"{date} 16:00:00", f"{date} 17:00:00", now, now))
        c.commit(); c.close()

    async def test_day_block_preview_reports_missing_phone_and_requires_confirmation(self):
        date = future_date()
        rows = [
            {"id": 801, "start": f"{date} 10:00:00", "end": f"{date} 11:00:00", "status": "Booked", "serviceId": 1, "serviceName": "Consulta", "customer": {"firstName": "Con", "lastName": "Teléfono", "phone": "5492665111111"}},
            {"id": 802, "start": f"{date} 11:00:00", "end": f"{date} 12:00:00", "status": "Booked", "serviceId": 1, "serviceName": "Consulta", "customer": {"firstName": "Sin", "lastName": "Teléfono", "phone": ""}},
        ]
        async def fake_ea(req, method, path, **kwargs):
            if path == "/providers/2": return {"id": 2}
            self.assertEqual((method, path), ("GET", "/appointments")); return rows
        with patch.object(app, "ea", side_effect=fake_ea):
            result = await app.day_block_tool(self.day_block(date=date), request())
        self.assertTrue(result["confirmation_required"])
        self.assertEqual(result["contactable_count"], 1)
        self.assertEqual(result["missing_phone_count"], 1)
        self.assertEqual(result["missing_phone"][0]["patient"], "Sin Teléfono")
        self.assertIsNotNone(app.load_pending_day_block("5493517000000", result["proposal_id"]))

    async def test_local_san_luis_phone_is_normalized_for_whatsapp(self):
        row = {"customer": {"phone": "266 511-1111"}}
        self.assertEqual(app.customer_phone(row), "5492665111111")

    async def test_same_appointment_can_enter_a_later_block_campaign(self):
        now = datetime.now(app.TZ).isoformat(); c = app.db()
        c.execute("INSERT INTO day_blocks(id,provider_id,block_date,reason,owner_number,status,created_at) VALUES(1,2,?,'uno','1','verified',?)", (future_date(30), now))
        c.execute("INSERT INTO day_blocks(id,provider_id,block_date,reason,owner_number,status,created_at) VALUES(2,2,?,'dos','1','verified',?)", (future_date(31), now))
        values = (901, "Paciente", "5492665111111", "Consulta", 1, "2026-09-01 16:00:00", "2026-09-01 17:00:00", "queued", "mensaje", now, now)
        for block_id in (1, 2):
            c.execute("""INSERT INTO rebooking_campaigns(block_id,appointment_id,patient_name,patient_phone,service_name,service_id,original_start,original_end,status,outreach_text,created_at,updated_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (block_id, *values))
        c.commit(); count = c.execute("SELECT COUNT(*) FROM rebooking_campaigns WHERE appointment_id=901").fetchone()[0]; c.close()
        self.assertEqual(count, 2)

    async def test_patient_cannot_preview_or_block_a_day(self):
        item = self.day_block(role="patient", requester_phone="5492665000000", override_authorized=False)
        with patch.object(app, "ea", side_effect=AssertionError("EA must not be called")):
            result = await app.day_block_tool(item, request())
        self.assertEqual(result["error"], "permission_denied")

    async def test_spoofed_admin_phone_is_rejected_server_side(self):
        item = self.day_block(role="admin", requester_phone="5492665999999", override_authorized=True)
        with patch.object(app, "ea", side_effect=AssertionError("EA must not be called")):
            result = await app.day_block_tool(item, request())
        self.assertEqual(result["error"], "permission_denied")

    async def test_expected_basic_auth_hash_rejects_other_basic_credentials(self):
        expected = hashlib.sha256(b"Basic expected").hexdigest()
        with patch.object(app, "EXPECTED_BASIC_AUTH_SHA256", expected), patch.object(app, "ea", side_effect=AssertionError("EA must not be called")):
            with self.assertRaises(app.HTTPException) as denied:
                await app.day_block_tool(self.day_block(action="status"), request())
        self.assertEqual(denied.exception.status_code, 401)

    async def test_new_endpoints_reject_unauthenticated_requests_before_reading_state(self):
        day = self.day_block(action="status")
        with self.assertRaises(app.HTTPException) as blocked:
            await app.day_block_tool(day, unauthenticated_request())
        self.assertEqual(blocked.exception.status_code, 401)
        reschedule = app.RescheduleIn(role="patient", requester_phone="5492665111111", message_id="unauth-r")
        with self.assertRaises(app.HTTPException) as moved:
            await app.reschedule_tool(reschedule, unauthenticated_request())
        self.assertEqual(moved.exception.status_code, 401)

    async def test_basic_header_is_validated_against_easyappointments(self):
        async def invalid_credentials(req, method, path, **kwargs):
            raise app.HTTPException(502, "EasyAppointments respondió HTTP 401")
        with patch.object(app, "ea", side_effect=invalid_credentials):
            blocked = await app.day_block_tool(self.day_block(action="status"), request())
            moved = await app.reschedule_tool(app.RescheduleIn(role="patient", requester_phone="5492665111111", message_id="invalid-basic"), request())
        self.assertEqual(blocked["error"], "authentication_failed")
        self.assertEqual(moved["error"], "authentication_failed")

    async def test_changed_appointments_require_fresh_day_block_confirmation(self):
        date = future_date(); state = {"rows": []}
        async def fake_ea(req, method, path, **kwargs): return {"id": 2} if path == "/providers/2" else state["rows"]
        with patch.object(app, "ea", side_effect=fake_ea):
            preview = await app.day_block_tool(self.day_block(date=date, message_id="preview-change"), request())
            state["rows"] = [{"id": 803, "start": f"{date} 10:00:00", "end": f"{date} 11:00:00", "status": "Booked", "serviceId": 1, "serviceName": "Consulta", "customer": {"firstName": "Turno", "lastName": "Nuevo", "phone": "5492665111111"}}]
            confirm = self.day_block(action="confirm", date=date, confirmed=True, message_id="confirm-change", proposal_id=preview["proposal_id"])
            result = await app.day_block_tool(confirm, request())
        self.assertEqual(result["error"], "day_block_conflicts_changed_confirmation_required")
        self.assertEqual(result["appointment_count"], 1)

    async def test_confirmation_cannot_reuse_preview_message(self):
        date = future_date(); rows = []
        async def fake_ea(req, method, path, **kwargs): return rows
        with patch.object(app, "ea", side_effect=fake_ea):
            preview = await app.day_block_tool(self.day_block(date=date, message_id="same-message"), request())
            result = await app.day_block_tool(self.day_block(action="confirm", date=date, confirmed=True, message_id="same-message", proposal_id=preview["proposal_id"]), request())
        self.assertEqual(result["error"], "confirmation_must_be_later_message")

    async def test_confirmation_requires_exact_proposal_and_later_timestamp(self):
        date = future_date(); rows = []
        async def fake_ea(req, method, path, **kwargs): return rows
        with patch.object(app, "ea", side_effect=fake_ea):
            preview = await app.day_block_tool(self.day_block(date=date, message_id="preview-uuid", event_timestamp=500), request())
            missing = await app.day_block_tool(self.day_block(action="confirm", date=date, confirmed=True, message_id="confirm-no-uuid", event_timestamp=501), request())
            stale = await app.day_block_tool(self.day_block(action="confirm", date=date, confirmed=True, message_id="confirm-stale", event_timestamp=500, proposal_id=preview["proposal_id"]), request())
        self.assertEqual(missing["error"], "proposal_id_required")
        self.assertEqual(stale["error"], "confirmation_must_be_later_message")

    async def test_changed_snapshot_dry_run_does_not_consume_or_refresh_proposal(self):
        date = future_date(); state = {"rows": []}
        async def fake_ea(req, method, path, **kwargs): return state["rows"]
        with patch.object(app, "ea", side_effect=fake_ea):
            preview = await app.day_block_tool(self.day_block(date=date, message_id="preview-dry-state", event_timestamp=700), request())
            state["rows"] = [{"id": 990, "start": f"{date} 10:00:00", "end": f"{date} 11:00:00", "status": "Booked", "providerId": 2, "serviceId": 1, "customerId": 2, "customer": {"id": 2, "phone": "5492665111111"}}]
            result = await app.day_block_tool(self.day_block(action="confirm", date=date, confirmed=True, message_id="confirm-dry-state", event_timestamp=701, proposal_id=preview["proposal_id"], dry_run=True), request())
        self.assertEqual(result["error"], "day_block_conflicts_changed_confirmation_required")
        c = app.db(readonly=True)
        consumed, count = c.execute("SELECT consumed_at,(SELECT COUNT(*) FROM pending_day_blocks) FROM pending_day_blocks WHERE proposal_id=?", (preview["proposal_id"],)).fetchone(); c.close()
        self.assertIsNone(consumed); self.assertEqual(count, 1)

    async def test_mutation_claim_is_exclusive_and_payload_bound(self):
        first = app.claim_mutation("claim:test", {"slot": "uno"})
        same = app.claim_mutation("claim:test", {"slot": "uno"})
        conflict = app.claim_mutation("claim:test", {"slot": "dos"})
        self.assertEqual(first["state"], "claimed")
        self.assertEqual(same["state"], "in_progress")
        self.assertEqual(conflict["state"], "conflict")
        app.finish_mutation("claim:test", {"ok": True})
        self.assertEqual(app.claim_mutation("claim:test", {"slot": "uno"})["state"], "completed")

    async def test_day_block_dry_run_has_zero_calendar_mutations(self):
        date = future_date(); rows = []
        calls = []
        async def fake_ea(req, method, path, **kwargs): calls.append((method, path)); return rows
        with patch.object(app, "ea", side_effect=fake_ea):
            result = await app.day_block_tool(self.day_block(date=date, message_id="preview-dry", dry_run=True), request())
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["blocked"])
        self.assertFalse(any(method != "GET" for method, _ in calls))
        c = app.db()
        for table in ("day_blocks", "pending_day_blocks", "mutation_claims", "tool_runs"):
            self.assertEqual(c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0, table)
        c.close()

    async def test_verified_day_block_queues_contacts_and_records_missing_phone(self):
        date = future_date(); rows = [
            {"id": 811, "start": f"{date} 10:00:00", "end": f"{date} 11:00:00", "status": "Booked", "serviceId": 1, "serviceName": "Consulta", "customer": {"firstName": "Con", "lastName": "Teléfono", "phone": "5492665111111"}},
            {"id": 812, "start": f"{date} 11:00:00", "end": f"{date} 12:00:00", "status": "Booked", "serviceId": 1, "serviceName": "Consulta", "customer": {"firstName": "Sin", "lastName": "Teléfono", "phone": ""}},
        ]
        async def fake_ea(req, method, path, **kwargs):
            if path == "/providers/2": return {"id": 2}
            if path == "/appointments": return rows
            if path == "/unavailabilities" and method == "GET": return []
            if path == "/unavailabilities" and method == "POST": return {"id": 55}
            if path == "/unavailabilities/55": return {"id": 55, "providerId": 2, "start": f"{date} 00:00:00", "end": f"{date} 23:59:59"}
            if path == "/services": return [{"id": 1}]
            if path == "/availabilities": return []
            raise AssertionError((method, path))
        with patch.object(app, "ea", side_effect=fake_ea):
            preview = await app.day_block_tool(self.day_block(date=date, message_id="preview-real", dry_run=False), request())
            result = await app.day_block_tool(self.day_block(action="confirm", date=date, confirmed=True, message_id="confirm-real", dry_run=False, proposal_id=preview["proposal_id"]), request())
        self.assertTrue(result["blocked"]); self.assertTrue(result["verified"])
        self.assertEqual(result["queued_contact_count"], 1); self.assertEqual(result["missing_phone_count"], 1)
        c = app.db(); statuses = dict(c.execute("SELECT appointment_id,status FROM rebooking_campaigns").fetchall()); c.close()
        self.assertEqual(statuses, {811: "queued", 812: "missing_phone"})

    async def test_reschedule_updates_same_appointment_and_verifies_readback(self):
        old_date = future_date(12); new_date = future_date(13)
        while datetime.strptime(new_date, "%Y-%m-%d").weekday() not in (1, 2, 3):
            new_date = (datetime.strptime(new_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        self.seeded_campaign(old_date)
        original = {"id": 901, "start": f"{old_date} 16:00:00", "end": f"{old_date} 17:00:00", "status": "Booked", "notes": "Original", "providerId": 2, "serviceId": 1, "customerId": 10, "customer": {"id": 10, "phone": "5492665111111"}}
        state = {"updated": False}; put_payload = {}
        async def fake_ea(req, method, path, **kwargs):
            if path == "/providers/2": return {"id": 2}
            if path == "/appointments/901" and method == "GET":
                return {**original, "start": f"{new_date} 16:00:00", "end": f"{new_date} 17:00:00"} if state["updated"] else original
            if path == "/availabilities": return [f"{new_date} 16:00:00"]
            if path == "/appointments" and method == "GET": return []
            if path == "/appointments/901" and method == "PUT": state["updated"] = True; put_payload.update(kwargs["json"]); return {"id": 901}
            raise AssertionError((method, path))
        item = app.RescheduleIn(role="patient", requester_phone="5492665111111", message_id="reschedule-real", date=new_date, time="16:00")
        with patch.object(app, "ea", side_effect=fake_ea): result = await app.reschedule_tool(item, request())
        self.assertTrue(result["confirmed"]); self.assertTrue(result["verified"])
        self.assertEqual(put_payload["start"], f"{new_date} 16:00:00")
        c = app.db(); status = c.execute("SELECT status FROM rebooking_campaigns WHERE appointment_id=901").fetchone()[0]; c.close()
        self.assertEqual(status, "rescheduled")

    async def test_reschedule_verification_failure_rolls_back_original_turn(self):
        old_date = future_date(40); new_date = future_date(41)
        while datetime.strptime(new_date, "%Y-%m-%d").weekday() not in (1, 2, 3):
            new_date = (datetime.strptime(new_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        self.seeded_campaign(old_date)
        original = {"id": 901, "start": f"{old_date} 16:00:00", "end": f"{old_date} 17:00:00", "status": "Booked", "providerId": 2, "serviceId": 1, "customerId": 10, "customer": {"id": 10, "phone": "5492665111111"}}
        state = {"record": dict(original), "puts": 0}

        async def fake_ea(req, method, path, **kwargs):
            if path == "/appointments/901" and method == "GET": return state["record"]
            if path == "/availabilities": return [f"{new_date} 16:00:00"]
            if path == "/appointments" and method == "GET": return []
            if path == "/appointments/901" and method == "PUT":
                state["puts"] += 1
                state["record"] = {**original, **kwargs["json"], "customer": original["customer"]}
                if state["puts"] == 1: state["record"]["serviceId"] = 99
                return {"id": 901}
            raise AssertionError((method, path))

        item = app.RescheduleIn(role="patient", requester_phone="5492665111111", message_id="reschedule-rollback", date=new_date, time="16:00")
        with patch.object(app, "ea", side_effect=fake_ea):
            result = await app.reschedule_tool(item, request())
        self.assertEqual(result["error"], "reschedule_verification_failed_rolled_back")
        self.assertTrue(result["rolled_back"]); self.assertEqual(state["puts"], 2)
        self.assertEqual(app.appointment_fingerprint(state["record"]), app.appointment_fingerprint(original))
        c = app.db(); status = c.execute("SELECT status FROM rebooking_campaigns WHERE appointment_id=901").fetchone()[0]; claims = c.execute("SELECT COUNT(*) FROM mutation_claims").fetchone()[0]; c.close()
        self.assertEqual(status, "contacted"); self.assertEqual(claims, 0)

    async def test_reschedule_aborts_when_notes_change_before_put(self):
        old_date = future_date(50); new_date = future_date(51)
        while datetime.strptime(new_date, "%Y-%m-%d").weekday() not in (1, 2, 3):
            new_date = (datetime.strptime(new_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        self.seeded_campaign(old_date)
        original = {"id": 901, "start": f"{old_date} 16:00:00", "end": f"{old_date} 17:00:00", "status": "Booked", "notes": "Original", "providerId": 2, "serviceId": 1, "customerId": 10, "customer": {"id": 10, "phone": "5492665111111"}}
        reads = {"appointment": 0}; puts = []
        async def fake_ea(req, method, path, **kwargs):
            if path == "/appointments/901" and method == "GET":
                reads["appointment"] += 1
                return original if reads["appointment"] == 1 else {**original, "notes": "Cambio concurrente"}
            if path == "/availabilities": return [f"{new_date} 16:00:00"]
            if path == "/appointments" and method == "GET": return []
            if method == "PUT": puts.append(kwargs["json"]); return {"id": 901}
            raise AssertionError((method, path))
        item = app.RescheduleIn(role="patient", requester_phone="5492665111111", message_id="reschedule-notes-race", date=new_date, time="16:00")
        with patch.object(app, "ea", side_effect=fake_ea): result = await app.reschedule_tool(item, request())
        self.assertEqual(result["error"], "original_appointment_changed")
        self.assertEqual(puts, [])

    async def test_reschedule_dry_run_never_puts_or_changes_campaign(self):
        old_date = future_date(20); new_date = future_date(21)
        while datetime.strptime(new_date, "%Y-%m-%d").weekday() not in (1, 2, 3):
            new_date = (datetime.strptime(new_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        self.seeded_campaign(old_date)
        original = {"id": 901, "start": f"{old_date} 16:00:00", "end": f"{old_date} 17:00:00", "status": "Booked", "providerId": 2, "serviceId": 1, "customerId": 10, "customer": {"id": 10, "phone": "5492665111111"}}
        calls = []
        async def fake_ea(req, method, path, **kwargs):
            calls.append((method, path))
            if path == "/providers/2": return {"id": 2}
            if path == "/appointments/901": return original
            if path == "/availabilities": return [f"{new_date} 16:00:00"]
            if path == "/appointments": return []
            raise AssertionError((method, path))
        item = app.RescheduleIn(role="patient", requester_phone="5492665111111", message_id="reschedule-dry", date=new_date, time="16:00", dry_run=True)
        before = app.db(); before_counts = {t: before.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("tool_runs", "mutation_claims", "pending_day_blocks")}; before.close()
        with patch.object(app, "ea", side_effect=fake_ea): result = await app.reschedule_tool(item, request())
        self.assertTrue(result["dry_run"]); self.assertFalse(result["confirmed"])
        self.assertFalse(any(method == "PUT" for method, _ in calls))
        c = app.db(); status = c.execute("SELECT status FROM rebooking_campaigns WHERE appointment_id=901").fetchone()[0]; c.close()
        self.assertEqual(status, "contacted")
        after = app.db(); after_counts = {t: after.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("tool_runs", "mutation_claims", "pending_day_blocks")}; after.close()
        self.assertEqual(before_counts, after_counts)


if __name__ == "__main__":
    unittest.main()
