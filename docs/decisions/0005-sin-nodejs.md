# 0005 — Cero Node.js en el toolchain

**Estado:** Aceptada · 2026-09-01

## Contexto

Tailwind CSS se distribuye normalmente por npm, lo que arrastraría Node.js,
`package.json`, `node_modules` y una etapa extra en el Dockerfile — a un
proyecto que por lo demás es exclusivamente Python.

Existen dos piezas que lo hacen innecesario:

- El **CLI standalone de Tailwind**: un ejecutable autocontenido, sin Node.
- **`pytailwindcss`**: paquete de pip que descarga y gestiona ese ejecutable,
  así que Tailwind entra por la misma puerta que el resto de dependencias.

Basecoat (ADR-0004) se distribuye por npm, pero sus macros y su CSS se copian al
repositorio una sola vez, así que tampoco requiere npm en tiempo de ejecución.

## Decisión

**Ningún Node.js en el proyecto.** Tailwind vía `pytailwindcss`; Basecoat y HTMX
vendorizados en `app/static/`.

## Consecuencias

- Un solo gestor de paquetes (`uv`) y un solo lenguaje en el toolchain. Menos
  que instalar, menos que explicar y menos que puede romperse.
- Dockerfile sin etapa de Node: imagen más pequeña y build más rápido.
- HTMX y el JS de Basecoat se sirven desde `app/static/`, no desde un CDN. Esto
  no es solo purismo: evita una petición externa que bloquea el render, no filtra
  visitas a terceros, y funciona sin conexión.
- Limitación aceptada: no se pueden usar plugins de Tailwind que requieran Node.
  Con Basecoat cubriendo los componentes, no ha hecho falta ninguno.
