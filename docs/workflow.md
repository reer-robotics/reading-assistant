# Fixed reading workflow

The manifest is `src/reading_assistant/workflow.json`. The only AI skill is versioned in `skills/assess.json`; other stages are ordinary deterministic code. There is one optional local model and no autonomous agent loop.

| Stage | Responsibility | Boundary |
| --- | --- | --- |
| Capture | Split the current draft into paragraphs; produce content IDs, character offsets and a draft hash | Up to 24 paragraphs / 30,000 characters; offsets are Unicode code points |
| Retrieve | Filter the catalog by trusted audiences, then match terms in title, tags and passage text | Never send an unauthorized source to scoring or the model |
| Rank | BM25-style score; two shared terms minimum; internal tier then curated tier; four distinct sources at most | Scores indicate retrieval ordering, not probability or factual quality |
| Assess (optional) | One local model explains candidate relevance and suggests reading/citation/conflict categories | Exactly the retrieved IDs; no sources, excerpts or citation metadata may be supplied by the model |
| Validate | JSON schema, allowed IDs and unique coverage | Invalid model output fails the whole request; no repair loop or silent fallback |
| Display | Matching passage/card colors and P-labels; source notes and explicit actions | Browser discards results for an old draft revision; human decides what to insert |

The model returns every candidate once, ordered by relevance. The engine preserves paragraph order and internal/external tiers while applying that order within each tier. It never rewrites the draft. Interpretations can be wrong even when schemas and IDs pass validation. Source maturity is context, not proof.

The AI request uses only the approved local endpoint. `/api/show` checks completion capability and rejects remote metadata. Requests do not follow redirects or inherit proxy settings. An error remains visible; automatic browser updates pause. No model is downloaded. The adapter has a 100,000-character context limit and a 180-second HTTP timeout. These are prototype resource bounds, not performance promises.

## Update and color behavior

A button always requests a fresh result. The optional timer runs at 30/60/120/300 seconds, defaults to 60, and skips unchanged drafts and hidden tabs. A generation counter detects changes during a request, even if the user changes text and then changes it back. A browser-side busy flag and a server-side lock prevent overlapping work.

Each paragraph gets a P-number and one of six colors. The matching cards reuse both. Colors repeat after P6; labels remain distinct. The numbering/color assignment follows paragraph order within a draft snapshot; inserting a paragraph can change subsequent numbers. Stable content IDs connect exact passages within the snapshot, including duplicate-paragraph occurrence numbers.

Editing invalidates the old associations and disables citation insertion. Clicking a fresh card label returns to its paragraph. Linked view shows the colored writing; Edit shows plain editable text while cards remain visible. A future rich editor may render inline highlights while typing using the same result contract.

## Citation format

`source-note-v1` uses a Markdown footnote marker `[^SOURCE:PASSAGE]` plus a definition containing authors, date, title, locator, version, and original URL or internal source ID. Missing authors/dates are explicit. The interface inserts the marker only on request; it exports the corresponding definition with the draft. It does not claim APA, Chicago, or IEEE conformity.

Citation insertion uses Unicode code-point offsets from the same draft snapshot, including emoji. Repeated insertion of the same marker into the same passage is blocked. After insertion the draft is stale and needs another recommendation request. Notes whose markers were removed are omitted from downloaded Markdown.

## Provenance and limitations

Results include a draft SHA-256, permitted-catalog SHA-256, evidence hashes, workflow version and assessment skill version. They are returned to the caller; the service does not persist an audit database. Model tags can change, and a skill version is not a cryptographic attestation of model execution. Pin models and catalog snapshots separately when reproducibility matters.

Version 0.1 validates this workflow with deterministic examples, mocked Ollama responses and browser interactions. Real-model semantic performance has not been measured. Synonyms, multilingual ranking, large-catalog indexing and citation entailment remain future evaluation work.
