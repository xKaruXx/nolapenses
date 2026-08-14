# Bloqueo de días y reagendación — Ana

## Contrato operativo

1. `gestionar_bloqueo_dia(action=preview)` consulta la agenda real y guarda una propuesta inmutable por 30 minutos, ligada al actor, UUID y timestamp confiable del mensaje de vista previa.
2. La respuesta enumera turnos, contactos disponibles y turnos sin teléfono. No modifica la agenda.
3. Sólo una confirmación explícita de Ana habilita `action=confirm`.
4. La confirmación debe llegar en otro mensaje. Antes de escribir se compara el snapshot completo de cada turno (ID, horario, servicio, paciente, teléfono y estado). Si cambió, se exige otra confirmación.
5. Se crea una `unavailability` de día completo en EasyAppointments y se verifica:
   - lectura por ID;
   - proveedor, inicio y fin exactos;
   - ausencia de slots para todos los servicios devueltos por el catálogo activo.
6. Recién después se crean campañas de contacto.
7. `/opt/nolapenses/ana-ops/ana_calendar_ops.py process-rebooking-outreach` procesa la cola:
   - relee cada turno desde EasyAppointments y suprime el contacto si cambió, fue cancelado o ya no existe;
   - respeta `ana_bot_blocklist`;
   - marca el registro como `sending` antes del envío para evitar duplicados;
   - no reintenta automáticamente un envío incierto;
   - avisa a Ana con un resumen, incluyendo paciente/hora/servicio cuando falta teléfono.
8. Cuando el paciente responde, `reagendar_turno_bloqueo` identifica la campaña por su teléfono, ofrece slots reales y actualiza el mismo `appointment_id` mediante `PUT`.
9. Un claim durable impide que dos confirmaciones muten la misma fecha o campaña a la vez.
10. El cambio sólo se confirma después de verificar ID, paciente, proveedor, servicio, estado, inicio, fin y ausencia de solapamientos. Si diverge, intenta restaurar y verificar el turno original; un resultado incierto se escala y no se reintenta automáticamente.

## Límites de autorización

- El contenedor no publica puertos al host; sólo es accesible en `n8n-net`.
- `ADMIN_PHONES` se valida del lado servidor. El `role` del JSON no alcanza para autorizar un bloqueo.
- `EXPECTED_BASIC_AUTH_SHA256` valida el header Basic exacto del credential de n8n antes de leer estado local.
- Configurar ambos valores en `/opt/nolapenses/ana-agent-tools/.env`; el archivo no se versiona.

## Estados de campaña

- `queued`: listo para contactar.
- `sending`: reclamado por un worker; no debe enviarse desde otro proceso.
- `contacted`: Evolution devolvió un identificador de mensaje.
- `missing_phone`: no existe destino; debe aparecer en el aviso a Ana.
- `suppressed`: el teléfono está en la lista de exclusión.
- `send_failed`: el envío falló o quedó incierto; requiere revisión manual.
- `source_changed`: el turno cambió, fue cancelado o desapareció antes del envío; no se contacta al paciente y requiere revisión manual.
- `rescheduled`: el mismo turno fue movido y verificado.

## Pruebas sin efectos reales

```bash
cd ops/ana-agent-tools
python3 -m unittest -v test_app.py

cd ../ana-ops
python3 -m unittest -v test_ana_calendar_ops.py

cd ../..
python3 ops/n8n/update_ana_day_blocking.py \
  --input /tmp/AnaAgentFinalV1-live.json \
  --output /tmp/AnaAgentFinalV1-day-block-candidate.json
```

Los tests reemplazan EasyAppointments y Evolution por dobles; no realizan `POST`, `PUT`, `DELETE` ni envíos reales. Los dry-run nuevos usan SQLite en modo read-only y tampoco escriben propuestas, claims, auditoría ni estados de campañas.

## Despliegue

1. Backup de:
   - `/opt/nolapenses/ana-agent-tools/`;
   - `/opt/nolapenses/ana-ops/`;
   - workflow `AnaAgentFinalV1` (el transformador lo hace antes del `PUT`).
2. Copiar `ops/ana-agent-tools/*` preservando el directorio `data/` existente y crear `.env` desde `.env.example` con permisos `0600`.
3. Ejecutar `docker compose up -d --build` y verificar `/healthz`.
4. Copiar `ops/ana-ops/ana_calendar_ops.py` y agregar la línea de cron incluida en `ops/ana-ops/cron.rebooking-outreach`.
5. Ejecutar primero `process-rebooking-outreach --dry-run`.
6. Aplicar el workflow con `python3 ops/n8n/update_ana_day_blocking.py --apply`.
7. Verificar que el workflow siga activo y que existan ambas herramientas.
8. Probar por webhook con `dry_run=true`; nunca usar fechas o pacientes reales para la prueba mutante.

## Rollback

- Restaurar los archivos del backup y reconstruir `ana-agent-tools`.
- Restaurar el JSON anterior de `AnaAgentFinalV1` por API.
- Eliminar la línea `ANA_REBOOKING_OUTREACH` del crontab.
- Las tablas SQLite son aditivas; no es necesario borrarlas para volver a la versión previa.
