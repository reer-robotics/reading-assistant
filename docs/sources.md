# Source catalogs

The input is a JSON object with `schema_version: 1` and a `sources` array. Start by copying `src/reading_assistant/demo/catalog.json` to a directory outside your public checkout.

Each source needs:

| Field | Meaning |
| --- | --- |
| `id` | Stable identifier beginning with a letter; letters, digits, hyphens and underscores only |
| `title`, `authors`, `issued` | Bibliographic metadata. Use an empty authors list or date string when unknown |
| `origin` | `internal` or `curated_external` |
| `version` | The actual source revision or snapshot description |
| `maturity` | `observation`, `peer_validated`, `approved`, or `external_reference` |
| `url` | Original HTTPS link for curated external sources; internal sources may leave it empty |
| `synthetic` | True for invented examples; do not relabel examples as company findings |
| `access` | One or more trusted audience labels, or `public` |
| `tags` | Curator-supplied indexing terms; these influence lexical ranking |
| `passages` | Stored text excerpts with unique IDs and meaningful page/section locators |

A `public` source is visible to every audience. Otherwise a source is visible only if one of its labels matches the configured audience. An external reference can also have restricted access, for example a licensed internal reference collection. This filtering protects the response only when the caller's audience is trusted. In the demo it is selected by the process operator; a future hosted service must derive it from authenticated identity.

```json
{
  "schema_version": 1,
  "sources": [{
    "id": "PUBLIC-METHOD",
    "title": "Your method document",
    "origin": "internal",
    "authors": [],
    "issued": "",
    "version": "revision-1",
    "maturity": "observation",
    "url": "",
    "synthetic": true,
    "access": ["engineering"],
    "tags": ["experiment", "method"],
    "passages": [{"id": "method", "locator": "Method, paragraph 1", "text": "Replace this example with a permitted source excerpt."}]
  }]
}
```

Start with `readassist --catalog /absolute/path/catalog.json --audience engineering serve`. The service loads the catalog at startup; restart it after changing the catalog. It does not fetch, crawl or refresh source URLs. Opening an original link in the browser is an explicit user action.

Use accurate excerpts, not model-authored summaries presented as quotations. If a curator adds a summary, label it in the text and identify its provenance. Avoid storing long copyrighted texts without redistribution rights. Keep retrieved text and locators synchronized with source revisions; evidence hashes identify the exact stored excerpts.

No PDF/Word parser is included here. An ingestion adapter may later transform authorized documents into this catalog contract, including content prepared with Document Formatter. Such an adapter must preserve source identities and page/section locations rather than treating generated writing as original evidence.
