# Desrobotizar

Un skill para sacarle las marcas de IA a la prosa en español.

## Qué es esto

La escritura de IA tiene patrones: frases, estructuras y ritmos predecibles. Este skill le enseña a Claude (o a cualquier LLM) a detectarlos y eliminarlos en español. Es la adaptación al español de [stop-slop](https://github.com/hvpandya) de Hardik Pandya: no una traducción, sino una versión que cubre los vicios propios del español de máquina (gerundios de consecuencia, pasiva refleja, adverbios en -mente, conectores académicos en cadena, "cabe destacar").

## Estructura del skill

```
desrobotizar/
├── SKILL.md                  # Instrucciones núcleo
├── references/
│   ├── frases.md             # Frases a eliminar
│   ├── estructuras.md        # Patrones estructurales a evitar
│   ├── ejemplos.md           # Transformaciones antes/después
│   ├── aprendizaje.md        # Modo aprendizaje: extraer el estilo del usuario
│   ├── reglas-propias.md     # Reglas anti-slop que agrega cada usuario
│   └── estilo-personal.md    # Perfil de estilo generado (aparece tras el aprendizaje)
├── README.md
└── LICENSE
```

## Inicio rápido

**Claude Code:** Agregá esta carpeta como skill.

**Claude Projects:** Subí `SKILL.md` y los archivos de referencia al conocimiento del proyecto.

**Instrucciones personalizadas:** Copiá las reglas núcleo de `SKILL.md`.

**Llamadas a la API:** Incluí `SKILL.md` en tu system prompt. Los archivos de referencia se cargan a demanda.

## Qué detecta

**Frases prohibidas.** Aperturas de carraspeo, muletillas de énfasis, jerga corporativa, adverbios en -mente, declarativas vagas, fórmulas de revelación ("el verdadero cambio viene cuando"), meta-comentario, léxico de IA ("sumérgete", "amplio abanico", "el auge de"). Ver `references/frases.md`.

**Clichés estructurales.** Contrastes binarios ("no es X, sino Y", "no se trata de X: se trata de Y"), listados negativos, fragmentación dramática, setups retóricos, falsa agencia, narrador a la distancia, voz pasiva y pasiva refleja, gerundios en cadena. Ver `references/estructuras.md`.

**Reglas a nivel oración.** Nunca em-dashes (—): incisos con guion medio (-) siempre en par, abierto y cerrado. Sin abuso de ":" ni de guiones. Sin párrafos que arrancan con "Sin embargo"/"Además", sin staccato, sin extremos perezosos, un gerundio por oración como máximo, voz activa con sujeto humano.

## Modo aprendizaje

El skill puede aprender tu estilo. Le pegás textos escritos por vos (o por un autor cuya escritura te gusta), le pasás archivos, o le das links a cosas que redactaste, y Claude los parsea y extrae tus patrones: registro, ritmo, puntuación, vocabulario, muletillas propias, lo que nunca hacés. El resultado queda en `references/estilo-personal.md` y se aplica como segunda capa sobre las reglas anti-slop.

Dos condiciones: las fuentes tienen que ser de autoría humana (nunca texto generado por IA), y conviene que sean **muchas y variadas** (mínimo 3, ideal 5-10, de distintos formatos, temas y épocas). Con poco corpus el perfil sale sesgado y queda marcado como de confianza baja. Ver `references/aprendizaje.md`.

## Reglas propias

El skill es ampliable por cada usuario. Cuando un texto te molesta, se lo marcás y Claude extrae el patrón de fondo (no solo la frase literal), te lo propone generalizado y lo suma a `references/reglas-propias.md`. Desde ahí vale igual que las reglas de base.

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

## Créditos

Adaptado de [stop-slop](https://hvpandya.com) de Hardik Pandya.

## Licencia

MIT. Usalo libre, compartilo.
