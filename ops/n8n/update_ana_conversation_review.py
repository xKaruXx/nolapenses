#!/usr/bin/env python3
"""Prepare Ana's conversation UX improvements for review.

This transform is intentionally non-deploying: it edits an exported workflow and
writes a candidate JSON. It does not call n8n, Evolution or EasyAppointments.
The ambiguous weekly schedule is deliberately excluded.
"""
from __future__ import annotations

import argparse
import json
import pathlib

CONTEXT_NODE = "Preparar contexto agente directo"
CONFIG_NODE = "Configurar testing y avisos"
VERSION = "v1.2-conversation-review"
MARKER = "REGLAS UX ANA SEPTIEMBRE 2026"
RULES = """# REGLAS UX ANA SEPTIEMBRE 2026
Para pacientes, la respuesta normal debe tener entre 1 y 4 líneas, una idea principal y una sola pregunta concreta. Usá dos preguntas únicamente si son inseparables. No repitas saludos ni datos ya conocidos.
Mostrá el menú inicial sólo cuando la conversación empieza sin intención clara, el mensaje es demasiado ambiguo o la persona pide opciones. No lo repitas después de cada respuesta.
Menú inicial: 1. Sacar o gestionar un turno; 2. Consultar valores o coseguros; 3. Tengo una urgencia; 4. Hablar con Ana. Aclarale que también puede escribir libremente.
Al gestionar un turno, si todavía no se conoce la práctica, ofrecé: 1. Consulta; 2. Arreglo simple; 3. Limpieza; 4. Tratamiento de conducto; 5. Incrustación; 6. No estoy seguro/a.
Si elige “No estoy seguro/a”, no diagnostiques: ofrecé una consulta de evaluación. Si menciona dolor fuerte, hinchazón, infección, sangrado o traumatismo, tratá el caso como urgente.
Para valores o coseguros preguntá sólo si es particular u obra social y qué práctica consulta cuando haga falta. Respondé únicamente con operational_catalog; si no hay valor confirmado, derivá sin inventar.
Ofrecé como máximo tres horarios reales por mensaje. Nunca muevas, adelantes ni contactes a pacientes ya agendados para rellenar otro hueco.
No incorpores todavía la grilla manuscrita ni reglas de liberación de cupos: están pendientes de validación escrita de Ana.
# FIN REGLAS UX ANA SEPTIEMBRE 2026
"""


def node(workflow: dict, name: str) -> dict:
    matches = [item for item in workflow.get("nodes", []) if item.get("name") == name]
    if len(matches) != 1:
        raise RuntimeError(f"Se esperaba exactamente un nodo {name!r}; encontrados: {len(matches)}")
    return matches[0]


def transform(workflow: dict) -> dict:
    context = node(workflow, CONTEXT_NODE)
    code = context.get("parameters", {}).get("jsCode")
    if not isinstance(code, str):
        raise RuntimeError("El nodo de contexto no contiene jsCode")
    if MARKER not in code:
        anchor = "Sos la asistente virtual del consultorio de Ana Maldonado. Rol confiable: ${role}. Español rioplatense, claro y breve.\n"
        if anchor not in code:
            raise RuntimeError("No se encontró el ancla segura del prompt")
        code = code.replace(anchor, anchor + RULES, 1)
    context["parameters"]["jsCode"] = code

    config = node(workflow, CONFIG_NODE)
    config_code = config.get("parameters", {}).get("jsCode")
    if not isinstance(config_code, str):
        raise RuntimeError("El nodo de configuración no contiene jsCode")
    import re
    updated, count = re.subn(r"version:\s*'v[^']+'", f"version: '{VERSION}'", config_code, count=1)
    if count != 1:
        raise RuntimeError("No se encontró una única versión de configuración")
    config["parameters"]["jsCode"] = updated
    return workflow


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    workflow = json.loads(args.input.read_text())
    transformed = transform(workflow)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(transformed, ensure_ascii=False, indent=2))
    args.output.chmod(0o600)
    print(json.dumps({"output": str(args.output), "version": VERSION, "nodes": len(transformed.get("nodes", []))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
