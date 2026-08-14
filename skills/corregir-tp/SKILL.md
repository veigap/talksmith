---
name: corregir-tp
description: Usar cuando el usuario pida corregir, evaluar o poner nota a entregas de alumnos de una materia donde existen (a) un enunciado del TP y (b) clases dictadas con contenidos y practicas. Tambien cuando pida armar una rubrica para ese tipo de correccion. No activar para revisar codigo propio ni para feedback informal sin nota.
---

# corregir-tp: evaluar TPs contra el enunciado y contra lo enseñado

## Principio

Un TP se evalua contra DOS referencias concretas, nunca contra descriptores abstractos:

1. **El enunciado**: que se pidio y como.
2. **El contenido dictado en clase**: el piso tecnologico exigible.

El objetivo formativo de un TP es aplicar el curso. Usar tecnologia mas primitiva que
lo enseñado no es una "decision de diseño defendible": es no haber incorporado el
contenido, y resta fuerte. Este skill existe porque una correccion real evaluo un
matching por listas de palabras como "trade-off defendible por explicabilidad" en una
materia que dicto RAG semantico completo, y el docente tuvo que corregirlo tres veces.

## Insumos requeridos

| Insumo | Si falta |
|---|---|
| Enunciado del TP | Pedirlo; sin enunciado no hay P1/P2 |
| Carpeta de contenidos del curso (teoria + practicas) | Pedirla; sin vara no hay P3. Si el repo de la materia tiene las clases, ofrecer armar el inventario desde ahi para que el docente lo curen |
| Entregas (repos o carpetas por equipo) | Pedir links/accesos; registrar los pendientes |
| Transcripts o acceso a presentaciones orales | Opcional; sin ellos, la dimension presentacion queda para el docente |
| Politicas de la materia (perfil del alumnado, tolerancias) | Preguntar solo las que cambian la nota; registrar cada una fechada |

## Metodo

**Paso 0: Inventario de Contenidos Enseñados.** De la carpeta del curso, tabla:
tecnica/concepto, fuente (clase/practica), nivel dictado (visto / practicado /
entregable previo). Mapear cada tecnica a las areas del TP y asignar **centralidad**
(que area es el corazon del trabajo). Este inventario es la vara: nadie puede alegar
que una tecnica central "no se vio".

**Paso 1: Deliverables del enunciado (P1 y P2).** Extraer del enunciado la lista
exhaustiva de entregables con su seccion fuente. Por cada uno:
- **P1: ¿existe?** Binario. Un deliverable ausente no se compensa con calidad en otro.
- **P2: ¿es conforme a la letra?** Campos y formatos exactos, requisitos textuales
  (ej. "si no corre en 10 minutos no cumple el requisito"). Hecho-pero-distinto = no
  conforme. Citar la frase del enunciado que ancla cada exigencia dura.

**Paso 2: Extraccion por equipo con subagentes → ficha intermedia.** Lanzar UN
subagente por equipo, en paralelo. Cada subagente recibe el enunciado, el inventario
del paso 0 y los insumos de SU equipo (repo + transcript/video), y produce
`ficha-<equipo>.md`: una representacion intermedia detallada, estructurada en funcion
del enunciado, de la que despues se deriva la version numerica. El subagente NO pone
nota; extrae y clasifica. Esquema de la ficha:

1. **Identificacion**: integrantes, links (repo, presentacion), ubicacion de la
   entrega dentro del repo si esta mezclada con otras.
2. **Relevamiento de hechos del repo** (hechos separados de valoracion, evidencia
   siempre citada archivo:linea):
   - ¿El HEAD entregado compila y corre? (caso real: dos ediciones web de ultimo
     momento rompieron una entrega que "andaba")
   - Secrets en working tree y en historial de git
   - Commits: distribucion temporal y autoria (insumo de ajuste individual)
   - ¿Los resultados reportados corresponden a la version entregada?
3. **P1/P2 por deliverable**: checklist existe/conforme con la cita del enunciado.
4. **P3 por area tecnologica**: tecnica usada, clasificacion (paso 3) y evidencia.
5. **Presentacion, descompuesta en LAS SECCIONES que el enunciado exige**
   (textuales, en su orden). Por cada seccion:
   - presente / ausente / vaciada de contenido
   - **calidad de como la presentaron**: claridad, profundidad, correccion
   - **evaluacion cualitativa contra los contenidos de clase**: ¿nombran y explican
     bien los conceptos del curso? ¿justifican contra lo dictado o solo describen?
     ¿presentan como "lo enseñado" algo que no lo es? (agravante 3.2.2)
   - citas textuales del transcript que anclan cada juicio
6. **Consistencia presentacion ↔ repo**: ¿lo que dicen coincide con lo que el codigo
   entregado hace? Registrar cada discrepancia (funcionalidad mostrada que no esta en
   el HEAD, tecnica declarada que el codigo no implementa, resultados del video que no
   salen de la version entregada, integrantes que aparecen en uno y no en el otro).
7. **Señales para ajuste individual** (autoria de commits vs presencia en video).

Consolidar: leer las fichas, verificar que usan la misma vara, resolver asimetrias de
evidencia antes de puntuar.

**Paso 3: Clasificacion P3 por area tecnologica**, contra el inventario:
- **3.1 Uso lo enseñado, bien aplicado** → muy bueno; sostiene o suma
- **3.1-mal: lo enseñado, mal aplicado o sin validar** → resta (−0.5 a −1)
- **3.2.1 Algo superador o evolucion de lo enseñado** → buenisimo; premia (+0.5)
- **3.2.2 Algo MAS PRIMITIVO que lo enseñado, o no resuelve** → resta fuerte
  (−1 a −2, mas cuanto mas central el area)
- Agravante de 3.2.2: presentar lo primitivo con el nombre de lo enseñado (llamar
  "RAG" a un matching de palabras) o como virtud.

**Paso 4: Modelo numerico (Excel), derivado de las fichas.** La nota se divide en
DOS bloques con nota propia sobre 10 cada uno:

- **Bloque ENTREGA (repositorio)**: criterios derivados de P1/P2 (contrato, formatos,
  reproducibilidad, secrets, interfaz, etica/privacidad...) y de P3 por area
  (tecnica usada vs enseñada, una fila por area). Los criterios P3 de las areas
  centrales llevan los pesos mas altos del bloque.
- **Bloque PRESENTACION**: (a) presencia de las secciones exigidas por el enunciado y
  (b) calidad de como las presentaron (claridad, profundidad, correccion conceptual
  contra los contenidos de clase). Las inconsistencias presentacion↔repo de la ficha
  restan aca o en Entrega segun donde este la mentira.

Mecanica: escala **1 a 5** por criterio (celda en blanco = no evaluado, se excluye de
la normalizacion); cada criterio tiene un **% del bloque editable** (suman 100% por
bloque, con celda verificadora); cada bloque produce su nota /10 por promedio
ponderado; **ponderacion global editable entre Entrega y Presentacion** (celdas knob);
fila de **ajuste por equipo** (±1 solo con evidencia y motivo registrado); redondeo
editable. Cada celda de puntaje lleva su justificacion en una hoja Evidencia.
Advertir al docente la propiedad del piso: en escala 1-5 el minimo aporta 20% del
criterio; para que una regresion duela mas hay que subirle el peso o usar el ajuste.
Construir el Excel con un script regenerable (formulas vivas, no valores pegados) y
marcar visualmente las celdas editables.

## Outputs

- `inventario-contenidos.md` (paso 0)
- `ficha-<equipo>.md` por equipo (paso 2): la representacion intermedia con toda la
  evidencia citada; es la fuente del Excel y de la devolucion
- Excel acta (paso 4): hoja de puntajes con los dos bloques y knobs, hoja de
  evidencia, hoja de politicas docentes fechadas, hoja resumen con links
- `devolucion-<equipo>.md` por equipo: el documento QUE VE EL ALUMNO

**Devolucion al alumno.** Formato fijo: **nota final**, un **parrafo de aciertos**,
un **parrafo de errores**, y una **reflexion final con takeaways para la vida
profesional** (que les enseña este trabajo sobre como van a trabajar con estas
tecnologias en serio). Reglas duras:
- Los alumnos NO deben tener acceso ni poder deducir la metodologia numerica: nada de
  criterios con pesos, puntajes parciales, escalas, nombres de bloques ni aritmetica
  de la nota. Prosa docente, no rubrica.
- Honesta y accionable: los errores se nombran con sus consecuencias, no se
  suavizan hasta desaparecer.
- Consistente con el acta: todo lo dicho debe estar respaldado por la ficha, pero
  traducido a lenguaje de devolucion.

## Racionalizaciones a rechazar (observadas en correccion real)

| Excusa | Realidad |
|---|---|
| "Es un trade-off defendible (explicabilidad, costo, simplicidad)" | Si la tecnica es mas primitiva que lo dictado en el area central, es 3.2.2. La justificacion elaborada no lo salva; puede agravarlo |
| "El sistema funciona y las metricas son decentes" | Funcionar con tecnologia pre-curso no demuestra el aprendizaje que el TP evalua |
| "El equipo lo argumento muy bien en el README" | Argumentar bien la esquiva sigue siendo esquivar. Evaluar el argumento contra el inventario, no por su elocuencia |
| "La rubrica generica le da nivel alto en ese criterio" | Descriptor abstracto sin vara de curso = agujero de la rubrica, no merito del alumno |
| "Espero a que el docente lo note" | Señalar regresiones tecnologicas en la PRIMERA lectura es parte del trabajo |

## Red flags: detenerse y re-evaluar

- Estas por puntuar alto un area central resuelta con tecnicas que la materia supero
- Estas evaluando sin haber leido los contenidos del curso
- Los resultados que estas usando no salieron de la version entregada
- Estas comparando equipos con evidencia asimetrica (ej. ejecutaste solo a algunos)
- Un "hallazgo" tuyo contradice al repo del alumno: verificar si el error es propio
  (caso real: un held-out fallo por usar una base desactualizada del corrector)

## Errores comunes

- Pesos uniformes entre criterios cuando el enunciado declara una restriccion como
  critica: ponderarla acorde (y citar la frase que lo justifica)
- Evaluar la presentacion con criterios inventados en vez de las secciones textuales
  del enunciado
- Confundir "pocos commits" con "poco trabajo" (pudo desarrollarse fuera de git);
  lo objetivo es la perdida de historial, no la holgazaneria
- Cambiar criterios sin registrar la decision del docente con fecha
- Filtrar la mecanica numerica en la devolucion al alumno (mencionar pesos, bloques o
  puntajes parciales permite ingenieria inversa de la rubrica)
- Puntuar la presentacion solo por presencia de secciones sin evaluar la calidad
  conceptual de lo dicho, o sin cruzarla contra el repo entregado
