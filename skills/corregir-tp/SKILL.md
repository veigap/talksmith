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

**Paso 2: Relevamiento de hechos por entrega** (hechos separados de valoracion,
evidencia siempre citada archivo:linea):
- ¿El HEAD entregado compila y corre? (caso real: dos ediciones web de ultimo momento
  rompieron una entrega que "andaba")
- Secrets en working tree y en historial de git
- Commits: distribucion temporal y autoria (insumo de ajuste individual)
- ¿Los resultados reportados corresponden a la version entregada?
- Transcript de la presentacion: mapear secciones pedidas + citas textuales utiles

**Paso 3: Clasificacion P3 por area tecnologica**, contra el inventario:
- **3.1 Uso lo enseñado, bien aplicado** → muy bueno; sostiene o suma
- **3.1-mal: lo enseñado, mal aplicado o sin validar** → resta (−0.5 a −1)
- **3.2.1 Algo superador o evolucion de lo enseñado** → buenisimo; premia (+0.5)
- **3.2.2 Algo MAS PRIMITIVO que lo enseñado, o no resuelve** → resta fuerte
  (−1 a −2, mas cuanto mas central el area)
- Agravante de 3.2.2: presentar lo primitivo con el nombre de lo enseñado (llamar
  "RAG" a un matching de palabras) o como virtud.

**Paso 4: Nota.** Base sobre 10 = proporcion P1+P2. Modulacion P3 por area.
Magnitudes default calibrables por el docente. Ajuste individual ±1 solo con
evidencia y motivo registrado. Redondeo segun la catedra.

**Presentacion oral/video:** doble rol. Como deliverable (P2: las secciones que el
enunciado exige, textuales). Como evidencia de P3: ¿explican sus tecnicas con los
conceptos del curso bien nombrados? ¿justifican contra lo dictado o solo describen?
¿la seccion de aprendizajes muestra incorporacion real o generalidades?

## Outputs

- `inventario-contenidos.md` (paso 0)
- Una planilla por equipo: P1/P2 checklist + tabla P3 por area + evidencia citada +
  devolucion de 4-6 lineas honesta y accionable
- Tabla/Excel resumen con notas y justificacion por criterio, apto como acta

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
