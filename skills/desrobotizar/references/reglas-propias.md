# Reglas propias del usuario

Reglas anti-slop que este usuario agregó a partir de textos que lo molestaron. Valen igual que las reglas de base de frases.md y estructuras.md.

## Cómo se agrega una regla

1. El usuario marca una frase, estructura o texto como slop.
2. Claude extrae el patrón de fondo, no solo la frase literal. "El verdadero cambio viene cuando" es una instancia; el patrón es la fórmula "el verdadero X viene cuando".
3. Claude propone el patrón generalizado con dos o tres variantes y una alternativa.
4. Confirmado por el usuario, se agrega acá abajo con el formato de la tabla.

## Reglas

| Patrón | Problema | En cambio |
|--------|----------|-----------|
| (vacío por ahora) | | |

Cuando el usuario diga "esto es slop", "agregá esta regla" o pegue un texto señalando lo que le molesta, el destino es esta tabla.
## No describir a una persona con "Aporta [beneficio abstracto]"

`Aporta la conexión con el capital internacional` / `Aporta experiencia y visión` son
relleno: nombran un beneficio abstracto en vez de mostrar qué hace la persona.
Reemplazá "Aporta X" por un **verbo activo concreto** con la persona de sujeto.

- Mal: "Aporta la conexión con el capital internacional."
- Bien: "Conecta a la empresa con el capital internacional."

Aplica también a "brinda", "ofrece", "suma" cuando el objeto es un beneficio vago.

## Nada de "X tras X" como relleno rítmico

`campaña tras campaña`, `día tras día`, `season after season`, `year after year`
suenan a muletilla de cierre de IA. Si el sentido "sostenido en el tiempo" importa,
decilo plano ("a lo largo de las campañas" / "across the seasons"); si no aporta, cortalo.

- Mal: "Calidad consistente, a escala, campaña tras campaña."
- Bien: "Calidad consistente y a escala." (o cortar la frase entera si es puro relleno)

## Nada de titulares de arco "De X a Y" (con o sin cola de coma)

`De la idea abstracta al render, sin perder el control` / `Del caos a la claridad` /
`De X a Y: cómo...` son la metáfora de viaje disfrazada de título, y la cola de coma
("..., sin perder el control", "..., paso a paso") agrava el patrón con una aposición
de beneficio. Vale también para la prosa: "llegar desde esa idea hasta una
visualización" es el mismo arco narrado. Decí qué hace o qué es la cosa, plano
y con verbo.

- Mal: "De la idea abstracta al render, sin perder el control."
- Mal: "La misión es llegar desde esa idea hasta una visualización detallada."
- Bien: "Acordá el diseño en texto; el render llega al final."
- Bien: "La misión es producir una visualización detallada de ese espacio."

## Nada de contraste negativo con coma: "X, no Y" / "X y no Y"

`contra la especificación, no contra tu gusto` / `depende del documento, no del modelo` /
`responde al plan y no a la imaginación`. Es la variante corta del contraste binario
"no es X, sino Y": afirma algo y le cuelga la negación de su opuesto para darle drama.
Si el opuesto no aporta información, cortalo; si aporta, dale su propia oración.

- Mal: "Mirá el resultado contra la especificación, no contra tu gusto."
- Bien: "Compará el resultado con la especificación."
- Mal: "Se apoyan acá, no en la memoria del chat."
- Bien: "Se apoyan en este documento. La memoria del chat se pierde."

## Nada de epigramas balanceados de dos cláusulas

`Acordá el diseño en texto; el render llega al final` / `El texto es el cerebro;
la imagen es la cara` / `X convierte lo que se pierde en lo que queda`. Dos cláusulas
en espejo (con punto y coma, coma o paralelismo léxico) que suenan a máxima de póster.
Es la versión sofisticada de "lo citeable": el balance ES el tell. Quedate con la
cláusula que informa y tirá la otra, o decí la instrucción plana.

- Mal: "Acordá el diseño en texto; el render llega al final."
- Bien: "Diseñá el espacio en texto antes de pedir el render."

## Verborragia que no suma

Toda frase u oración que no agrega información nueva se corta: colas explicativas de
lo ya dicho ("sin que tengas que repetir nada"), segundas oraciones que reformulan la
primera, aposiciones decorativas y paréntesis con detalle que el lector no necesita
en ese punto. Prueba: tapá la frase; si el texto comunica lo mismo, sobraba.

- Mal: "El trabajo sigue vivo en ese archivo y el próximo chat lo lee sin que repitas nada."
- Bien: "El trabajo sigue vivo en ese archivo."

## Coma compulsiva

Evitá cadenas de 3-4 items separados por coma y las comas de aposición al final
("Nuestra capacidad, disponible para terceros"). Partí en dos oraciones o convertí
la aposición en oración ("Nuestra capacidad está disponible para terceros"). En inglés,
sacá la coma de Oxford antes de "and". Máximo una o dos comas por oración.

## En presentaciones, la segunda persona no es el registro por defecto

El problema es el tuteo compulsivo y sin considerar el contexto: slides, tesis,
agenda y títulos que le hablan al público sistemáticamente ("el chat que ya usás",
"aprendés a extenderlo", "Trabajá en .md"). El que le habla a la audiencia es el
presentador, en vivo; la presentación enuncia. El registro por defecto es
impersonal o tercera persona; la segunda persona se reserva para usos puntuales
y deliberados que el contexto justifique (o pedido explícito del usuario).

- Mal: "Partís del chat que ya usás todos los días y lo extendés paso a paso."
- Bien: "La charla parte del chat de uso diario y lo extiende paso a paso."
- Mal (título): "Trabajá en .md, exportá al final."
- Bien (título): "Trabajar en .md, exportar al final."

Las notas del orador quedan fuera de esta regla (le hablan al presentador, no al
público). En prosa de slides esta regla le gana a la regla 5 de base ("vos le
gana a la gente"): esa regla vale para prosa que un lector lee, no para láminas
proyectadas.

## Nada de fórmulas de transformación: "X deja de Y y pasa a Z"

"Faro deja de depender de notas y pasa a investigar solo" es plantilla de
revelación. Decí el estado nuevo directo, con verbo concreto.

- Mal: "El chat deja de ser un buscador y pasa a ser un agente."
- Bien: "El chat investiga solo: busca precios y noticias, y los guarda."

Variantes que caen acá: "ya no X, ahora Y", "pasó de X a Y" como remate.

## Nada de hendidas de revelación: "X es lo que Y" / "el salto viene cuando"

"El salto de chatear a delegar es lo que vuelve útil a un agente" esconde una
afirmación simple detrás de un tambor de suspenso. Sujeto, verbo, complemento.

- Mal: "Delegar es lo que vuelve útil a un agente en el trabajo real."
- Bien: "Un agente se vuelve útil cuando se le delega trabajo real."
- Mal: "El cambio viene cuando el chat toca tus datos."
- Bien: "Con acceso a los datos, el chat responde sobre trabajo real."

Variantes: "X es lo que Y (realmente)", "el cambio/salto/truco viene cuando",
"ahí es donde X", "lo que hace la diferencia es". Parientes del ya prohibido
"el verdadero X viene cuando" — misma familia, mismo destino.

## Nunca "compu"

La palabra "compu" está prohibida en todo registro (slides, notas, prosa).
Siempre "computadora" (o "laptop" si el matiz portátil importa).

- Mal: "corre sin la compu" / "Claude instalado en tu compu".
- Bien: "corre sin la computadora prendida" / "Claude instalado en la computadora".

## Llamar a las cosas por su nombre

Nada de sustantivos desplazados que "quieren decir otra cosa": "la máquina" por
la IA o por la computadora, "la herramienta" por el producto concreto, "la
plataforma" cuando hay un nombre. Usá el término preciso: la IA, el modelo,
la computadora, Cowork.

- Mal: "La estructura también la entiende la máquina."
- Bien: "La IA está especialmente entrenada para comprender su estructura."

## Nada de minimizadores de fricción: "con un clic", "sin programar", "en segundos"

Prometen facilidad que casi nunca es literal ("se activa con un clic" cuando en
realidad requiere autenticación). Además de slop suelen ser mentira. Describí el
paso real.

- Mal: "Se activa con un clic, sin programar."
- Bien: "Se activa a través de la biblioteca de conectores. Muchos requieren autenticación."

## Nada de etiquetas autorreferentes: "la frase de la sesión", "la distinción de la charla"

Bautizar una frase propia con una etiqueta grandilocuente ("el concepto-ancla",
"la idea que ordena todo", "la regla de oro de esta charla") es autobombo de IA
y además suele ser impreciso (hay varias distinciones en una charla). Decí el
contenido sin ceremonial, o usá un rótulo descriptivo plano ("Dos modos de
responder:").

- Mal: "La frase de la sesión: 'Dejás de tipear...'"
- Mal: "La distinción de la charla: de memoria vs con búsqueda."
- Bien: "Dos modos de responder: de memoria / con búsqueda."

## Fragmentos telegráficos con coma: oración completa con verbo

"El formato final, al último." / "se genera una vez, al final." / "carpeta
dedicada, nunca una con datos confidenciales". El slop comprime en fragmentos
yuxtapuestos con coma; la redacción humana usa oraciones completas con verbo y
conector explícito. Hermana de "coma compulsiva", pero apunta al fragmento sin
verbo, no a la cadena de items.

- Mal: "Buena práctica: carpeta dedicada, nunca una con datos confidenciales."
- Bien: "Buena práctica: usar una carpeta dedicada y asegurarse de que no contenga datos confidenciales."

## Nada de colas de completitud: "punta a punta", "de principio a fin"

Colas que declaran exhaustividad sin agregar información. Si el recorrido es
completo, se ve; no hace falta anunciarlo.

- Mal: "El loop de Atlas, punta a punta:"
- Bien: "El loop completo de Atlas:"

## Sin mayúsculas enfáticas en prosa

"busca información real, AHORA" — el énfasis por mayúsculas es slop de slide.
Si una palabra necesita énfasis, reescribí la oración para que el énfasis salga
del contenido (o usá negrita si el medio lo permite). Excepción: siglas y
etiquetas de diagrama tipo ANTES/AHORA como rótulos de columnas.

## Intensificadores redundantes: "real", "de verdad", "literalmente"

Adjetivos que afirman lo que nadie puso en duda. "La app real" (¿existe una de
mentira?), "un problema de verdad", "literalmente X" sin literalidad en juego.
Se cortan sin pérdida.

- Mal: "tour de la pestaña Cowork sobre la app real."
- Bien: "tour de la pestaña Cowork sobre la app."

## Meta-narración de la presentación sobre sí misma

Frases donde la charla se narra a sí misma sin informar: "La charla arranca
ahí.", "sirve para ubicarse entre secciones.", "esto lo vemos después" como
relleno. El presentador narra el recorrido en vivo; la slide no. (Los marcadores
funcionales tipo "(visto)" / "estamos acá" en un mapa sí valen: son señal, no
narración.)

- Mal: "Todos ya usan un chat de IA. La charla arranca ahí."
- Bien: "Todos ya usan un chat de IA."

## "X vive acá/en Y" es slop

"El resto de la charla vive acá", "la información vive en .md": la metáfora
habitacional aplicada a contenido o software es muletilla de IA. Decir dónde
está o de qué trata, plano.

- Mal: "El resto de la charla vive acá."
- Bien: "El foco del resto de la charla."
