# 0008 — Sesiones en base de datos, no JWT

**Estado:** Aceptada · 2026-09-03

## Contexto

Un proyecto con usuarios tiene que decidir dónde vive la sesión. Las dos rutas
habituales:

- **Token autocontenido (JWT).** El navegador lleva un token firmado con el id
  del usuario dentro. El servidor no consulta nada: verifica la firma y ya. Es
  la opción por defecto en casi todo tutorial reciente, y la que una IA propone
  sin que se le pregunte.
- **Sesión con estado.** El navegador lleva un identificador opaco; el servidor
  guarda una fila con a quién pertenece y hasta cuándo vale.

La diferencia práctica aparece el día que hay que echar a alguien. Un JWT es
válido hasta que caduca **por definición**: no hay forma de invalidarlo sin
consultar una lista de revocados —que es, exactamente, la consulta a base de
datos que el JWT prometía evitar—. Los escenarios no son hipotéticos:

- Alguien cambia su contraseña porque cree que se la han robado. Con JWT, quien
  la robó sigue dentro hasta que su token caduque solo.
- Un empleado se va. Su token sigue funcionando.
- Se pierde un portátil con la sesión abierta.

El argumento a favor del JWT es evitar una consulta por petición. En este stack
esa consulta va por clave primaria indexada, en la misma conexión que la
petición ya tiene abierta, y con la carga del usuario en el mismo `JOIN`.

Aparte, cómo se guardan las contraseñas. bcrypt sigue siendo aceptable, pero
tiene un límite de 72 bytes que trunca en silencio, y no es *memory-hard*: una
GPU lo ataca en paralelo mucho mejor que a argon2id, ganador del Password
Hashing Competition y primera recomendación de OWASP.

## Decisión

**Sesiones en la tabla `user_sessions`, contraseñas con argon2id.**

La cookie lleva un token opaco de 256 bits firmado con `SECRET_KEY`; la tabla
guarda solo su SHA-256. Cambiar una contraseña revoca todas las sesiones de esa
cuenta. Rotar `SECRET_KEY` cierra todas las del sitio.

El modelo se llama `UserSession`, no `Session`, porque el código está lleno de
`sqlalchemy.orm.Session` y dos cosas con el mismo nombre en el mismo archivo
cuestan una tarde de depuración.

## Consecuencias

- Cerrar sesión, en un dispositivo o en todos, es un `UPDATE`. Echar a alguien
  es inmediato y auditable.
- Una consulta indexada por petición. Con `lazy="joined"` sobre el usuario, una
  sola.
- Un volcado de la base de datos no entrega ninguna sesión utilizable: los
  tokens están hasheados.
- **Coste real:** la tabla crece y nadie la limpia sola. Hay
  `UserSessionRepository.delete_expired()` para cuando haga falta, pero el
  framework no trae planificador; en un proyecto con mucho tráfico hay que
  llamarlo desde algún sitio.
- **Coste real:** no sirve para autenticar entre servicios distintos. Si algún
  día hace falta una API para terceros, eso es un token aparte —no reabrir
  esto—.
- argon2id usa 64 MiB por verificación. Es intencional: es lo que hace cara la
  fuerza bruta. En una máquina muy pequeña, con muchos logins simultáneos, ese
  consumo se nota, y bajarlo tiene su propio precio.
