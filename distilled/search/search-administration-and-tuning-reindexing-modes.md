---
url: "https://learn.liferay.com/w/dxp/search/search-administration-and-tuning/reindexing-modes"
capability: search
fetched_at: "2026-07-01T13:48:08Z"
content_hash: "sha256:ee1f67615f6bb66603c886043d3a06168d70ffac5b654a86905cf2453335a286"
distilled_at: "2026-07-01T00:00:00Z"
---
## Conceptos clave

- Desde Liferay DXP 2023.Q4 / Portal GA102+ hay 3 modos de reindexado, ejecutables desde Global Menu → Control Panel → Search → Index Actions:
  - **Full**: borra el índice y lo regenera desde cero. Sin alta disponibilidad (downtime). Único modo válido para conectar un clúster Elasticsearch nuevo/vacío.
  - **Concurrent**: crea un índice nuevo en paralelo (blue/green) y borra el antiguo al terminar. Alta disponibilidad para reindexar TODO el contenido. No sirve para single-model reindex.
  - **Sync**: actualiza documentos existentes in place y borra los obsoletos al terminar. Alta disponibilidad, apto también para single-model reindex, pero no tiene en cuenta cambios de mappings/settings del índice.
- Full es el modo por defecto del sistema; se cambia en System Settings → Platform → Search → Reindex → Default Reindex Execution Mode.

## Decisiones prácticas y gotchas

- **Concurrent y Sync no están disponibles con Solr** — solo funcionan con Elasticsearch/OpenSearch.
- Concurrent requiere más espacio en disco que los otros modos (mantiene ambos índices simultáneamente); Liferay estima el espacio disponible y avisa si es insuficiente, pero es una consideración de capacidad a validar antes de ejecutar en producción.
- Reglas prácticas de elección:
  - Instalar clúster Elasticsearch nuevo → Full (único disponible).
  - Cambiar field mappings / index settings / upgrade de Liferay → Concurrent recomendado (Full también funciona pero con downtime).
  - Reindexar tras un corte de conexión → Concurrent recomendado, Sync también disponible.
  - Reindexar un único modelo (p. ej. tras crear un search blueprint o activar semantic search) → Sync recomendado; Full es fallback si Sync no basta. Concurrent no aplica a single-model.
- Sync no reconstruye mappings/settings — si cambiaste la estructura del índice, Sync no es suficiente aunque sea el modo "más barato".

## Fuente

https://learn.liferay.com/w/dxp/search/search-administration-and-tuning/reindexing-modes
