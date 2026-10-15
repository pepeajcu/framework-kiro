# 0016 — `make check` es la puerta de CI, y las reglas de AGENTS.md las comprueba una máquina

**Estado:** Aceptada · 2026-10-14

## Contexto

AGENTS.md lista diez reglas duras. `mypy --strict` y `ruff` cubren una (los tipos) y
media (los nombres); el resto vivía solo en prosa, y una IA (o una persona con prisa)
las incumple mientras todo lo demás sigue en verde. La auditoría de 2026-10-14 lo
confirmó con código real, no con hipótesis:

- un handler de página sin `OptionalUser` (regla 10), y cuatro POST que
  re-renderizan una página sin declararlo, con la cabecera mostrando "Entrar" a
  alguien que ya había entrado;
- un servicio que importaba `fastapi.Request` (`services/consent.py`);
- la regla "router → servicio → repositorio, sin excepciones" que el propio
  `notes.py` y la skill `kiro-feature` incumplían en las lecturas.

Además, `make check` decía ser "lo que corre CI" y no lo era: CI mantenía su propia
lista de pasos (compilaba Tailwind y corría el contrato de diseño; `make check` no),
y el hook de mypy de `pre-commit` montaba un entorno aparte con una lista de
dependencias a mano que se desfasó y fallaba.

Alternativas reales:

- **`import-linter`**: una dependencia más, solo ve imports (no `async def` sin
  `await`, ni un `.create()` desde un router, ni plantillas) y su mensaje no dice
  qué hacer en su lugar.
- **`ruff` con `TID251` (banned-api)**: cubre prohibiciones de import por módulo,
  nada de lo estructural, y no mira Jinja.
- **Revisión por la IA** ("comprueba las reglas antes de acabar"): es exactamente lo
  que ya fallaba.

## Decisión

1. **`scripts/archcheck.py`**, solo librería estándar (`ast` más expresiones
   regulares sobre las plantillas). Trece reglas con identificador (K1-K8 para
   Python, J1-J5 para plantillas), documentadas en AGENTS.md. Cada violación dice
   archivo, línea, qué hacer en su lugar y qué regla rompe.
2. **Una excepción exige un motivo** (`# kiro: allow K6 — motivo`, o su forma
   Jinja). Sin motivo no cuenta, y todas las excepciones vigentes se listan en
   cada ejecución.
3. **Lecturas sí, escrituras no.** Un router puede leer de un repositorio; escribir
   (`create/update/delete`) pasa siempre por un servicio, aunque sea de una línea
   (K4). Es lo que ya hacía `notes.py` para escribir; ahora está escrito y se
   comprueba.
4. **`make check` es la definición única de "en verde"**: `lint types css archcheck
   test migrations-check` más el contrato de diseño con `allow_defaults=1`. CI
   ejecuta `make check` (con `PYTEST_ADDOPTS` para la cobertura) y añade solo
   `pip-audit` y la imagen de Docker.
5. Los hooks de `pre-commit` de mypy y de archcheck son locales (`uv run`): el mismo
   entorno que `make check`, sin lista de dependencias que mantener.

## Consecuencias

- Un proyecto existente puede ver violaciones nuevas al actualizar. Cada una trae su
  arreglo, y una excepción con motivo las silencia donde de verdad aplique.
- Son heurísticas, no un análisis completo: K4 reconoce un repositorio por el
  nombre de la clase (`...Repository`), K7 busca `render(request, "pages/...")`.
  Un falso positivo se resuelve con una excepción razonada; un falso negativo se
  descubre añadiendo un caso a `tests/test_archcheck.py`, que tiene una violación y
  un caso correcto por regla.
- `make check` tarda unos segundos más (compila Tailwind) y exige el binario de
  Tailwind, que `make css` ya descarga. En un proyecto recién clonado el contrato de
  diseño sigue avisando de que no tiene identidad, sin fallar; un contrato roto, un
  `input.css` desfasado o una fuente ausente sí rompen. Esto sustituye lo que decía
  el ADR-0014 ("no forma parte de `make check`").
- `scripts/archcheck.py` y `tests/test_archcheck.py` viajan a cada proyecto
  generado, y su test lee AGENTS.md: si se borra una regla de uno, el otro avisa.
- CI ya no tiene un paso por comprobación, así que un fallo se localiza por la
  salida de `make check` y no por el nombre del paso.
