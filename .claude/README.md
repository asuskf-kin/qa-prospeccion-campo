# .claude

Contexto del proyecto para trabajar con Claude Code, y la documentación que hace
falta para entender y replicar el QA sin haber estado en las conversaciones.

```
.claude/
├── settings.json          permisos del proyecto
├── commands/
│   ├── correr-qa.md       /correr-qa [pais]
│   └── nuevo-pais.md      /nuevo-pais <pais> <ISO3>
└── docs/
    ├── dominio.md         qué es cada fuente, columna y categoría
    ├── hallazgos.md        las conclusiones con sus cifras
    ├── decisiones.md      por qué el código es así, y las trampas
    └── replicar.md        levantar el proyecto y añadir un país
```

El punto de entrada es [`../CLAUDE.md`](../CLAUDE.md) en la raíz, que Claude Code
carga solo. Estos documentos son la referencia profunda a la que apunta.

## Por dónde empezar

| Si vas a… | Lee |
|---|---|
| entender de qué va el proyecto | `../CLAUDE.md` |
| tocar el análisis | `docs/dominio.md`, después `docs/decisiones.md` |
| presentar los resultados | `docs/hallazgos.md` |
| correrlo en tu máquina | `docs/replicar.md` |
| añadir un país | `docs/replicar.md`, o `/nuevo-pais` |

## Sobre los permisos

`settings.json` deniega tres cosas a propósito:

- **leer `data/*/raw/**` con la herramienta Read** — son CSV de 38 y 58 MB;
  inspecciónalos con `python -c` y una consulta concreta
- **escribir en `data/*/raw/**`** — son los insumos tal como llegaron; el
  análisis no los modifica
- **escribir en `*_EDITADO*`** — los deck con mapas pegados a mano. No están en
  git y regenerar encima destruye trabajo
