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
| [0006](0006-nombre-kiro.md) | Conservar el nombre "Kiro" pese a la colisión | Provisional |
| [0007](0007-sin-alpinejs.md) | Sin Alpine.js | Aceptada |
| [0008](0008-sesiones-en-base-de-datos.md) | Sesiones en base de datos, no JWT | Aceptada |
| [0009](0009-csrf-doble-envio.md) | CSRF de doble envío, validado como dependencia | Aceptada |
| [0010](0010-cabeceras-de-seguridad-y-csp.md) | Cabeceras de seguridad y CSP con `'unsafe-inline'` | Aceptada |
