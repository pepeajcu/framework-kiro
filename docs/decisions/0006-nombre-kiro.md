# 0006 — Conservar el nombre "Kiro" pese a la colisión

**Estado:** Provisional · 2026-09-01
**Debe resolverse antes de:** la publicación pública (v1.0.0)

## Contexto

"Kiro" es también el nombre del IDE agéntico de AWS ([kiro.dev](https://kiro.dev)),
disponible de forma general desde marzo de 2026. Está en el mismo nicho —
herramientas de desarrollo asistido por IA — lo que implica:

- **SEO:** imposible posicionar "Kiro framework" frente a AWS.
- **Confusión:** el IDE de AWS popularizó el desarrollo dirigido por
  especificaciones (`requirements.md` / `design.md` / `tasks.md`), y este
  framework incorpora un flujo parecido. La confusión sería casi inevitable.
- **Marca:** riesgo bajo pero no nulo en un producto público.

## Decisión

Conservar "Kiro" durante el desarrollo. Para uso interno y de agencia el
conflicto no tiene coste real, y detener el trabajo por elegir nombre sí lo
tiene.

Para que renombrar siga siendo barato, el nombre está **contenido**: aparece
como token sustituible y en un conjunto acotado de archivos, nunca incrustado en
identificadores de código. El paquete de la aplicación se llama `app`, no `kiro`.

## Consecuencias

- Antes de publicar hay que tomar la decisión definitiva. Está en la Fase 4 del
  plan, no es un pendiente flotante.
- Renombrar debe seguir costando minutos. **Regla:** ningún módulo, clase ni
  variable de Python lleva "kiro" en el nombre. La única excepción son los
  prefijos internos de `setup.sh` (`__KIRO_*__`, `KIRO_REPLACE_FILES`), que
  desaparecen del proyecto generado.
- Verificable: `grep -ri kiro app/` no debe devolver identificadores de código.
