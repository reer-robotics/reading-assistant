# Integration choices

The library and versioned schemas are the stable boundary for this prototype. Keep the company journal, Document Formatter, and Reading Assistant as independent repositories. Do not copy private knowledge into this public repository to connect them.

## Option 1: standalone local tool

Run `readassist serve`. Paste a section into Edit, request recommendations, and download Markdown with explicit source notes. This is the implemented browser demo and requires no changes to Docusaurus or Decap.

## Option 2: library in a trusted backend

Call `Recommender(catalog, audiences=trusted_groups, model=optional_local_model).recommend(draft)` from an authenticated application. Pass audiences derived from server-side identity; never trust a browser-supplied group list. The library has no identity provider itself. Do not share an engine with the wrong user's audiences.

The result has:

- `draft_sha256`: the exact analyzed UTF-8 text.
- `paragraphs`: IDs, P-labels, colors, text, and `[start, end)` Unicode code-point offsets.
- `recommendations`: each card's `passage_id`, source metadata, source-owned evidence, locator, citation and assessment.
- `workflow`: mode provenance and versions.

JavaScript strings use UTF-16 offsets; convert with `Array.from(text)` or an equivalent mapping before applying Python offsets. Only apply an insertion to an unchanged draft. The included `web/state.js` shows revision counters and code-point insertion.

## Option 3: side panel in an editor

Build a Decap custom widget/editor extension or an independent companion panel that sends the current section to a trusted backend. Reuse the recommendation schema and label/color mapping. This adapter is a documented extension point, **not implemented in 0.1**.

An editor integration should:

1. Capture a draft revision, paragraph ranges and current access context.
2. Use the Recommend button or an opt-in timer; skip unchanged content and avoid overlapping requests.
3. Retrieve permitted internal sources and curated external snapshots on the backend.
4. Discard responses whose revision no longer matches.
5. Render untrusted excerpts as text, with numbered labels alongside colors.
6. Insert a citation only on the author's explicit action; leave peer/supervisor approval in the journal workflow.

Docusaurus is the reader/publication layer. It may render the resulting Markdown, but the public static bundle must not contain an internal source catalog or internal search index. Decap's Git authentication is not automatically backend authorization for this service.

## Local HTTP contract

The demo serves:

| Request | Result |
| --- | --- |
| `GET /api/config` | Local-session token, configured model, permitted-source count, synthetic draft |
| `POST /api/recommend` | Accepts exactly `{"draft": "text"}` and returns schema version 1 |
| `GET /api/sources/SOURCE_ID` | The permitted stored source; otherwise 404 |

POST requires JSON and `X-Reading-Token` from the same server process. The server rejects cross-origin requests and untrusted hosts, binds to loopback, sets no-store headers, and does not enable CORS. It allows one generation request at a time. This is a single-user demonstration, not a browser-to-server authentication protocol for internet deployment.

## Before online deployment

A production service needs authenticated users, group mapping, TLS, per-user/session request isolation, resource/rate limits, private catalog storage, a controlled local-model deployment and a retention policy. The browser must not be able to choose another user's audiences. Hosted draft text should go only to the explicitly configured backend/model. These requirements are not supplied by publishing this code repository.

Open-web discovery is not available in this release. If introduced, it should be an explicit mode with separate provenance and a policy for what draft context may leave the system. Curated sources do not imply permission to transmit internal drafts to those websites.
