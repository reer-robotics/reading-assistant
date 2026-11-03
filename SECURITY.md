# Security and privacy

Version 0.1 is a single-user, loopback-only demonstration. Do not expose the Flask development server publicly or place it behind a reverse proxy and assume it has company authentication.

- Drafts are held in browser memory and sent to the local Python process only on request or an enabled timer. The service does not save them. Downloading creates a file at the user's chosen browser download location.
- Optional model processing uses only `http://127.0.0.1:11434`, rejects remote model metadata, and disables redirects/proxy inheritance. Ollama itself is an independently administered local service; its logging and model configuration are the operator's responsibility.
- Source catalogs are loaded by the process operator. Audience filtering occurs before retrieval, model requests, and source display. A local audience label is not authenticated identity.
- HTTP requests cannot select a catalog path, model, endpoint, or audience. The server rejects untrusted Host headers, non-loopback clients and unauthenticated/cross-origin POSTs. No CORS is enabled. The request token is not SSO.
- Source content and model output are untrusted. The browser creates text nodes rather than rendering supplied HTML; source URLs must be HTTPS. The server applies a restrictive content-security policy. Do not open unfamiliar source links merely because the model recommends them.
- Model responses cannot replace evidence, citations or source identities. Structured validation does not establish factual accuracy or eliminate prompt injection. Review the actual source.
- Do not commit private drafts, source catalogs, credentials, or model files. Store real catalogs outside this public repository. `private-data/` is ignored as an additional convenience, not a substitute for reviewing commits.

Report a vulnerability privately using the repository's Security advisories option if enabled; otherwise contact a repository maintainer privately before sharing exploit details. Do not attach secrets or real internal documents to public issues.
