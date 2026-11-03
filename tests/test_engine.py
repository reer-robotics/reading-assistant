import copy
import json
from importlib.resources import files

import httpx
import pytest
from jsonschema import ValidationError

from reading_assistant.engine import (
    Recommender,
    citation,
    digest,
    load_catalog,
    resource,
    split_draft,
)
from reading_assistant.server import create_app

DRAFT = files("reading_assistant").joinpath("demo/draft.md").read_text()


def test_demo_links_and_exact_citations():
    result = Recommender().recommend(DRAFT)
    assert result["mode"] == "lexical"
    assert len(result["paragraphs"]) == 3
    paragraphs = {p["id"]: p for p in result["paragraphs"]}
    sources = {s["id"]: s for s in load_catalog()["sources"]}
    assert result["recommendations"]
    for card in result["recommendations"]:
        p = paragraphs[card["passage_id"]]
        assert (card["label"], card["color"]) == (p["label"], p["color"])
        original = next(
            x
            for x in sources[card["source"]["id"]]["passages"]
            if x["id"] == card["evidence"]["id"]
        )
        assert card["evidence"]["text"] == original["text"]
        assert card["evidence"]["sha256"] == digest(original["text"])
        assert card["kind"] == "suggested_reading"
    first = [c for c in result["recommendations"] if c["label"] == "P1"]
    assert first[0]["source"]["origin"] == "internal"
    assert any(c["source"]["origin"] == "curated_external" for c in first)


def test_acl_filters_before_scoring_and_response():
    catalog = load_catalog()
    secret = copy.deepcopy(catalog["sources"][0])
    secret.update(
        id="RESTRICTED", title="Secret unreleased product", access=["executives"]
    )
    catalog["sources"].append(secret)
    result = Recommender(catalog, audiences=["demo"]).recommend(DRAFT)
    assert "RESTRICTED" not in json.dumps(result)
    assert "Secret unreleased" not in json.dumps(result)
    assert Recommender(catalog, audiences=[]).sources() == [
        s for s in catalog["sources"] if "public" in s["access"]
    ]


def test_no_match_and_empty_draft():
    assert (
        Recommender().recommend("Molecular gastronomy and sourdough fermentation.")[
            "recommendations"
        ]
        == []
    )
    assert Recommender().recommend("")["paragraphs"] == []


def test_unicode_offsets_and_duplicate_paragraph_ids():
    text = "🚀 Pickup uncertainty.\n\n🚀 Pickup uncertainty."
    paragraphs = split_draft(text)
    assert paragraphs[0]["id"] != paragraphs[1]["id"]
    for p in paragraphs:
        assert text[p["start"] : p["end"]] == p["text"]
    assert len(split_draft("a\r\n\r\nb")) == 2


@pytest.mark.parametrize("text", ["x" * 30_001, "\n\n".join(["paragraph"] * 25), None])
def test_draft_limits(text):
    with pytest.raises(ValueError):
        Recommender().recommend(text)


def test_missing_metadata_is_explicit():
    source = load_catalog()["sources"][-1]
    source["authors"] = []
    result = citation(source, source["passages"][0])
    assert result["missing_fields"] == ["authors", "issued"]
    assert "n.d." in result["text"] and "Author not supplied" in result["text"]


def test_lexical_mode_never_calls_model(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected network access")

    monkeypatch.setattr(httpx.Client, "post", forbidden)
    Recommender().recommend(DRAFT)


def test_ai_cannot_replace_evidence_and_respects_priority(monkeypatch):
    captured = []

    def mock_assess(model, paragraphs, cards):
        captured.extend(cards)
        return [
            {
                "id": c["id"],
                "kind": "possible_conflict",
                "reason": "The excerpt qualifies this claim.",
                "caveat": "Human review required.",
            }
            for c in reversed(cards)
        ]

    monkeypatch.setattr("reading_assistant.model.assess", mock_assess)
    result = Recommender(model="test-local").recommend(DRAFT)
    assert result["mode"] == "ollama"
    assert captured
    first = [c for c in result["recommendations"] if c["label"] == "P1"]
    assert first[0]["source"]["origin"] == "internal"
    assert all(c["kind"] == "possible_conflict" for c in result["recommendations"])
    for card in result["recommendations"]:
        assert (
            card["evidence"]["text"]
            == next(c for c in captured if c["id"] == card["id"])["evidence"]["text"]
        )


def mock_transport(monkeypatch, transform=None, metadata=None):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path == "/api/show":
            return httpx.Response(
                200, json=metadata or {"capabilities": ["completion"]}
            )
        body = json.loads(request.content)
        prompt = json.loads(body["messages"][-1]["content"])
        items = [
            {
                "id": c["id"],
                "kind": "possible_citation",
                "reason": "Relevant evidence.",
                "caveat": "Check the full source.",
            }
            for c in prompt["candidates"]
        ]
        if transform:
            items = transform(items)
        return httpx.Response(
            200, json={"message": {"content": json.dumps({"items": items})}}
        )

    original = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: original(transport=httpx.MockTransport(handler), **kw),
    )
    return calls


def test_local_model_contract(monkeypatch):
    calls = mock_transport(monkeypatch)
    result = Recommender(model="installed-local").recommend(DRAFT)
    assert len(calls) == 2
    assert all(str(c.url).startswith("http://127.0.0.1:11434/") for c in calls)
    assert result["recommendations"][0]["kind"] == "possible_citation"


@pytest.mark.parametrize(
    "transform",
    [
        lambda items: [{**items[0], "id": "invented"}] + items[1:],
        lambda items: [items[0]] * len(items),
    ],
)
def test_model_rejects_invented_and_duplicate_ids(monkeypatch, transform):
    mock_transport(monkeypatch, transform=transform)
    with pytest.raises((ValueError, ValidationError)):
        Recommender(model="installed-local").recommend(DRAFT)


def test_model_rejects_remote_execution(monkeypatch):
    calls = mock_transport(
        monkeypatch,
        metadata={"capabilities": ["completion"], "remote_host": "cloud.example"},
    )
    with pytest.raises(ValueError, match="cloud"):
        Recommender(model="remote").recommend(DRAFT)
    assert len(calls) == 1


def test_restricted_source_never_reaches_model(monkeypatch):
    catalog = load_catalog()
    catalog["sources"][0]["access"] = ["private"]

    def inspect(model, paragraphs, cards):
        assert "DEMO-PICKUP" not in json.dumps(cards)
        return [
            {
                "id": c["id"],
                "kind": "suggested_reading",
                "reason": "Relevant.",
                "caveat": "Review.",
            }
            for c in cards
        ]

    monkeypatch.setattr("reading_assistant.model.assess", inspect)
    Recommender(catalog, audiences=["demo"], model="test").recommend(DRAFT)


def test_catalog_rejects_unsafe_urls_and_duplicates(tmp_path):
    catalog = load_catalog()
    path = tmp_path / "catalog.json"
    catalog["sources"][0]["url"] = "javascript:alert(1)"
    path.write_text(json.dumps(catalog))
    with pytest.raises(ValueError):
        load_catalog(path)
    catalog = load_catalog()
    catalog["sources"].append(catalog["sources"][0])
    path.write_text(json.dumps(catalog))
    with pytest.raises(ValueError):
        load_catalog(path)


def test_server_requires_token_and_trusted_host():
    app = create_app()
    client = app.test_client()
    assert client.get("/", headers={"Host": "attacker.example"}).status_code == 400
    assert client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.1"}).status_code == 403
    assert client.post("/api/recommend", json={"draft": DRAFT}).status_code == 403
    token = client.get("/api/config").json["token"]
    headers = {"X-Reading-Token": token}
    assert (
        client.post(
            "/api/recommend", json={"draft": DRAFT}, headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/recommend",
            json={"draft": DRAFT},
            headers={**headers, "Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/recommend",
            json={"draft": DRAFT, "audience": "admin"},
            headers=headers,
        ).status_code
        == 400
    )
    assert client.get("/").headers["Cache-Control"] == "no-store"


def test_source_endpoint_applies_same_access_filter():
    client = create_app(audiences=[]).test_client()
    assert client.get("/api/sources/DEMO-PICKUP").status_code == 404
    assert client.get("/api/sources/NIST-SCATTER").status_code == 200


def test_browser_assets_served():
    client = create_app().test_client()
    for url in ["/", "/app.js", "/state.js", "/style.css"]:
        assert client.get(url).status_code == 200


def test_source_html_is_not_server_rendered():
    client = create_app().test_client()
    assert "innerHTML" not in client.get("/app.js").text


def test_citation_keys_are_unambiguous_and_markdown_is_escaped():
    source = load_catalog()["sources"][0]
    passage = source["passages"][0]
    source.update(id="A-B", title="<script>{attack}</script>\n[^injected]: evil")
    passage["id"] = "C"
    first = citation(source, passage)
    source["id"], passage["id"] = "A", "B-C"
    second = citation(source, passage)
    assert first["key"] != second["key"]
    assert "<script>" not in first["markdown"]
    assert "\n" not in first["markdown"]
    assert r"\{" in first["markdown"]


def test_library_validates_source_urls_too():
    catalog = load_catalog()
    catalog["sources"][0]["url"] = "javascript:alert(1)"
    with pytest.raises(ValueError):
        Recommender(catalog)
