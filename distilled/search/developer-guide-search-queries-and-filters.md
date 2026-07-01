---
url: "https://learn.liferay.com/w/dxp/search/developer-guide/search-queries-and-filters"
capability: search
fetched_at: "2026-07-01T13:46:45Z"
content_hash: "sha256:b981e9c2da11e351be932cc836e7474f718887e51f01aee1312b006ae6fda5ff"
distilled_at: "2026-07-01T00:00:00Z"
---
## Conceptos clave

- Las APIs de query están en el módulo `portal-search-api`. Se construyen queries y filtros con el mismo tipo de objetos (`Query`), y se añaden a la request con métodos distintos según el rol:
  - `SearchRequestBuilder.query(fooQuery)` → afecta al relevance scoring.
  - `SearchRequestBuilder.postFilterQuery(fooQuery)` → filtra sin afectar al score (yes/no puro).
- **Filtros** responden sí/no sin calcular relevancia; **queries** responden lo mismo pero calculan un score de relevancia (full-text match).
- Para campos anidados (object fields, web content structure fields, document/media metadata sets) hay que usar `NestedQuery` con el `path` correcto (`ddmFieldArray` para web content/metadata, `nestedFieldArray` para objects) y un `BooleanQuery` con dos cláusulas MUST (una para el nombre del campo, otra para el valor).
- Para inspeccionar la query real generada por el motor de búsqueda, existe una utilidad de troubleshooting documentada aparte (Elasticsearch query inspection).

## Decisiones prácticas y gotchas

- Hay que setear `searchContext.setKeywords(...)` explícitamente, o habilitar `searchRequestBuilder.emptySearchEnabled(true)` — si no, la búsqueda falla o se comporta de forma inesperada.
- El campo `folderId` se usa típicamente como filtro (no query) para acotar a la carpeta raíz (`folderId = 0`); contenido anidado en subcarpetas no tiene `folderId = 0` y por tanto no aparece en resultados filtrados por ese criterio — las carpetas en sí sí aparecen porque viven en la carpeta raíz.
- No existe una API separada para "filtrar": se construye la query igual que siempre y se añade con `postFilterQuery` en vez de `query`.

## Código relevante

Inicializar el builder de la request:

```java
SearchRequestBuilder searchRequestBuilder =
	_searchRequestBuilderFactory.builder();
```

Poblar el `SearchContext` (compañía, clases de entidad a buscar, keywords):

```java
searchRequestBuilder.withSearchContext(
	searchContext -> {
		searchContext.setCompanyId(_portal.getDefaultCompanyId());
		searchContext.setEntryClassNames(
			new String[] {
				"com.liferay.document.library.kernel.model.DLFileEntry",
				"com.liferay.document.library.kernel.model.DLFolder",
				"com.liferay.journal.model.JournalArticle",
				"com.liferay.journal.model.JournalFolder"
			});
		searchContext.setKeywords(keywords);
	});
```

Construir un `BooleanQuery` con dos cláusulas MUST (term + match) y ejecutar la búsqueda:

```java
BooleanQuery booleanQuery = _queries.booleanQuery();

booleanQuery.addMustQueryClauses(
	_queries.term(Field.FOLDER_ID, "0"),
	_queries.match(
		StringBundler.concat(
			"localized_", Field.TITLE, StringPool.UNDERLINE,
			LocaleUtil.US),
		keywords));
```

```java
SearchRequest searchRequest = searchRequestBuilder.query(
	booleanQuery
).build();

SearchResponse searchResponse = _searcher.search(searchRequest);

SearchHits searchHits = searchResponse.getSearchHits();

for (SearchHit searchHit : searchHits.getSearchHits()) {
	Document document = searchHit.getDocument();

	String uid = document.getString(Field.UID);

	System.out.println(
		StringBundler.concat(
			"Document ", uid, " has a score of ",
			searchHit.getScore()));
}
```

Referencias OSGi típicas para este tipo de código:

```java
@Reference
private Portal _portal;

@Reference
private Queries _queries;

@Reference
private RoleLocalService _roleLocalService;

@Reference
private Searcher _searcher;

@Reference
private SearchRequestBuilderFactory _searchRequestBuilderFactory;

@Reference
private UserLocalService _userLocalService;
```

Query anidada para campos de web content structure / object fields (mismo patrón para ambos, solo cambia el `path`):

```java
BooleanQuery booleanQuery = queries.booleanQuery();

MatchQuery fieldNameQuery = queries.match("ddmFieldArray.ddmFieldName", "ddm__text__35174__Text25689566_en_US");

MatchQuery fieldValueQuery = queries.match("ddmFieldArray.ddmFieldValueKeyword_en_US", keywords);

booleanQuery.addMustQueryClauses(fieldNameQuery, fieldValueQuery);

NestedQuery nestedQuery = queries.nested("ddmFieldArray", booleanQuery);
```

Filtrar (patrón `postFilterQuery` + `query` combinados):

```java
TermQuery termQuery = _queries.term(Field.FOLDER_ID, "0");

searchRequestBuiler.postFilterQuery(termQuery);

MatchQuery matchQuery = _queries.match(
    StringBundler.concat(
        "localized_", Field.TITLE, StringPool.UNDERLINE,
           LocaleUtil.US), keywords);

searchRequestBuilder.query(matchQuery);

SearchRequest searchRequest = searchRequestBuilder.build();
```

## Fuente

https://learn.liferay.com/w/dxp/search/developer-guide/search-queries-and-filters
