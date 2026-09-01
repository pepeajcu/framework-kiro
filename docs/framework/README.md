# Documentación interna del framework

Esta carpeta es **FRAMEWORK-ONLY**: `setup.sh` la elimina de los proyectos
generados. Aquí vive lo que importa para desarrollar *Kiro*, no para desarrollar
*con* Kiro.

- [`vision.md`](vision.md) — el documento original que dio origen al framework.
  Se conserva como registro de intención. Donde contradiga a los ADRs, mandan
  los ADRs: son decisiones posteriores y razonadas.
- [`roadmap.md`](roadmap.md) — fases y estado actual.
- [`contributing.md`](contributing.md) — cómo trabajar en el framework.

Las decisiones de arquitectura viven en [`../decisions/`](../decisions/), que sí
se queda en los proyectos generados: un agente necesita saber *por qué* el stack
es como es para no proponer deshacerlo cada sesión.
