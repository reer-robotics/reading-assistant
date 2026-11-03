"""Exercise public/synthetic examples without a model or network access."""

from importlib.resources import files
from pathlib import Path

from reading_assistant.engine import Recommender

root = Path(__file__).parent
engine = Recommender()
for name, text in [
    (
        "pickup and governance",
        files("reading_assistant").joinpath("demo/draft.md").read_text(),
    ),
    ("method", (root / "method.md").read_text()),
    ("no match", (root / "no-match.md").read_text()),
]:
    result = engine.recommend(text)
    print(
        f"{name}: {len(result['paragraphs'])} paragraphs, {len(result['recommendations'])} recommendations"
    )
    if name == "no match":
        assert not result["recommendations"]
    else:
        assert result["recommendations"]
        for card in result["recommendations"]:
            print(
                f"  {card['label']} -> {card['source']['id']} / {card['evidence']['id']}"
            )
