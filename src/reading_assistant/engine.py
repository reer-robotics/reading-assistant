"""Deterministic retrieval, source-owned citations, and optional bounded AI review."""

import copy
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlparse

from jsonschema import validate

STOP = set(
    "a about all an and are as at be been by can could did do does for from has have how i if in into is it its may more not of on or our should than that the their them these they this to was we were what when which while will with would synthetic example each every".split()
)
COLORS = ["teal", "violet", "amber", "blue", "rose", "olive"]


def resource(name):
    return json.loads(files("reading_assistant").joinpath(name).read_text())


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def tokens(text):
    return [
        t
        for t in re.findall(r"[^\W_]+", text.casefold(), re.UNICODE)
        if len(t) > 2 and t not in STOP
    ]


def load_catalog(path=None):
    catalog = (
        json.loads(Path(path).read_text()) if path else resource("demo/catalog.json")
    )
    return validate_catalog(catalog)


def validate_catalog(catalog):
    validate(catalog, resource("schemas/catalog.schema.json"))
    ids = set()
    for source in catalog["sources"]:
        if source["id"] in ids:
            raise ValueError("Duplicate source ID")
        ids.add(source["id"])
        passage_ids = [p["id"] for p in source["passages"]]
        if len(passage_ids) != len(set(passage_ids)):
            raise ValueError("Duplicate passage ID")
        if source["url"]:
            url = urlparse(source["url"])
            if url.scheme != "https" or not url.netloc or url.username or url.password:
                raise ValueError("Source URLs must be HTTPS without credentials")
        if source["origin"] == "curated_external" and not source["url"]:
            raise ValueError("Curated external sources need an original HTTPS URL")
    return catalog


def permitted(source, audiences):
    return "public" in source["access"] or bool(set(source["access"]) & set(audiences))


def split_draft(text):
    if not isinstance(text, str) or len(text) > 30_000:
        raise ValueError("Draft must be text of at most 30,000 characters")
    paragraphs = []
    counts = Counter()
    for match in re.finditer(r"\S[\s\S]*?(?=\n\s*\n|\Z)", text):
        passage = match.group().rstrip()
        if not passage:
            continue
        key = digest(passage)[:12]
        counts[key] += 1
        index = len(paragraphs)
        paragraphs.append(
            {
                "id": f"p-{key}-{counts[key]}",
                "label": f"P{index + 1}",
                "color": COLORS[index % len(COLORS)],
                "text": passage,
                "start": match.start(),
                "end": match.start() + len(passage),
            }
        )
    if len(paragraphs) > 24:
        raise ValueError("Use up to 24 paragraphs; analyze a smaller section")
    return paragraphs


def citation(source, passage):
    # Bibliographic fields always come from the catalog, never from the model.
    key = f"{source['id']}:{passage['id']}"
    authors = "; ".join(source["authors"]) or "Author not supplied"
    date = source["issued"] or "n.d."
    text = f"{authors} ({date}). {source['title']}. {passage['locator']}. Version {source['version']}."
    if source["url"]:
        text += " " + source["url"]
    else:
        text += f" Internal source {source['id']}."
    if source["synthetic"]:
        text += " Synthetic demonstration; not company evidence."
    text = " ".join(text.split())
    markdown_text = re.sub(r"([\\`*_{}\[\]<>#!|])", r"\\\1", text)
    return {
        "key": key,
        "marker": f"[^{key}]",
        "text": text,
        "markdown": f"[^{key}]: {markdown_text}",
        "style": "source-note-v1",
        "missing_fields": [k for k in ["authors", "issued"] if not source[k]],
    }


class Recommender:
    def __init__(self, catalog=None, audiences=("demo",), model=None):
        self.catalog = copy.deepcopy(catalog) if catalog is not None else load_catalog()
        validate_catalog(self.catalog)
        self.audiences = tuple(audiences)
        self.model = model

    def sources(self):
        return [s for s in self.catalog["sources"] if permitted(s, self.audiences)]

    def recommend(self, text):
        paragraphs = split_draft(text)
        records = [(s, p) for s in self.sources() for p in s["passages"]]
        bags = [
            Counter(tokens(" ".join([s["title"], " ".join(s["tags"]), p["text"]])))
            for s, p in records
        ]
        average = sum(sum(b.values()) for b in bags) / max(len(bags), 1)
        frequency = Counter(t for bag in bags for t in bag)
        cards = []
        for paragraph in paragraphs:
            # Inserted footnotes should not amplify future retrieval.
            query = set(tokens(re.sub(r"\[\^[^\]]+\]", "", paragraph["text"])))
            candidates = []
            for (source, passage), bag in zip(records, bags):
                overlap = sorted(query & bag.keys())
                if len(overlap) < 2:
                    continue
                length = sum(bag.values())
                score = sum(
                    math.log(
                        1 + (len(bags) - frequency[t] + 0.5) / (frequency[t] + 0.5)
                    )
                    * (
                        bag[t]
                        * 2.2
                        / (bag[t] + 1.2 * (0.25 + 0.75 * length / max(average, 1)))
                    )
                    for t in overlap
                )
                candidates.append((source, passage, overlap, score))
            # Relevant internal evidence comes first, then the curated collection.
            candidates.sort(
                key=lambda c: (
                    c[0]["origin"] != "internal",
                    -c[3],
                    c[0]["id"],
                    c[1]["id"],
                )
            )
            seen = set()
            selected = []
            for candidate in candidates:
                if candidate[0]["id"] not in seen:
                    selected.append(candidate)
                    seen.add(candidate[0]["id"])
                if len(selected) == 4:
                    break
            for source, passage, overlap, score in selected:
                key = f"{paragraph['id']}:{source['id']}:{passage['id']}"
                cards.append(
                    {
                        "id": key,
                        "passage_id": paragraph["id"],
                        "label": paragraph["label"],
                        "color": paragraph["color"],
                        "rank": 0,
                        "kind": "suggested_reading",
                        "reason": "Shared terms: "
                        + ", ".join(overlap[:8])
                        + ". Read the excerpt to assess whether it supports your claim.",
                        "caveat": "Lexical match only; support or contradiction has not been assessed.",
                        "score": round(score, 4),
                        "assessment": "lexical",
                        "source": {
                            k: source[k]
                            for k in [
                                "id",
                                "title",
                                "origin",
                                "authors",
                                "issued",
                                "version",
                                "maturity",
                                "url",
                                "synthetic",
                            ]
                        },
                        "evidence": {
                            "id": passage["id"],
                            "locator": passage["locator"],
                            "text": passage["text"],
                            "sha256": digest(passage["text"]),
                        },
                        "citation": citation(source, passage),
                    }
                )
        workflow = resource("workflow.json")
        trace = ["capture", "retrieve", "rank"]
        if self.model and cards:
            from .model import assess

            assessments = assess(self.model, paragraphs, cards)
            order = {item["id"]: i for i, item in enumerate(assessments)}
            by_id = {item["id"]: item for item in assessments}
            for card in cards:
                item = by_id[card["id"]]
                card.update({k: item[k] for k in ["kind", "reason", "caveat"]})
                card["assessment"] = "model_suggestion"
            p_order = {p["id"]: i for i, p in enumerate(paragraphs)}
            cards.sort(
                key=lambda c: (
                    p_order[c["passage_id"]],
                    c["source"]["origin"] != "internal",
                    order[c["id"]],
                )
            )
            trace.append("assess")
        else:
            trace.append("assess_skipped")
        ranks = Counter()
        for card in cards:
            ranks[card["passage_id"]] += 1
            card["rank"] = ranks[card["passage_id"]]
        result = {
            "schema_version": 1,
            "draft_sha256": digest(text),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "ollama" if self.model and cards else "lexical",
            "paragraphs": paragraphs,
            "recommendations": cards,
            "workflow": {
                "id": workflow["id"],
                "version": workflow["version"],
                "steps": trace + ["validate", "display"],
                "model": self.model,
                "catalog_sha256": digest(json.dumps(self.sources(), sort_keys=True)),
                "skill_version": resource("skills/assess.json")["version"],
            },
            "notice": "Recommendations are reading aids, not verified endorsements. No open-web discovery.",
        }
        validate(result, resource("schemas/recommendations.schema.json"))
        return result
