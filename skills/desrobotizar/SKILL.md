---
name: desrobotizar
description: Elimina patrones de escritura de IA en prosa en español. Usar solo cuando el usuario invoque explicitamente desrobotizar o pida aplicar esta skill por nombre. No activar por redactar, editar o revisar texto en español sin esa solicitud explicita.
metadata:
  inspired-by: stop-slop de Hardik Pandya (https://hvpandya.com)
---

# Desrobotizar

Elimina los patrones predecibles de la escritura de IA en español.

## Reglas núcleo

1. **Corta las frases de relleno.** Elimina aperturas de carraspeo, muletillas de énfasis, jerga corporativa y los adverbios en -mente. Ver [references/frases.md](references/frases.md).

2. **Rompe las estructuras formuláicas.** Nada de contrastes binarios ("no es X, sino Y"), listados negativos, fragmentación dramática, preguntas retóricas con respuesta inmediata, falsa agencia. Ver [references/estructuras.md](references/estructuras.md).

3. **Usa voz activa con sujeto humano.** Nada de voz pasiva ("fue decidido") ni de pasiva refleja que esconde al actor ("se decidió que..."). Nada de objetos inanimados haciendo verbos humanos ("la queja se convierte en solución"). Alguien decide, alguien arregla: nómbralo.

4. **Sé específico.** Nada de declarativas vagas ("las implicancias son profundas"). Nombra la cosa concreta. Nada de extremos perezosos ("todo", "siempre", "nunca", "nadie") haciendo trabajo vago.

5. **Pon al lector en la escena.** Nada de narrador flotando a la distancia. "Vos"/"tú" le gana a "la gente". Lo concreto le gana a lo abstracto.

6. **Varía el ritmo.** Mezcla largos de oración. Dos ítems le ganan a tres. Termina los párrafos de formas distintas.

7. **Confía en el lector.** Afirma directo. Sin suavizar, sin justificar cada frase, sin llevarlo de la mano.

8. **Corta lo citeable.** Si una frase suena a cita de póster motivacional, reescríbela.

9. **Domestica el gerundio.** Un gerundio por oración como máximo, y solo si expresa simultaneidad real. Nada de "logrando así", "permitiendo que", "generando un impacto".

10. **Corta los conectores académicos en cadena.** "Sin embargo", "no obstante", "por otro lado", "asimismo", "además" abriendo párrafo tras párrafo delatan a la máquina. Que las ideas se conecten solas.

11. **Nunca em-dashes (—).** Para un inciso usa el guion medio común (-), y siempre en par: se abre y se cierra ("el equipo - el de ventas - lo pidió"). Un inciso abierto con guion no puede quedar colgando hasta el punto.

12. **Sin puntuación compulsiva.** Los dos puntos (:) como bisagra dramática en cada párrafo y los guiones de inciso repetidos son tells de máquina. Usa cada uno pocas veces por texto; si abundan, reescribe con oraciones simples.

13. **Sin ganchos de complicidad fabricada.** Nada de atribuirle experiencias o acuerdos al lector para generar cercanía: "vos también lo reconocés", "seguro te pasó", "todos lo hemos visto", "¿te suena?". Es la versión IA del carisma. Muestra el ejemplo concreto y deja que el lector se reconozca solo.

14. **Las instrucciones no se narran.** Si el usuario pide cambiar o agregar algo a lo que estás generando, aplica el cambio. No incorpores al texto la explicación o el razonamiento de fondo de esa instrucción, salvo que el usuario lo pida explícito. "Que la instalación sea para gente no técnica" significa diseñarla así, no escribir "no hace falta saber programar" en el texto.

15. **El usuario amplía las reglas.** Cuando el usuario marca una frase o un texto como slop, extraé el patrón de fondo (no solo la frase literal), proponéselo y agregalo a [references/reglas-propias.md](references/reglas-propias.md). Esas reglas valen igual que las de base.

## Chequeos rápidos

Antes de entregar prosa:

- ¿Adverbios en -mente? Matálos.
- ¿Voz pasiva o pasiva refleja escondiendo al actor? Encontrá quién actúa y ponelo de sujeto.
- ¿Cosa inanimada haciendo verbo humano ("la decisión emerge")? Nombrá a la persona.
- ¿"Cabe destacar", "es importante mencionar", "vale la pena señalar"? Borrá y decí la cosa.
- ¿Contraste "no es X, sino Y"? Afirmá Y directo.
- ¿Tres oraciones seguidas del mismo largo? Rompé una.
- ¿Párrafo que termina con remate efectista? Variá.
- ¿Em-dash (—) en alguna parte? Reemplazá por guion medio (-) en par, coma, punto o paréntesis.
- ¿Inciso con guion abierto y nunca cerrado? Cerralo o reescribí.
- ¿"El verdadero X viene cuando" o pariente? Borrá la fórmula y mostrá el X concreto.
- ¿"No se trata de X" (con o sin "se trata de Y")? Afirmá Y directo.
- ¿Más de dos usos de ":" o de guiones de inciso en el texto? Reescribí con oraciones simples.
- ¿Apertura que le atribuye algo al lector ("vos también", "seguro te pasó", "¿te suena?")? Mostrá el caso concreto y sacá la complicidad.
- ¿El texto narra una instrucción que te dieron para generarlo ("pensado para que cualquiera pueda...")? Sacala; la instrucción moldea el texto, no aparece en él.
- ¿Cápsula de beneficio cerrando un bloque ("Desde ahí redacta como vos.", "Y listo.")? Integrá el beneficio a la oración del hecho o cortalo.
- ¿Titular de párrafo ("Y crece con el uso. [explicación]")? Cortá el anuncio o fusionalo con la explicación.
- ¿Intercepción dramática ("antes de que llegue a...", "antes de que sea tarde")? Decí el hecho plano, sin cuenta regresiva.
- ¿Magia instantánea ("lo marcás y queda prohibido", "un clic y listo")? Mostrá la acción real completa, con su actor.
- ¿Oración hendida ("sos vos quien...") o pronombre redundante ("lo hacés vos")? Sujeto, verbo, complemento.
- ¿Metáfora de viaje ("punto de partida", "primer paso hacia")? Decí el estado real.
- ¿Dueto lírico ("tu ritmo y tus palabras") o relleno instrumental ("con el uso")? Nombrá el rasgo o la acción concreta.
- ¿Eco redundante (repetir al cierre lo que ya está implícito)? Cortá la segunda mitad.
- ¿Cola de participio adulador ("afinada a tu criterio", "adaptada a tus necesidades")? Si tiene información, hacela oración; si no, cortá en la coma.
- ¿Existe references/reglas-propias.md? Aplicá también esas reglas.
- ¿Declarativa vaga ("el impacto es significativo")? Nombrá el impacto concreto.
- ¿Gerundio de consecuencia ("logrando", "permitiendo", "generando")? Reescribí con verbo conjugado.
- ¿Párrafos que arrancan con "Sin embargo" / "Además" / "Por otro lado"? Sacá el conector.
- ¿"En un mundo donde", "en la era de", "en el vertiginoso"? Borrá la apertura entera.
- ¿Meta-comentario ("a lo largo de este artículo veremos...")? Borrá. Que el texto avance.
- ¿Sustantivo + "clave" o "juega un papel fundamental"? Decí qué hace y por qué importa.

## Modo aprendizaje

Cuando el usuario pide aprender su estilo (o el de un autor que le gusta) y trae textos pegados, archivos o links, seguí [references/aprendizaje.md](references/aprendizaje.md):

1. Juntá el corpus: texto pegado, archivos leídos con las herramientas de archivos, links traídos con WebFetch.
2. Verificá que las fuentes sean de autoría humana, no de IA. Si algo huele a IA, avisá antes de incluirlo.
3. Pedí fuentes **muchas y variadas** (mínimo 3, ideal 5-10; distintos formatos, temas y épocas). Con poco corpus, procesá igual pero marcá el perfil como de confianza baja.
4. Extraé los patrones (registro, ritmo, puntuación, conectores, vocabulario, aperturas y cierres, muletillas propias, lo que el autor nunca hace) y escribí `references/estilo-personal.md` con evidencia citada.

Si `references/estilo-personal.md` existe, aplicalo como segunda capa: primero las reglas anti-slop de siempre, después el perfil para todo lo que las reglas dejan abierto. Las excepciones documentadas en el perfil (con evidencia del corpus) le ganan a las reglas de estilo generales.

## Puntaje

Calificá de 1 a 10 cada dimensión:

| Dimensión | Pregunta |
|-----------|----------|
| Franqueza | ¿Afirma o anuncia? |
| Ritmo | ¿Variado o metrónomo? |
| Confianza | ¿Respeta la inteligencia del lector? |
| Autenticidad | ¿Suena a persona? |
| Densidad | ¿Queda algo cortable? |

Menos de 35/50: revisar.

## Ejemplos

Ver [references/ejemplos.md](references/ejemplos.md) para transformaciones antes/después.

## Licencia

MIT
