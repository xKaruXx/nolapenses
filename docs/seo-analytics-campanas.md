# Nolapenses — SEO, analítica y campañas pagas

## Reglas editoriales para notas

Las notas de Nolapenses no son resúmenes automáticos de novedades. La fuente es el disparador; la nota tiene que traer criterio propio, mirada de negocio y una postura clara.

### Voz editorial

- Español rioplatense/LatAm, cercano, profesional y práctico.
- Opinativo sin ser soberbio.
- Sin hype tecnológico ni tono corporativo duro.
- Con foco en decisiones reales de negocio.
- La automatización aparece como herramienta para resolver un problema, no como fin en sí mismo.

### Enfoque obligatorio

- Arrancar desde una postura: qué importa, qué es ruido, qué riesgo hay y qué decisión conviene tomar.
- No empezar con un resumen neutro de la fuente si la bajada editorial todavía no está clara.
- Identificar primero el problema operativo real: consultas que se pierden, datos desordenados, procesos sin dueño, permisos mal definidos, respuestas inconsistentes, falta de seguimiento, costos invisibles, trazabilidad débil o derivación humana ausente.
- Después explicar cómo IA/automatización puede ayudar, con límites claros.
- Revisar título, excerpt y primer párrafo como si fueran una columna breve: menos neutralidad, más punto de vista.

### Evitar

- “la lectura práctica es clara”
- “la señal es clara”
- “la lección práctica”
- “la señal práctica es clara”
- “para una pyme...” como puente mecánico
- “transformación digital”
- “soluciones disruptivas”
- “revolucionar el negocio”
- enumerar novedades sin interpretación
- repetir “automatización” como palabra comodín

### Estructura sugerida

1. **Título:** con postura, no clickbait vacío.
2. **Excerpt/bajada:** 2 o 3 frases con qué importa y por qué debería importarle a un negocio.
3. **Introducción:** interpretación fuerte antes que resumen.
4. **Desarrollo:** contexto de la fuente, solo lo necesario.
5. **Bajada a negocio:** atención, WhatsApp, agenda, datos, permisos, seguimiento, equipo humano, costos o control.
6. **Cierre:** recomendación concreta o pregunta estratégica.

### Ejemplo de tono

En vez de:

> “Para una pyme, la lectura práctica es clara: no alcanza con esperar el modelo más potente...”

Preferir:

> “Lo de Sol, Terra y Luna sirve menos como carrera por el modelo de moda y más como recordatorio incómodo: si una empresa no tiene claro qué dato usa, quién decide y cuándo interviene una persona, cualquier modelo nuevo termina siendo solo ruido caro.”

## Reglas de imágenes para notas

- No usar imágenes verticales en notas.
- Formatos permitidos:
  - Horizontal 16:9 recomendado: `1600x900`, `1200x675` o similar.
  - Horizontal social/OG: `1200x630`.
  - Cuadrado permitido: `1080x1080`.
- Evitar verticales tipo `9:16`, `4:5`, `2:3` porque rompen las tarjetas del índice de notas.
- Guardar siempre en servidor bajo `/opt/nolapenses/web/assets/img/notas/`.
- Preferir WebP optimizado.
- El nombre del archivo debe describir la nota con slug, sin nombres genéricos.

## Convención UTM para campañas

Usar UTMs en todo link externo publicado en redes, anuncios, email o WhatsApp.

### Parámetros obligatorios

- `utm_source`: plataforma o fuente real.
- `utm_medium`: tipo de tráfico.
- `utm_campaign`: campaña agrupadora.

### Parámetros recomendados

- `utm_content`: variante creativa, pieza o ubicación.
- `utm_term`: palabra clave, audiencia o ángulo si aplica.

## Valores sugeridos

### Sources

- `facebook`
- `instagram`
- `linkedin`
- `whatsapp`
- `google`
- `newsletter`
- `direct_message`

### Mediums

- `paid_social` para anuncios Meta/LinkedIn.
- `organic_social` para publicaciones orgánicas.
- `cpc` para búsqueda paga.
- `referral` para links desde terceros.
- `message` para WhatsApp/DM manual.
- `email` para campañas de email/newsletter.

### Campaigns

Formato:

```text
YYYYMM_objetivo_segmento
```

Ejemplos:

```text
202607_leads_whatsapp_ia_san_luis
202607_contenido_ia_privada_pymes
202607_remarketing_visitas_notas
```

### Content

Formato:

```text
ubicacion-formato-angulo-variante
```

Ejemplos:

```text
feed-video-consultas-v1
stories-imagen-whatsapp-v2
linkedin-post-nota-ia-privada
```

## Ejemplos de URLs

Anuncio de Instagram a una nota:

```text
https://nolapenses.com.ar/notas/atencion-conversacional-ia-consultas-viajes-negocios/?utm_source=instagram&utm_medium=paid_social&utm_campaign=202607_leads_whatsapp_ia_san_luis&utm_content=feed-imagen-consultas-v1
```

Post orgánico de LinkedIn:

```text
https://nolapenses.com.ar/notas/ia-privada-conocimiento-interno-empresas/?utm_source=linkedin&utm_medium=organic_social&utm_campaign=202607_contenido_ia_privada_pymes&utm_content=post-nota-ia-privada
```

WhatsApp manual:

```text
https://nolapenses.com.ar/?utm_source=whatsapp&utm_medium=message&utm_campaign=202607_contacto_directo&utm_content=respuesta-manual
```

## Eventos GA4 importantes

Ya existe GA4 `G-PTMH8173DX`. Para análisis comercial mirar especialmente:

- `page_view`: visitas por landing/nota.
- `note_view`: lectura de nota.
- `note_whatsapp_click`: clic a WhatsApp desde nota.
- `note_source_click`: clic a fuente de la nota.
- `lead_chat_opened`: apertura del asistente.
- `lead_chat_submitted`: envío del lead desde chat.
- Eventos de la landing principal enviados por `assets/js/main.js`.

## Lectura recomendada en GA4

Para campañas pagas, revisar por:

- Session source / medium.
- First user source / medium.
- Campaign.
- Landing page + query string.
- Evento de conversión: WhatsApp, apertura chat, envío lead.
- Comparar nota/landing que inició la sesión contra evento final.

## SEO técnico mínimo por nota

Cada nota debe tener:

- `<title>` único y claro.
- `<meta name="description">` única.
- `<link rel="canonical">` absoluto.
- `og:title`, `og:description`, `og:url`, `og:image`.
- JSON-LD `Article` con headline, description, image, dates, author y publisher.
- Un solo `<h1>`.
- Imagen con `alt` descriptivo.
- Link interno hacia WhatsApp o página principal con UTM si viene de campaña externa.
- Estar incluida en `/sitemap.xml`.

## Nota sobre robots.txt

No bloquear `/assets/css/` ni `/assets/js/`: Google necesita renderizar CSS/JS para evaluar mobile friendliness, contenido visible y experiencia de página.
