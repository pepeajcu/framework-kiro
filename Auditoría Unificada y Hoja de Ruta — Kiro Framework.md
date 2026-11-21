Auditoría Unificada y Hoja de Ruta — Kiro Framework

**Fecha:** 12 de noviembre de 2026  
**Alcance:** Consolidación de hallazgos técnicos, de seguridad, entorno, metodología SDD, stack y modelo de negocio.  
**Nota sobre Diseño:** El análisis y rediseño del motor visual queda intencionalmente abierto en este documento para profundizar en una fase dedicada.

---

1\. Errores Técnicos y de Seguridad (Priorizados)

1.1 Prioridad Alta (Críticos de Datos y Disponibilidad)

### A1. El guardado definitivo en base de datos ocurre después de responder al usuario

* **Qué pasa (en simple):** Es como imprimir el ticket de compra antes de cobrar la tarjeta. Cuando alguien guarda un registro o inicia sesión, la app primero responde *"¡Listo\!"* al navegador y una fracción de segundo después intenta confirmar el guardado en PostgreSQL. Si ese guardado falla, el usuario vio éxito pero el dato no existe. En el login, el navegador puede pedir la página siguiente antes de que la sesión termine de guardarse, haciendo que parezca que no inició sesión.  
* **Ubicación:** app/db.py:42-57 y app/deps.py:24 (DbSession \= Annotated\[Session, Depends(get\_db)\]).  
* **Por qué ocurre:** En FastAPI 0.141.1, los generadores con yield usan scope="request" por defecto, ejecutando la parte posterior al yield (session.commit()) después de enviar la respuesta HTTP.  
* **Solución:** Cambiar la inyección en app/deps.py:24 a:

```py
DbSession = Annotated[Session, Depends(get_db, scope="function")]
```

A2. Bloqueo global de inicio de sesión detrás de un proxy inverso (DoS por IP compartida)

* Qué pasa (en simple): Para frenar ataques de fuerza bruta, Kiro bloquea la IP que falle 10 veces el login. Al desplegar detrás de un proxy inverso (Coolify, Traefik, Nginx, Cloudflare), todas las visitas pasan por un mismo "recepcionista" (el proxy). Hoy la app anota la IP interna del proxy en lugar de la IP real de cada visitante. Si una sola persona falla 10 veces, bloquea el login para todos los usuarios del sitio durante 15 minutos.  
* Ubicación: app/routers/auth.py:61-64 (\_client\_fingerprint) y Dockerfile:105.  
* Solución:  
  Añadir \--proxy-headers y \--forwarded-allow-ips (configurable por variable de entorno para redes privadas de Docker/Coolify) en el CMD de producción del Dockerfile.  
  Asegurar que \_client\_fingerprint use la IP real resuelta por el proxy de confianza.

1.2 Prioridad Media (Seguridad, Privacidad y Resiliencia)  
M1. Un login exitoso borra el contador de intentos fallidos de toda la IP

* Qué pasa (en simple): Si alguien falla 9 veces intentando adivinar la contraseña de otra persona, está a un paso del bloqueo. Pero si se registra con una cuenta propia e inicia sesión, Kiro limpia tanto el contador de su correo como el de su IP. Así puede repetir ciclos de 9 intentos contra víctimas indefinidamente.  
* Ubicación: app/routers/auth.py:170 (limiter.reset(buckets)).  
* Solución: Al autenticar con éxito, reiniciar únicamente el bucket del correo (limiter.reset(\[f"login:email:{account.email}"\])) y nunca borrar el bucket login:ip:\*.

M2. Fuga del token de recuperación de contraseña en los logs de acceso

* Qué pasa (en simple): Cuando un usuario abre su enlace para cambiar la contraseña, el código secreto viaja en la URL y el registro de visitas lo anota literalmente. Cualquiera que lea los logs del servidor o de monitoreo durante los siguientes 30 minutos ve ese código y puede tomar la cuenta.  
* Ubicación: app/routers/auth.py:329 y app/middleware/access\_log.py:39.  
* Solución: Redactar /reset-password/\<token\> como /reset-password/\[REDACTED\] en AccessLogMiddleware (y opcionalmente mover el token a una cookie firmada temporal tras el primer GET con redirección 303).

M3. Fuga de secretos de GA4 (api\_secret) y Meta (access\_token) en los logs de error

* Qué pasa (en simple): Google Analytics 4 y Meta exigen enviar sus claves secretas dentro de la URL. Cuando falla la conexión o responden un error, la librería HTTP incluye la URL completa en el texto del error y la app lo imprime en los logs con exc\_info=True, dejando tus claves privadas expuestas en la bitácora.  
* Ubicación: app/analytics/providers/ga4.py:46-59 y app/analytics/providers/meta.py:60-66.  
* Solución: Capturar httpx2.HTTPStatusError y httpx2.RequestError sin exc\_info=True, registrando solo el código de estado HTTP y el tipo de excepción.

M4. Enumeración de cuentas en /register

* Qué pasa (en simple): Tu regla base es que nadie pueda averiguar si un correo ya tiene cuenta. Login y recuperación de contraseña la cumplen, pero el registro responde explícitamente *"Ya existe una cuenta con este email"*, permitiendo verificar correos registrados.  
* Ubicación: app/routers/auth.py:258 vs app/services/auth.py:63-66 y AGENTS.md.  
* Solución: Enviar un correo de aviso al titular cuando el email ya exista y mostrar una respuesta neutra (*"Revisa tu correo para continuar"*), o documentar explícitamente en AGENTS.md si se acepta esta excepción por UX.

M5. Fallo del proveedor de correo en /forgot-password genera 500 y deshace el Rate Limit

* Qué pasa (en simple): Si Resend o SMTP fallan justo al pedir un cambio de contraseña, la petición explota con error 500 solo cuando el correo sí existe (delatando la cuenta) y el rollback de la base de datos borra el intento del contador de seguridad (limiter.record).  
* Ubicación: app/routers/auth.py:321-324 y app/services/auth.py:173.  
* Solución: Capturar EmailDeliveryError dentro de request\_password\_reset, registrarlo en el log sin relanzarlo al router y devolver siempre la misma respuesta.

M6. Sin rotación de token CSRF al iniciar o cerrar sesión

* Qué pasa (en simple): El permiso temporal que protege los formularios (csrf\_token) se crea al entrar como anónimo y dura 14 días sin renovarse cuando el usuario inicia o cierra sesión, exponiendo un vector de fijación si hubiera subdominios comprometidos.  
* Ubicación: app/middleware/csrf.py y app/security.py:130-180.  
* Solución: Emitir un new\_csrf\_token() nuevo dentro de set\_session\_cookie y clear\_session\_cookie.

1.3 Prioridad Baja (Higiene y Casos Borde)

* B1 (app/routers/auth.py:326): POST /forgot-password devuelve 200 OK en vez de redirigir con 303 See Other (Post/Redirect/Get); si el usuario recarga la página, reenvía el formulario.  
* B2 (app/security.py:177 y app/routers/consent.py): Añadir secure=settings.is\_production en clear\_session\_cookie (delete\_cookie) y en la cookie de consentimiento.  
* B3 (app/repositories/note.py:22): Añadir .limit(100) en list\_for\_user para evitar consultas sin cota.  
* B4 (app/templating.py:85, 143): Leer settings desde request.app.state.settings en lugar del singleton global get\_settings().  
* B5 (app/middleware/access\_log.py:35): Envolver call\_next en try/except para que los errores 500 también queden registrados en el log de acceso.  
* B6 (app/services/rate\_limit.py y auth.py:203): Hacer atómico el consumo del token en reset\_password (with\_for\_update() o UPDATE ... WHERE used\_at IS NULL) para evitar condiciones de carrera.  
* B7 (app/routers/seo.py): Usar settings.base\_url.rstrip('/') en robots.txt para evitar //sitemap.xml si BASE\_URL termina en /.  
* B8 (app/routers/health.py y app/models/user.py): Omitir environment en /health y omitir email en User.\_\_repr\_\_.  
* B9 (Limpieza de ejemplo notes): Crear make strip-example (y flag en setup.sh) para eliminar de un golpe el CRUD de muestra (app/routers/notes.py, migración, enlaces en nav\_auth.html, tests) al iniciar un proyecto real.

1.4 Entorno, Dependencias y Despliegue

* E1 (Python 3.15 en pyproject.toml): psycopg\[binary\]==3.3.5 en uv.lock no tiene wheel cp315. Acotar requires-python \= "\>=3.12,\<3.15" en pyproject.toml y fijar versión en CI.  
* E2 (Dockerfile etapa assets): Verificar que design.toml esté compilado en input.css antes de correr tailwindcss en el build de producción para evitar desfases entre CSS y DesignRuntime.  
* E3 (scripts/lib/replace.sh): Asegurar que la sustitución de tokens use el intérprete Python validado (o uv run \--no-project python) antes del bootstrap.

2\. Metodología SDD y Optimización de Tokens

* Fricción actual: El salto entre el "Golden Path directo" (0 ceremonia) y los 4 comandos de especificación (/spec-new → /spec-design → /spec-tasks → /spec-build) obliga a demasiadas aprobaciones manuales en features medianas y consume tokens releyendo archivos en cada paso.  
* Propuesta:  
  Añadir un modo intermedio (/spec-plan) que genere un único documento compacto (Requisitos verificables \+ Capas \+ Checklist de tareas) para aprobar en una sola parada antes de /spec-build.  
  Adelgazar AGENTS.md moviendo ejemplos largos de código a .claude/skills/, dejando en el archivo raíz únicamente las reglas duras y la arquitectura que archcheck.py vigila mecánicamente.

3\. Evaluación del Stack Tecnológico

* Veredicto: Mantener Python 3.12+ · FastAPI · SQLAlchemy 2.0 Síncrono · PostgreSQL · Jinja2 · HTMX · Tailwind v4 CLI · Basecoat. Es ideal para desarrollo con IA porque elimina la duplicación de estado, los errores de hidratación y las alucinaciones de async en plantillas (MissingGreenlet).  
* Mejoras puntuales:  
  Mover el envío de correos (emailer.send) fuera del hilo síncrono de la petición HTTP (BackgroundTasks o cola en Postgres) para no bloquear respuestas si el proveedor SMTP/Resend es lento.  
  Añadir un micro-helper declarativo propio (kiro-ui.js, \~2 KB) con atributos data-ui-\* para interacciones locales simples (tabs, toggles, drawers) sin depender de viajes al servidor ni escribir JS libre por página.

4\. Propuesta de Negocio: Core Ligero \+ Módulos Oficiales

* Diferenciador real frente a ShipFast y SaaS Pegasus: Kiro no vende solo plantillas pre-escritas; vende código que la IA no puede corromper, respaldado por verificación mecánica (make archcheck \+ make check).  
* Arquitectura comercial en 2 niveles (sin engordar el Core):  
  Core (MIT, este repo): Auth, Email, SEO, Analítica, Motor de Diseño y Guardrails (archcheck).  
  Módulos Oficiales Instalables (bajo el mismo Golden Path de 8 capas):  
  kiro-payments (Stripe / LemonSqueezy \+ webhooks idempotentes).  
  kiro-jobs (Cola de tareas en PostgreSQL con FOR UPDATE SKIP LOCKED, sin Redis).  
  kiro-storage (Subida de archivos local en dev y S3 / Cloudflare R2 en producción).  
  kiro-admin (Panel de administración de usuarios, roles y métricas).  
  kiro-auth-plus (Magic Links \+ OAuth social).

5\. Diseño Visual (Pendiente de Profundización)

* Objetivo declarado: Resolver de manera óptima la generación de interfaces para lograr diseños únicos, memorables y con identidad real, evitando que las páginas se vean generadas por IA o que terminen pareciendo todas iguales por seguir un mismo *design system* rígido.  
* Estado: Esta sección no se define ni se modifica todavía. Queda reservada para una sesión dedicada exclusivamente a explorar y diseñar la mejor arquitectura posible antes de tocar el motor actual.

6\. Plan de Acción Inmediato (Pre-Diseño)

1. Parches críticos de datos y proxy: Depends(get\_db, scope="function") en app/deps.py, \--proxy-headers en Dockerfile y resolución real de IP.  
2. Hardening de Auth y Logs: No resetear el bucket de IP en login, redactar /reset-password/{token} en access\_log.py, quitar exc\_info=True de ga4.py / meta.py, capturar EmailDeliveryError, rotar CSRF en login/logout y resolver enumeración en /register.  
3. Entorno y Limpieza: Acotar requires-python \= "\>=3.12,\<3.15" en pyproject.toml y crear make strip-example.  
4. Siguiente sesión: Profundizar exclusivamente en la arquitectura del sistema de diseño para lograr resultados únicos y memorables.

