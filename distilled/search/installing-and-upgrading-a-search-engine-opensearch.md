---
url: "https://learn.liferay.com/w/dxp/search/installing-and-upgrading-a-search-engine/opensearch"
capability: search
fetched_at: "2026-07-01T13:47:16Z"
content_hash: "sha256:acfcff18b720db2009e53605aa492078d0a1d2601546c43ba2360ce58b4e4e2a"
distilled_at: "2026-07-01T00:00:00Z"
---
## Conceptos clave

- OpenSearch es una alternativa a Elasticsearch (el motor nativo) soportada desde Liferay DXP 2025.Q1.
- Requiere instalar el conector "Liferay Connector to OpenSearch 2" (GA) desde Liferay Marketplace; si venías usando el conector beta, hay que reinstalar la versión GA, no basta con actualizar.
- Con el toolkit Cloud Native Experience AWS Ready, el dominio de Amazon OpenSearch y su conexión se aprovisionan automáticamente.

## Decisiones prácticas y gotchas

- OpenSearch **no soporta** estas features de Liferay Enterprise Search: Cross-Cluster Replication, Monitoring, Learning to Rank. Si el cliente necesita alguna de estas, la decisión de arquitectura debe ser Elasticsearch, no OpenSearch.
- Verificar la matriz de compatibilidad de versiones Liferay↔OpenSearch antes de comprometerse con esta ruta.
- La versión del conector debe coincidir con el release de Liferay DXP en uso (consultar la matriz de compatibilidad para el conector correcto).

## Fuente

https://learn.liferay.com/w/dxp/search/installing-and-upgrading-a-search-engine/opensearch
