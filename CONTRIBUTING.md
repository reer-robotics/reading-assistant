# Contributing

Start with a small change and a reproducible example. This repository is the reading/citation component; formatter and company-journal changes belong in their own repositories.

## Set up

1. Fork the public repository and clone your fork.
2. Create a branch such as `feature/citation-style` or `fix/stale-anchor`.
3. Use Python 3.11+ and create a virtual environment: `python3 -m venv .venv`.
4. Activate it and run `python -m pip install -e '.[dev]'`.
5. Start `readassist serve --port 4174`; the included source library is sufficient. No model is required.
6. Run `pytest -q` and, with Node 22+, `node --test tests/state.test.mjs`.

## Choose the kind of contribution

**Sources:** follow [the catalog contract](docs/sources.md). Use public or synthetic material in examples. Supply accurate title, provenance, locator and version. Include only excerpts you have rights to redistribute; link to the full original. Do not upload company content, employee information, credentials, or unpublished research to an issue or pull request.

**Retrieval:** add a small fixture showing the query, expected relevant source and irrelevant alternatives. Measure both missed useful evidence and false matches. Keep authorization filtering before ranking and model requests. A retrieval score is not a confidence score. Do not label lexical matches as verified support.

**Model skill:** update `skills/assess.json` and its version, explain the changed role/contract, and add mocked regression cases. Keep the model bounded to the supplied candidate IDs. It cannot browse, create sources, write the draft, or accept citations. Do not introduce a download, cloud fallback, or another model implicitly.

**Citation rendering:** add a style adapter and document missing-field handling. Preserve source IDs, original evidence and locators. Citation formatting and metadata must remain deterministic; do not ask a model to invent bibliographic details.

**Interface:** preserve the numbered labels alongside colors, keyboard actions, visible stale state and explicit insertion. Test edit-during-request, Unicode anchors, repeated paragraphs, no results and narrow layouts. Draft text is untrusted: render it as text, not executable HTML.

**Hosting or editor integration:** explain the authentication boundary first. The supplied Flask server deliberately binds to loopback and is not a deployment template. Keep internal catalog data and its retrieval index out of public Docusaurus bundles. Follow [integration guidance](docs/integration.md).

## Before opening a pull request

- Explain the user-visible problem, resulting behavior, and how you tested it.
- Run the Python tests, browser-state tests, and `python examples/run_demo.py`.
- For packaging changes, run `python -m pip wheel --no-deps . -w dist` and verify new resources are included.
- For interface changes, check the browser and include a screenshot using only synthetic/public examples.
- Update relevant contracts, docs and `CHANGELOG.md`. Bump a schema or skill version when its meaning changes.
- Keep generated artifacts, private catalogs, environment files and model files out of the commit. Review `git diff --cached`.

Submit the pull request against `main`. Maintainers should review correctness, provenance, access behavior and contributor usability. This public repository does not imply that branch approval rules are enforced; maintainers must configure those separately if desired.

## Evaluation with a real model

Use an explicitly installed local model and synthetic examples first. Record its tag/version, hardware, response time, unsupported claims, citation relevance and missed contradictions. Compare with lexical mode. Include model failures and ambiguous cases, not only successful demonstrations. A passing mocked test does not demonstrate semantic accuracy.
