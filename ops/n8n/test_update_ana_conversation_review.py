import copy
import json
import pathlib
import tempfile
import unittest

import update_ana_conversation_review as update


def fixture():
    return {
        "nodes": [
            {
                "name": update.CONTEXT_NODE,
                "parameters": {
                    "jsCode": "const baseRules=`Sos la asistente virtual del consultorio de Ana Maldonado. Rol confiable: ${role}. Español rioplatense, claro y breve.\nRegla existente.`;"
                },
            },
            {
                "name": update.CONFIG_NODE,
                "parameters": {"jsCode": "const CONFIG = { version: 'v1.1-day-blocking-rebooking' };"},
            },
        ],
        "connections": {},
    }


class ConversationReviewTransformTests(unittest.TestCase):
    def test_loads_singleton_cli_export(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "workflow.json"
            path.write_text(json.dumps([fixture()]))
            self.assertEqual(update.load_workflow(path), fixture())

    def test_rejects_multi_workflow_cli_export(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "workflow.json"
            path.write_text(json.dumps([fixture(), fixture()]))
            with self.assertRaisesRegex(RuntimeError, "único workflow"):
                update.load_workflow(path)

    def test_adds_validated_conversation_rules_without_schedule(self):
        result = update.transform(fixture())
        code = result["nodes"][0]["parameters"]["jsCode"]
        self.assertIn(update.MARKER, code)
        self.assertIn("entre 1 y 4 líneas", code)
        self.assertNotIn("4. Hablar con Ana", code)
        self.assertIn("reactivación siguen pendientes", code)
        self.assertIn("No estoy seguro/a", code)
        self.assertIn("operational_catalog", code)
        self.assertIn("pendientes de validación escrita", code)
        self.assertNotIn("Lunes y viernes", code)
        self.assertNotIn("Miércoles", code)

    def test_updates_version(self):
        result = update.transform(fixture())
        config = result["nodes"][1]["parameters"]["jsCode"]
        self.assertIn("version: 'v1.2-conversation-review'", config)

    def test_is_idempotent(self):
        once = update.transform(fixture())
        twice = update.transform(copy.deepcopy(once))
        self.assertEqual(once, twice)
        code = twice["nodes"][0]["parameters"]["jsCode"]
        self.assertEqual(code.count(update.MARKER), 2)  # apertura y cierre

    def test_fails_closed_when_prompt_anchor_changes(self):
        broken = fixture()
        broken["nodes"][0]["parameters"]["jsCode"] = "const baseRules=`otro prompt`;"
        with self.assertRaisesRegex(RuntimeError, "ancla segura"):
            update.transform(broken)

    def test_fails_closed_on_duplicate_target_node(self):
        broken = fixture()
        broken["nodes"].append(copy.deepcopy(broken["nodes"][0]))
        with self.assertRaisesRegex(RuntimeError, "exactamente un nodo"):
            update.transform(broken)


if __name__ == "__main__":
    unittest.main()
