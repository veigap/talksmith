# Thesis

Fixture Talk for the Step-6 ASCII -> SVG pipeline. Not a real talk. Every slide below is
lifted verbatim — art, prose and speaker notes — from a production Talk, picked to span the
shapes and edge cases the render + critique loop has to survive. One slide per section, so
each block gets a stable `sN-1-1` id. See README.md for what each one is for.

# 1. hiperparametros-ai · s3-2-1

**Goal of this section:** widest, thinnest art (~7.9:1) — the frame is easy to over-declare here

## 1. Top-p: la otra forma de dar variedad

### Content

- Top-p (o "nucleus") es una perilla alternativa a la temperatura: en vez de subir el azar, *recorta la lista* de candidatos.
- Top-p = 0.9 → el modelo solo considera los candidatos que juntos suman el 90% de la confianza, y descarta la "cola" improbable.
- Regla práctica clave: se toca *una u otra*, no las dos a la vez — combinarlas suele ser contraproducente.
- Negocio: mismo eje que la temperatura (variedad vs. control); en la práctica muchos equipos ajustan solo una.
- Ojo: en los **modelos de razonamiento** (los que "piensan" antes de responder) varios proveedores **deshabilitan** estas perillas — el modelo fija temperatura y top-p internamente y no las podés tocar.

```ascii
  Lista completa de candidatos (por confianza):
   azul  gris  claro  celeste  turquesa  ...cola larga...

  top_p = 0.9  ->  |<-- se queda con esto -->|  x x x x
                     (los que suman 90%)       descarta la cola
```
<!-- ascii-note:
intent: mostrar que top-p recorta la cola larga de candidatos improbables, quedándose con el núcleo que suma p
emphasize: la frontera del corte al 90%; la "cola larga" descartada con equis
labels: fila de candidatos ordenados, "top_p = 0.9", "se queda con esto (los que suman 90%)", "descarta la cola"
-->

**Disponibilidad de top-p por proveedor** (verificar contra la doc vigente de cada proveedor):

| Proveedor | top-p en la API | En modelos de razonamiento |
|---|---|---|
| OpenAI (GPT) | Sí | Deshabilitado (queda fijo) |
| Anthropic (Claude) | Sí — se ajusta temperatura *o* top-p, no ambos | Deshabilitado con *extended thinking* |
| Google (Gemini) | Sí (`topP`) | Disponible |

### Sources

- research/corpus/parametros-llm.md.md (top_p nucleus sampling, 0.9 típico; se usa EN LUGAR DE temperature, no en conjunto; regla general de Claude: alterar temperature o top_p, no ambos)
- research/corpus/parametros-llm.md.md (RL/RLHF: por qué se deshabilita el sampling —temperatura/top-p— en modelos de razonamiento) — respalda la columna "modelos de razonamiento".
- Disponibilidad exacta por proveedor/modelo: conocimiento de dominio del presenter, **a verificar** contra la doc vigente — los nombres y defaults por modelo NO están verificados en el corpus.

### Speaker notes

Segunda perilla, y la presento como "la prima de la temperatura". Persigue el mismo objetivo — controlar variedad — pero con otro mecanismo: en vez de subir el azar, recorta la lista de candidatos y descarta la cola de opciones raras. Top-p 0.9 significa "quedate con las opciones que entre todas suman el 90% de la confianza". El punto de negocio más accionable de este slide: se ajusta *una u otra*, temperatura o top-p, nunca las dos juntas — es un error común que degrada resultados. Para la audiencia de negocios, el takeaway es: si un proveedor te habla de "top-p", es la misma decisión de variedad-vs-control que ya entendiste con temperatura. No necesito que sepan la mecánica fina; necesito que no se asusten cuando la vean. Cierro con una aclaración importante: en los modelos de razonamiento varios proveedores bloquean estas perillas (las fijan internamente); dejo la tabla de disponibilidad por proveedor como referencia, aclarando que hay que verificarla contra la doc vigente porque cambia seguido.

### Presenter feedback

---

# 2. claude-cowork · s2-3-1

**Goal of this section:** wide left-to-right flow (~7.2:1)

## 1. Conectores y MCP: las "manos" del chat

### Content

- Conectores = **las "manos"**: lo que la IA puede tocar que de otro modo no podría (Drive, Gmail, Calendar, Slack, bases de datos).
- **MCP**: el estándar detrás. Cualquier app con servidor MCP se vuelve conversacional.
- Un equipo técnico puede armar **conectores propios** (custom, vía MCP).

```ascii
+--------+   pide datos    +-----------+   protocolo   +--------------+
| CHAT / | --------------> | Connector |  -- MCP -->   | Servicio ext |
| agente |                 |  (1 clic) |               | Gmail/Calendar|
+--------+ <-------------- +-----------+ <-----------  +--------------+
            devuelve datos
```
<!-- ascii-note:
intent: mostrar el flujo de una llamada a un Connector: el chat/agente pide datos, el Connector traduce vía el protocolo MCP, el servicio externo responde.
emphasize: la etiqueta "MCP" sobre la flecha del medio; el Connector como puente de un clic.
labels: Chat/agente -> Connector (1 clic) -> Servicio externo (Gmail / Calendar); flecha de ida "pide datos", flecha de vuelta "devuelve datos".
-->

### Sources

- corpus/agentic-ai-deck.zip.md — definición de Connector (MCP): "The hands"; slide 5.4 (rango de MCP; "any app that exposes an MCP server").
- "corpus/mision - auto.zip.md" — MT Newswires "ya tiene un connector listo" (Step 2.1); Gmail connector de un clic (M3).
- Model Context Protocol (sitio oficial del estándar): https://modelcontextprotocol.io — qué es MCP y cómo las plataformas exponen herramientas; base de los conectores personalizados.
- Anthropic Support — Getting started with custom connectors using remote MCP: https://support.claude.com/en/articles/11175166-getting-started-with-custom-connectors-using-remote-mcp — los conectores personalizados existen y se agregan vía MCP (mención, sin profundizar).

### Speaker notes

Desarmar el miedo: conectar un servicio externo le da "manos" al chat, sin programar nada. Usar el diagrama para explicar qué pasa por debajo: la IA pide datos y el conector los trae vía MCP (Model Context Protocol), el estándar que vuelve conversacional a cualquier plataforma con API. El patrón: la plataforma abre sus internals como herramientas. Mencionar dos o tres ejemplos del ecosistema (Figma, Vercel, Cal.com, Home Assistant) y seguir. Decir al pasar que un equipo técnico puede desarrollar conectores propios (custom, vía MCP); a nivel usuario alcanza con el directorio, que viene en la próxima slide. Los ejemplos guía de la sección son mail y calendario, porque son los que la audiencia ya tiene. Tiempo objetivo: ~8 min.

### Presenter feedback
- [closed] 2026-06-09 — "Esto - **Cómo se llama / registra un Connector.** En Cowork hay un **directorio de Connectors** con conexión de un clic ("Connect"), configurado por la UI de Settings — no hay archivo local que editar. Ejemplo (Atlas): **MT Newswires** ya tiene un connector listo; lo buscás y le das Connect, como cualquier app. Gmail, igual: un clic en el directorio. vamos a moverlo a un nuevo slide."
  Resolution: SPLIT: el bloque 'Como se llama/registra un Connector' se movio de 4.1 a una nueva slide 4.2 'Como se registra un Connector' (directorio de Connectors, conexion de un clic 'Connect', ejemplo MT Newswires + Gmail). Cableadas las dos imagenes nuevas images/connectors_directory.png y images/connector_browser.png. 4.1 queda con lo conceptual (Connectors + MCP) y un puntero a la slide siguiente; Schedule renumerada 4.2->4.3.
  - Added two images to include in this slide: connectors_directory.png & connector_browser

---

# 3. claude-cowork · s5-3-1

**Goal of this section:** no ascii-note — exercises the sparse-context path

## 1. Instrucciones: el contrato

### Content

- Instrucciones = el **"contrato de trabajo"**: reglas en lenguaje natural que valen para todo, sin repetirlas.
- Ejemplo (Atlas):

```text
Sos Atlas, el analista de mercado de un equipo de trabajo.
Preparás un pulso semanal para colegas NO técnicos (incluido el jefe),
que se lee en 2 minutos antes de la reunión de los lunes.

· REGLA DE ORO: tus reportes son informativos y de uso interno.
  NUNCA son recomendaciones de inversión ni asesoramiento financiero.
  Siempre incluís esa aclaración al final.
```

### Sources

- corpus/agentic-ai-deck.zip.md — "the project context panel (GUI)" como lugar de las Instrucciones en Cowork; matriz de disponibilidad 3.3 (Persistent instructions, Cowork ⚠️).
- "corpus/mision - auto.zip.md" — texto exacto de las Project Instructions de Atlas (Step 1.1); "las Instrucciones son su contrato de trabajo".

### Speaker notes

Conectar con el paradigma: en lugar de re-explicarle el contexto cada vez, lo escribís una vez y vale para todo el Project. Mostrar el texto real de las Instrucciones de Atlas. Leer en voz alta lo que no entró en la lámina: Atlas sigue Apple, Microsoft y Nvidia, escribe en español claro y breve, sin jerga financiera, y si usa un término técnico lo explica en una línea. Destacar la regla de oro del disclaimer: acá van las reglas no negociables. Consejo de escritura: cortas y claras, en lenguaje natural. Dónde viven: en el panel de contexto del Project. No es un archivo que edités a mano; lo escribís en el panel y queda asociado al Project. Tiempo objetivo: ~7 min.

### Presenter feedback
- [closed] 2026-06-09 — "Sacar "En Cowork viven en el panel de contexto del Project (la GUI), no en un archivo `.md` editable. Equivalen al `CLAUDE.md` de Claude Code — mismo concepto, distinto mecanismo." Dejarlo en las notas. Re-revisa que la audiencia no tiene contacto con Claude Code asi que es conveniente no connectar o mencionar en el resto de la presentacion."
  Resolution: Removida de Content la frase 'En Cowork viven en el panel de contexto del Project (la GUI), no en un archivo .md editable. Equivalen al CLAUDE.md de Claude Code...'. Movida a Speaker notes en forma neutral ('viven en el panel de contexto del Project, no es un archivo que edites') SIN la equivalencia con Claude Code/CLAUDE.md, por la directiva de minimizar Claude Code fuera de la Seccion 1. Tambien limpiada la mencion a CLAUDE.md en Sources.
- [closed] 2026-06-09 — "Agregar un ejemplo en el slide de que podria ser un Instructions."
  Resolution: Agregado en Content un bloque de ejemplo concreto de Project Instructions (Atlas, de corpus/'mision - auto.zip.md'): quien es Atlas, empresas que sigue (Apple/Microsoft/Nvidia), audiencia no tecnica, tono espanol sin jerga, y la REGLA DE ORO 'nunca recomendaciones de inversion / no asesoramiento financiero'.

- [closed] 2026-07-15 — "Slides has too much text. Mix de compactar sin perder el objetivo de la slide y partir en 2 slides."
  Resolution: COMPACTAR 5.3 (ex 5.2). Título "Instrucciones: ajustar el comportamiento sin repetirte" (54c) → "Instrucciones: el contrato" (26c): el título ya cargaba en prosa lo que el primer bullet define, y "el contrato" es el ancla que la lámina y las notes usan. Estaba sobre el techo de densidad con 4 bloques (bullet + fence ```text de 12 líneas + un párrafo indentado + 2 bullets más); quedan 2 (el bullet del contrato y el ejemplo). El fence ```text SE CONSERVA: lo pidió el [closed] del 2026-06-09 ("Agregar un ejemplo en el slide de que podria ser un Instructions"), pero se recortó a las líneas que cargan el punto, quién es Atlas y la REGLA DE ORO. Los tres bullets de estilo de adentro del ejemplo (empresas que sigue, español sin jerga, explicar el término técnico) bajan a Speaker notes, que ahora indican leerlos en voz alta: el ejemplo sigue completo en el guion. Quitados los tres bullets de cierre: "Se escribe una vez; vale para todo el Project" repetía el bullet 1; "Cortas y claras" es narración y pasa a notes; "El lugar de las reglas no negociables" ya lo demuestra la REGLA DE ORO dentro del ejemplo, y se dice en voz alta. El [closed] del 2026-06-09 sobre CLAUDE.md sigue respetado: las notes dicen dónde viven las Instrucciones sin nombrar Claude Code. Notes de 86 a 121 palabras (crecieron por el ejemplo que bajó).

---

# 4. seguridad-governance-ai · sc-4-1

**Goal of this section:** from the 2026-07-15 production run

## 1. Controller vs. processor

### Content

```ascii
RESPONSABLE  --(datos + instrucciones)-->  ENCARGADO
(tu empresa)                               (proveedor IA)
     |                                          |
     +-----------  DPA (Art. 28)  --------------+
       el contrato obligatorio que regula
       la relacion
```
<!-- ascii-note:
intent: relacion legal responsable (controller) / encargado (processor) bajo GDPR, con el DPA como contrato obligatorio que la une
emphasize: el DPA como puente/candado entre las dos cajas; "tu empresa" = responsable, "proveedor IA" = encargado
labels: flecha superior = flujo de datos + instrucciones; llave inferior = DPA (Art. 28)
-->

- **Responsable**: decide *qué* datos y *para qué* → responsabilidad principal.
- Responsable
- Encargado

### Sources

- corpus/gdpr-explicado.md.md (diagrama responsable/encargado/DPA — reutilizado)
- corpus/registro-sesion-chat.md.md (controller vs. processor)

### Speaker notes

Backup. La prueba para distinguir roles: ¿quién decide para qué se usan los datos? Con IA: tu empresa es responsable, el proveedor es encargado — y esa relación *legalmente requiere* un DPA. "¿Tiene DPA?" es la línea que separa IA gobernada de shadow AI. El DPA convierte "confío en que el proveedor se porte bien" en "está legalmente obligado — y puedo auditarlo".

### Presenter feedback

---

# 5. seguridad-governance-ai · s1-10-1

**Goal of this section:** the mis-declared viewBox (declared 2.30:1, art wanted ~2.91:1) — aspect-audit regression

## 1. Las dos caras de la seguridad

### Content

```ascii
   LO QUE IMAGINAMOS            LO QUE PASA DE VERDAD
+----------------------+     +------------------------+
| CARA 1: EL ATAQUE    |     | CARA 2: LAS PROMESAS   |
| hackers, malware     |     | incumplidas            |
| el candado roto      |     | datos fuera de control |
|                      |     | la puerta abierta      |
+----------------------+     +------------------------+
          ^                             ^
  casi todos miran aca          la IA golpea aca
```
<!-- ascii-note:
intent: contrastar las dos caras de la seguridad — ataque externo vs. promesas incumplidas (compliance) — como tesis de la charla
emphasize: la columna derecha (Cara 2) es la que importa; la flecha "la IA golpea aca" debe dominar visualmente
labels: izquierda = imaginario colectivo (candado roto), derecha = realidad con IA (puerta abierta)
-->

> *"Una falla de seguridad no siempre tiene un atacante. A veces sos vos incumpliendo lo que prometiste."*

### Sources

- corpus/apertura-samsung-storyboard.md.md (slide 9 — "si se llevan un solo slide, es este")
- corpus/security-ai-managers-agenda.md.md (encuadre las dos caras + frase para la lámina)
- corpus/registro-sesion-chat.md.md (concepto rector)

### Speaker notes

La tesis. "La seguridad tiene dos caras: protegerte de los que atacan, **y** cumplir lo que prometiste. Lo de Samsung — y lo que va a pasar en sus empresas — vive en la derecha: datos que se escapan por decisiones cotidianas y bienintencionadas, y promesas de confidencialidad que se rompen sin que nadie 'entre' a robar nada. La IA golpea sobre todo la segunda. Y esa es la que casi nadie está mirando." Indicación del storyboard: si se llevan un solo slide, es este.

### Presenter feedback

---

# 6. claude-cowork · s7-3-1

**Goal of this section:** widest lines (99 chars), dense two-panel

## 1. Anatomía de un SKILL.md

### Content

- Un `SKILL.md` por dentro: es el `.md` con metadata de la sección 6, abierto.

```ascii
+--------------------------------------------------------------+
| ---                                                          |  <-- METADATA / HEADER (YAML)
| name: reporte-semanal                                        |      "que es" + "cuando se activa"
| description: Genera el pulso semanal de mercado a partir     |
|   de la carpeta fuentes/ de la semana. Usar cuando pidan     |
|   "reporte semanal" o "pulso de la semana".                  |
| ---                                                          |
+--------------------------------------------------------------+
| # Reporte semanal                                            |  <-- CUERPO (Markdown)
|                                                              |      "que hace": las instrucciones
| 1. Leé TODOS los archivos de fuentes/ y consolidá           |
|    por empresa.                                              |
| 2. Generá el reporte con esta estructura exacta...          |
| 3. Guardá con sufijo -new (no pises el original).           |
+--------------------------------------------------------------+
```
<!-- ascii-note:
intent: mostrar la anatomía de un SKILL.md — un bloque de metadata (YAML frontmatter: name + description) arriba y el cuerpo de instrucciones en Markdown abajo. Refuerza el beat de archivos .md/metadata de la sección Cowork.
emphasize: la separación visual en dos zonas — METADATA/HEADER (name, description; "qué es / cuándo se activa") vs CUERPO (las instrucciones; "qué hace"); que la `description` es lo que dispara la Skill.
labels: zona superior = metadata/header (YAML, name + description); zona inferior = cuerpo (instrucciones en Markdown); etiquetas laterales "cuándo se activa" y "qué hace".
-->

- La `description` activa la Skill por **sentido**, no por palabra clave.

### Sources

- corpus/agentic-ai-deck.zip.md — definición de Skill (SKILL.md con YAML frontmatter: name + description; "Description drives triggering — semantic, not keyword").
- "corpus/mision - auto.zip.md" — la Skill `reporte-semanal` (entrada `fuentes/`, consolida por empresa, estructura fija, sufijo `-new`).

### Speaker notes

Slide-ejemplo que aterriza dos cosas a la vez: la anatomía de una Skill y el beat de archivos `.md` + metadata de la sección 6. Mostrar el `SKILL.md` partido en dos zonas: arriba el header YAML entre `---`, con `name`, que identifica, y `description`, que decide cuándo se activa; abajo el cuerpo, Markdown común, los pasos que sigue el agente. El punto a fijar: el sistema lee la `description` para decidir si esta Skill aplica a tu pedido, por sentido y no por palabra clave. Usar `reporte-semanal` para que sea concreto. Mantenerlo alto nivel: es para que vean cómo se ve, no un tutorial de formato. Tiempo objetivo: ~3-4 min.

### Presenter feedback

- [closed] 2026-07-15 — "Slides has too much text. Mix de compactar sin perder el objetivo de la slide y partir en 2 slides." (origin: presenter-chat)
  Resolution: COMPACTAR 7.3 (ex 7.2). Título "Anatomía de un SKILL.md" (23c) intacto; la lámina estaba sobre el techo de densidad por bloques (1 bullet + diagrama + 2 bullets). Salieron los 2 bullets de cierre ("**Metadata:** `name` identifica; `description` decide cuándo se activa" y "**Cuerpo:** Markdown común, los pasos que sigue el agente"): son la leyenda que el diagrama ya carga rotulada en sus dos zonas, y su ascii-note las nombra enteras en `emphasize` ("la separación visual en dos zonas — METADATA/HEADER vs CUERPO"). Ya vivían en notes ("arriba el header YAML, abajo las instrucciones en Markdown"), así que fue merge; se les sumó `name` identifica y "los pasos que sigue el agente" para no perder ni un matiz. Se conserva en lámina lo único que el ASCII NO dice: que la `description` activa por sentido y no por palabra clave (el `emphasize` dice que la `description` dispara la Skill, no que lo hace de forma semántica). Quedan 2 bloques: 1 bullet + diagrama + 1 bullet de remate. Cross-ref stale corregido: "Es el `.md` con metadata de la sección 4" → sección 6, que es donde vive hoy el beat de archivos `.md` (6.1 y 6.2); misma corrección en la primera línea de Speaker notes. Notes de 91 a 110 palabras: crecieron a propósito, es el destino de la leyenda que bajó, y siguen bajo las ~120. ASCII y ascii-note sin tocar.

---

# 7. seguridad-governance-ai · s2-2-1

**Goal of this section:** from the 2026-07-15 production run

## 1. PII vs. Personal Data

### Content

- **PII — Personally Identifiable Information**: lo que identifica a una persona **directamente**. Ejemplos: nombre, DNI / pasaporte, email, teléfono, foto del rostro, legajo.
- Error típico: "le saqué el nombre, ya no es personal" — falso si se puede reidentificar.

```ascii
+---------------------------------------------+
|  PERSONAL DATA (la categoria legal amplia)  |
|  todo lo vinculable a una persona:          |
|  IP, ubicacion, comportamiento,             |
|  inferencias...                             |
|                                             |
|     +-------------------------------+       |
|     |  PII (Personally              |       |
|     |  Identifiable Information)    |       |
|     |  identifica directamente:     |       |
|     |  nombre, DNI, email,          |       |
|     |  telefono, foto, legajo       |       |
|     +-------------------------------+       |
+---------------------------------------------+
```
<!-- ascii-note:
intent: mostrar que PII es un subconjunto de Personal Data (relacion de inclusion); terminos en ingles, sin nombrar ninguna ley
emphasize: el rectangulo exterior (Personal Data) es mucho mas grande que el interior (PII)
labels: exterior = Personal Data (la categoria legal amplia), interior = PII (Personally Identifiable Information)
-->



### Sources

- corpus/presenter-outline-esquema-slides-2026-07-06.md.md (S5)
- corpus/gdpr-explicado.md.md (definición de datos personales)
- corpus/registro-sesion-chat.md.md (PI vs PII)

### Speaker notes

Desplegar la sigla: PII — Personally Identifiable Information — es lo que identifica a una persona directamente: nombre, DNI o pasaporte, email, teléfono, la foto del rostro, el legajo. Personal Data es la categoría legal amplia: todo lo vinculable — IP, ubicación, comportamiento, incluso inferencias. **No son sinónimos: PII es un subconjunto de Personal Data.** Los dos términos quedan en inglés porque así van a aparecer en las herramientas y contratos que la sala va a manejar; la prosa sigue en español. No nombrar ninguna ley todavía: la norma detrás de "Personal Data" llega con nombre y artículo en la sección de estándares (GDPR). El error típico del manager: creer que anonimizó porque sacó el nombre; si el dato permite reidentificar, sigue siendo Personal Data y sigue protegido. Este concepto vuelve como Mito 4 del rompemitos.

### Presenter feedback
- [closed] 2026-07-06 — "Expander en la presentacion la definicion de PII."
  Resolution: Definición de PII expandida en lámina: sigla desplegada (Personally Identifiable Information) más ejemplos — nombre, DNI/pasaporte, email, teléfono, foto del rostro, legajo — en bullets y en el diagrama.
- [closed] 2026-07-06 — "No mencionar (GDPR) en la presetacion es este momento."
  Resolution: Quitado el namecheck GDPR del slide (diagrama y prosa): el conjunto exterior pasa a «Personal Data (la categoría legal amplia)» sin nombrar ley; GDPR se nombra recién en la Sección 9 — speaker notes ajustadas para decir que la norma llega después.
- [closed] 2026-07-06 — "Es DATOS PERSONALES igual a PI ? Si es asi, dejar todo en ingles por ahora."
  Resolution: PII ≠ Personal Data: PII es el subconjunto que identifica directamente (la distinción es el punto del slide y el Mito 4 depende de ella); ambos términos estandarizados en inglés en lámina (PII / Personal Data), prosa en español; diagrama, ascii-note, Mito 4 y goal de la Sección 2 actualizados.

---

# 8. claude-cowork · s4-5-1

**Goal of this section:** tallest, densest art (84x29)

## 1. Bloques que se apilan

### Content

- **Bloques que se apilan**: no es una escalera; usás solo los que necesitás.
- El mapa de la charla: ya recorrimos los tres primeros y **estamos acá**. Volvé para ubicarte.
- **Plugins** = capa transversal de distribución (sección 7).

```ascii
+============== PLUGINS (capa transversal: empaquetan y distribuyen) ==============+
||                                                                                ||
||  +----------------------+  "quiero compartir el resultado vivo"                ||
||  | LIVE ARTIFACTS       |                                                      ||
||  +----------------------+                                                      ||
||  +----------------------+  "no quiero repetir la tarea / delegar en paralelo"  ||
||  | SKILLS / SUBAGENTES  |  (avanzado, seccion 7)                               ||
||  +----------------------+                                                      ||
||  +----------------------+  "quiero que la IA entienda mi material"             ||
||  | ARCHIVOS .MD         |                                                      ||
||  +----------------------+                                                      ||
||  +----------------------+  "contexto fijo + todo en un lugar"                  ||
||  | INSTRUCCIONES +      |                                                      ||
||  | PROJECTS             |                                                      ||
||  +----------------------+                                                      ||
||  +----------------------+  "quiero que trabaje sobre mis archivos"   <== ACA   ||
||  | COWORK: carpetas     |                                                      ||
||  +----------------------+                                                      ||
||  +----------------------+  "quiero que corra solo"                   (visto)   ||
||  | TAREAS PROGRAMADAS   |                                                      ||
||  +----------------------+                                                      ||
||  +----------------------+  "quiero info real + que actue"            (visto)   ||
||  | CONECTORES           |                                                      ||
||  +----------------------+                                                      ||
||  +----------------------+  "respondia solo de memoria"               (visto)   ||
||  | EL CHAT              |                                                      ||
||  +----------------------+                                                      ||
+==================================================================================+
   los bloques se apilan (cada uno suma autonomia); PLUGINS los distribuye a todos
```
<!-- ascii-note:
intent: presentar el arco completo de la charla como bloques que se apilan (no una pirámide/escalera estricta): el chat (base) -> conectores -> tareas programadas -> Cowork (carpetas/archivos) -> Instrucciones+Projects -> archivos .md -> Skills/Subagentes -> Live Artifacts, con Plugins como BANDA TRANSVERSAL que envuelve/distribuye todo. Los tres bloques de abajo están marcados "(visto)" y el bloque Cowork lleva el marcador "estamos acá".
emphasize: el marcador "<== ACÁ" en el bloque Cowork; los "(visto)" en chat/conectores/tareas programadas; que Plugins es transversal (banda que rodea la pila, distinto color), NO un nivel más; el par bloque↔problema en cada nivel.
labels: banda exterior = PLUGINS (capa transversal, distribución). Bloques apilados (base→cima): El chat · Conectores · Tareas programadas · Cowork: carpetas · Instrucciones+Projects · Archivos .md · Skills/Subagentes · Live Artifacts, cada uno con su frase-problema a la derecha.
-->

### Sources

- corpus/agentic-ai-deck.zip.md — progresión de building blocks del deck (Instrucciones → Projects → Skills → Connectors/MCP → Schedule → Live Artifacts); la idea de "pila" es la lectura ordenada de esa progresión, re-secuenciada al arco chat-primero de esta charla.
- "corpus/mision - auto.zip.md" — la misión Atlas arma estas piezas una por una.

### Speaker notes

El mapa de toda la sesión: arranca en el chat que ya usan, no en Cowork. Aprovechar el efecto acumulado: los tres de abajo ya los recorrimos; señalar "estamos acá", Cowork, donde la IA trabaja sobre carpetas y archivos reales. Leer cada bloque por su problema, que el diagrama trae al lado: cada pieza nace de una frustración concreta. Cuidado con la metáfora: no es una pirámide donde cada capa depende de todas las de abajo; los bloques se apilan y se combinan. Prometer el roadmap: vamos a recorrer cada bloque, uno por uno, en este orden, y pueden volver acá entre secciones para ubicarse. Al final, la pila entera es Atlas. Plugins envuelve la pila y no es un bloque más: empaqueta y distribuye varias piezas a la vez. Lo vemos en la sección 7. Tiempo objetivo: ~3-4 min.

### Presenter feedback
- [closed] 2026-06-09 — "Es la represnetacion como piramide la correcta ?."
  Resolution: Revisado: la piramide estricta implicaba erroneamente que cada capa depende de todas las de abajo. Cambiado a un diagrama de 'bloques que se apilan' (se combinan, no se exigen), con texto que lo aclara, y Plugins como banda transversal. ascii-note y Speaker notes actualizados para quitar la lectura de piramide-dependencia.
- [closed] 2026-06-09 — "Tenemos que hacer claro que vamos a ir sobre cada uno de estos conceptos."
  Resolution: Agregada linea explicita en Content y Speaker notes: 'este es el mapa de la charla; vamos a recorrer cada bloque, uno por uno, en este orden' — y que se puede volver a la slide como 'estamos aca' entre secciones.
- [closed] 2026-06-09 — "deberiamos aregar tal vez plugins como transversar como una forma de distribuir parte de todo esto.  Agregar un slide si no existe sobre esto."
  Resolution: Plugins representado como CAPA TRANSVERSAL de distribucion en el diagrama (banda que envuelve la pila de bloques, no un peldano mas), con bullet dedicado en Content. La slide de Plugins ya existe (6.2) y ademas se agrego una slide nueva de ciclo de vida de Plugins en Team (6.3); ascii-note actualizado para marcar Plugins como transversal.
- [closed] 2026-07-15 — "Slides has too much text. Mix de compactar sin perder el objetivo de la slide y partir en 2 slides."
  Resolution: COMPACTAR 4.5 (ex 4.4). Título "El mapa de la charla: bloques que se apilan" (43c) → "Bloques que se apilan" (21c). Quitados los 9 sub-bullets que emparejaban cada bloque con su problema recurrente: el diagrama de 30 líneas los dibuja uno por uno, con la frase-problema al lado de cada bloque, y su ascii-note los nombra en `emphasize` ("el par bloque↔problema en cada nivel") y los lista enteros en `labels`. Verificados los 9 pares contra el ASCII antes de quitarlos: los 9 están dibujados (Instrucciones y Projects comparten caja). Fue merge, no borrado: la lámina sigue mostrando cada par, en el diagrama que es su lugar. Quedan 3 bullets: que no es una escalera, "estamos acá" para ubicarse, y Plugins como capa transversal. Los tres [closed] previos siguen en pie y su sustancia queda intacta en Speaker notes: el cuidado con la metáfora de la pirámide (2026-06-09), la promesa explícita de recorrer cada bloque uno por uno (2026-06-09) y Plugins como banda que envuelve la pila, no un peldaño más (2026-06-09). Notes de 181 a 140 palabras; quedan sobre las ~120 a propósito, porque comprimir más aplastaría alguno de esos tres beats protegidos. Cross-ref corregido en Content y en Speaker notes: la sección de Plugins pasó de 5 a 7. ASCII y ascii-note sin tocar (el ASCII todavía dice "seccion 5" en el bloque SKILLS / SUBAGENTES: reportado para un pase del ilustrador).
- [closed] 2026-07-15 — "El ASCII del mapa manda al público a la sección equivocada: dice 'seccion 5' para Skills/Subagentes y hoy esa sección es la 7. Arreglalo en el draft antes del freeze, no en el render." (origin: presenter-chat)
  Resolution: Corregido en el ASCII del mapa, línea del bloque `SKILLS / SUBAGENTES`: `(avanzado, seccion 5)` → `(avanzado, seccion 7)`. Es el último cross-ref stale de la renumeración de round 8 (la ex-sección 5 "Advanced" es hoy la 7 "Piezas avanzadas") y el único que vivía dentro de un diagrama, razón por la que los dispatches del pase de densidad lo reportaron sin tocarlo. Se arregla acá y no en `final.md` ni en el SVG porque una etiqueta con el número de sección equivocado es un defecto de contenido de Step 4, no de renderizado: el ilustrador nunca corrige contenido, así que un fix aguas abajo volvería a aparecer en cada re-render. Sustitución de un solo carácter, mismo ancho: las 28 líneas de la caja siguen midiendo 84 caracteres y los bordes `||` / `+===+` quedan intactos; cero cambios de geometría. El `ascii-note` se revisó y NO requería cambios: sus tres campos (`intent`, `emphasize`, `labels`) nombran Skills/Subagentes como bloque de la pila pero no citan ningún número de sección. Barrido independiente de los 17 bloques ASCII y sus notes del deck: no queda ninguna otra referencia stale a sección o slide dentro de un diagrama.

---

# 9. claude-cowork · s7-4-1

**Goal of this section:** most portrait art (~1.4:1)

## 1. Subagentes: delegar en paralelo

### Content

- **Subagente** = asistente aislado, contexto propio; devuelve **un resumen** (no la transcripción).
- Regla de una línea: chico y visible → **Skill**. Grande o ruidoso → **Subagente**.
- En Cowork corren "por debajo", **varios en paralelo**.
- Se agrega como una Skill (descripción + instrucciones): pedíselo a Claude, o viene en un **Plugin**.

```ascii
                +------------------+
                | agente principal |
                +------------------+
                  /      |       \
                 v       v        v
          +--------+ +--------+ +--------+
          | sub A  | | sub B  | | sub C  |
          |contexto| |contexto| |contexto|
          |propio  | |propio  | |propio  |
          +--------+ +--------+ +--------+
                 \       |       /
                  v      v      v
                +------------------+
                | resumen combinado|
                +------------------+
```
<!-- ascii-note:
intent: mostrar el patron fan-out/fan-in: el agente principal reparte una tarea entre varios subagentes que corren en paralelo con contexto propio, y junta los resultados en un resumen combinado.
emphasize: el paralelismo (tres subagentes a la vez) y que cada uno tiene contexto aislado; el resumen combinado al final.
labels: agente principal -> sub A / sub B / sub C (contexto propio) -> resumen combinado.
-->

### Sources

- corpus/agentic-ai-deck.zip.md — definición de Subagent (aislado, devuelve un resumen); "Skill vs Subagent" (slide 4.9 tabla); matriz 4.10 (Cowork ⚠️, under the hood); demo 4.8 (8 propuestas en paralelo).
- Claude Docs — Subagents: https://code.claude.com/docs/en/sub-agents — concepto general de subagente (un spec: cuándo usarlo + instrucciones).

### Speaker notes

Nivel avanzado, presentarlo como "para cuando crezcas". La distinción mental útil: si la sub-tarea es chica y querés verla, es una Skill; si es grande o ruidosa y querés que corra aparte sin ensuciar tu conversación, es un Subagente. El ejemplo del deck ilustra el fan-out: 8 propuestas de proveedores revisadas en paralelo por tres especialistas, con tabla combinada al final. Cómo se agrega, en paralelo a las Skills: un subagente se define con una descripción (cuándo usarlo) más instrucciones; le pedís a Claude que lo arme (se gestiona en Customize, igual que una Skill) o viene dentro de un Plugin. Mantenerlo alto nivel, sin rutas de archivos ni internals de persistencia. Tiempo objetivo: ~7 min.

### Presenter feedback
- [closed] 2026-06-09 — "Agregar como se agrega un agente."
  Resolution: Agregado beat 'Como se agrega un subagente' en Content (alto nivel): se define como una Skill (descripcion de cuando usarlo + instrucciones); le pedis a Claude que lo arme (se gestiona en Customize) o viene dentro de un Plugin; sin rutas de archivo ni internals. Reescrito el bullet 'En Cowork' (quitada la referencia a config /agents de Claude Code). Sumada fuente de docs de Subagents.
- [closed] 2026-07-15 — "Slides has too much text. Mix de compactar sin perder el objetivo de la slide y partir en 2 slides." (origin: presenter-chat)
  Resolution: COMPACTAR 7.4 (ex 7.3), SOLO EL TÍTULO: "Subagentes: delegar sub-tareas en paralelo" (42c) → "Subagentes: delegar en paralelo" (31c), 2 caracteres sobre el techo de 40 y ese era el defecto entero. Cae "sub-tareas", que el bullet 1 y el diagrama ya cargan. El cuerpo conforma y NO se tocó: 4 bullets + 1 diagrama, dentro del techo de densidad, y ninguno de los 4 transcribe el ASCII (el diagrama dibuja el fan-out/fan-in; los bullets dan la definición, la regla Skill-vs-Subagente, el paralelismo en Cowork y cómo se agrega). Sources, Speaker notes, ASCII y ascii-note sin tocar. El [closed] del 2026-06-09 ("Agregar como se agrega un agente") queda intacto y su beat sigue en lámina, que es donde lo puso.

---

