# Decisiones de arquitectura (ADRs)

Cada archivo registra una decisión, su contexto y sus consecuencias.

**Para agentes de IA:** léelos antes de proponer cambiar el stack. Casi toda
alternativa "obvia" (Django, React, async, npm) ya se evaluó aquí y se descartó
por un motivo concreto. Si crees que una decisión debe revisarse, di **cuál** y
**qué información nueva** la invalida — no la deshagas por tu cuenta.

| # | Decisión | Estado |
|---|---|---|
| [0001](0001-python-sobre-go.md) | Python en vez de Go | Aceptada |
| [0002](0002-sqlalchemy-sincrono.md) | SQLAlchemy síncrono, no async | Aceptada |
| [0003](0003-git-clone-sobre-plantillas.md) | `git clone` + `setup.sh` como distribución | Aceptada |
| [0004](0004-basecoat-en-vez-de-portar-shadcn.md) | Adoptar Basecoat en vez de portar shadcn/ui | Aceptada |
| [0005](0005-sin-nodejs.md) | Cero Node.js en el toolchain | Aceptada |
| [0006](0006-nombre-kiro.md) | Conservar el nombre "Kiro" pese a la colisión | Aceptada |
| [0007](0007-sin-alpinejs.md) | Sin Alpine.js | Aceptada |
| [0008](0008-sesiones-en-base-de-datos.md) | Sesiones en base de datos, no JWT | Aceptada |
| [0009](0009-csrf-doble-envio.md) | CSRF de doble envío, validado como dependencia | Aceptada |
| [0010](0010-cabeceras-de-seguridad-y-csp.md) | Cabeceras de seguridad y CSP con `'unsafe-inline'` | Aceptada |
| [0011](0011-consentimiento-y-analitica.md) | Consentimiento por cookie y analítica server-side sin bloquear al usuario | Aceptada |
| [0012](0012-registro-de-sitemap.md) | Sitemap por registro de proveedores, no por consulta a un modelo | Aceptada |
| [0013](0013-identidad-visual-con-taste-skill.md) | Identidad visual: `DESIGN.md`, tokens de marca y taste-skill | Aceptada |
| [0014](0014-motor-de-diseno.md) | Motor de diseño: `design.toml`, compilador, layouts y percepción | Aceptada |
| [0015](0015-motion-vendorizado-por-niveles.md) | Motion declarativo, por niveles y vendorizado bajo demanda | Aceptada |
| [0016](0016-make-check-es-ci-y-reglas-comprobadas.md) | `make check` es la puerta de CI y las reglas de AGENTS.md las comprueba una máquina | Aceptada |
| [0017](0017-errores-y-avisos-de-htmx.md) | Errores y avisos de HTMX: un contrato, no una página por respuesta | Aceptada |
| [0018](0018-constitucion-de-diseno-y-tuberia-unica.md) | Constitución de diseño y una sola tubería hacia el contrato | Aceptada |
| [0019](0019-uupm-vendorizado-con-solapamiento.md) | uupm vendorizado, traducido una vez a Kiro, y el suelo comprobado por una máquina | Aceptada |
| [0020](0020-kit-ios-superficie-auto-y-fuente-del-sistema.md) | Kit iOS, `surface = "auto"` y `fallback = "system"` | Aceptada |
| [0021](0021-referencias-externas-un-lector-y-candados.md) | Referencias externas: un lector tolerante, skillui como herramienta opcional y candados | Aceptada |
| [0022](0022-formularios-con-memoria-y-avisos-tras-redireccion.md) | Formularios con memoria y avisos tras una redirección | Aceptada |
| [0023](0023-densidad-compilada-y-estados.md) | Densidad compilada y los tres estados | Aceptada |
