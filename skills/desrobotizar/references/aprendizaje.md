# Modo aprendizaje

Extrae patrones de redacción de textos escritos por humanos y los convierte en un perfil de estilo que el skill aplica después al desrobotizar.

## Cuándo se activa

El usuario lo pide con frases tipo "aprendé mi estilo", "analizá cómo escribo", "quiero que escribas como yo / como este autor", o pega textos, archivos o links diciendo que son muestras de escritura.

## Qué acepta como fuente

- **Texto pegado** en la conversación.
- **Archivos locales**: .md, .txt, .docx, .pdf, mails exportados, posts. Leerlos con las herramientas de archivos.
- **Links**: páginas, blogs, artículos, documentos online. Traer el contenido con WebFetch (o la herramienta de fetch disponible) y quedarse solo con la prosa del autor, descartando navegación, comentarios de terceros y citas de otros.

Las fuentes tienen que ser textos redactados por el usuario, o por un autor cuya escritura el usuario quiere imitar. **Nunca textos generados por IA**: aprender de salida de IA reintroduce el slop que este skill combate. Si un texto huele a IA (pasarlo por los chequeos de SKILL.md), avisarle al usuario y pedirle confirmación antes de incluirlo en el corpus.

## Cantidad y variedad

Con una sola muestra el perfil sale pobre y sesgado. Pedir al usuario **muchas fuentes y variadas**:

- **Cantidad**: mínimo 3 textos; ideal 5 a 10 o más.
- **Variedad de formato**: mails, posts, ensayos, mensajes largos, documentación. Cada formato revela hábitos distintos.
- **Variedad de tema**: si todo el corpus habla de lo mismo, el perfil confunde vocabulario del tema con estilo del autor.
- **Variedad de época**: textos de distintos momentos separan el estilo estable de las modas pasajeras.

Si el usuario trae poco o todo del mismo tipo, procesarlo igual pero marcarlo en el perfil como **confianza baja** y decirle qué tipo de muestra sumaría más.

## Qué extraer

Analizar el corpus completo y documentar, con ejemplos citados de las fuentes:

1. **Registro y persona**: ¿voseo, tuteo, usted? ¿Primera persona, impersonal? ¿Formal, coloquial, mezclado?
2. **Ritmo**: largo típico de oración y de párrafo, cuánta variación hay, si usa oraciones cortas de remate y con qué frecuencia.
3. **Puntuación**: qué usa y qué evita (paréntesis, dos puntos, punto y coma, comillas, signos de apertura). Frecuencia real, no impresión.
4. **Conectores**: cuáles usa de verdad para hilar ideas ("igual", "encima", "ahora bien", o ninguno).
5. **Vocabulario**: regionalismos, palabras fetiche, nivel de jerga técnica, anglicismos que usa o rechaza.
6. **Aperturas y cierres**: cómo arranca los textos y párrafos, cómo termina. ¿Cierra con conclusión, con pregunta, en seco?
7. **Recursos propios**: humor, ironía, ejemplos personales, preguntas al lector, listas, analogías. Con qué frecuencia.
8. **Muletillas personales**: repeticiones que son firma del autor. Anotarlas como permitidas aunque una regla general las corte.
9. **Lo que nunca hace**: tan importante como lo que hace. Si en todo el corpus no hay ni una lista con viñetas, el perfil lo registra.

## Salida: el perfil de estilo

Escribir (o actualizar) `references/estilo-personal.md` dentro de la carpeta del skill con esta estructura:

```markdown
# Perfil de estilo personal

Generado: [fecha]
Corpus: [N textos, formatos, rango de fechas]
Confianza: alta / media / baja — [por qué]

## Registro
...

## Ritmo y puntuación
...

## Vocabulario y conectores
...

## Aperturas y cierres
...

## Recursos y muletillas propias (permitidas)
...

## Lo que este autor nunca hace
...

## Excepciones a las reglas base
[Reglas de SKILL.md que este perfil relaja, con la evidencia del corpus]
```

Cada afirmación del perfil lleva al menos un ejemplo citado del corpus. Sin evidencia, no entra.

## Cómo se aplica el perfil

Cuando `references/estilo-personal.md` existe, el skill trabaja en dos capas:

1. **Reglas base primero**: los patrones de IA (frases.md, estructuras.md) se eliminan igual. El perfil nunca sirve de excusa para dejar slop.
2. **El perfil refina**: donde las reglas base dejan margen (ritmo, registro, puntuación, vocabulario), manda el perfil.
3. **Conflictos**: si el corpus humano demuestra que el autor usa algo que una regla base corta (por ejemplo, arranca párrafos con "Igual" o usa listas de tres), la excepción queda registrada en el perfil con su evidencia y se respeta. La escritura real de un humano le gana a la regla general.

Para reaprender o ampliar el perfil, el usuario suma fuentes y se repite el análisis sobre el corpus completo, no solo sobre lo nuevo.
