"""The most important promise Tally makes: it finds real patterns and ignores noise."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tally import analysis, insights, loader
from tally.profile import classify

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "samples" / "coffee_shop_sales.csv"
NO_AI = {"ollama_url": "http://127.0.0.1:9", "use_ai": False}


def run(path: Path, context: str = "") -> dict:
    return analysis.analyze(path, file_name=path.name, sheet=None, context=context, settings=NO_AI)


def kinds_and_cols(report):
    return [(i["kind"], tuple(i["columns"])) for i in report["insights"]]


def test_sample_finds_planted_patterns():
    r = run(SAMPLE)
    found = kinds_and_cols(r)
    assert ("trend", ("Date", "Revenue")) in found
    assert any(k == "rhythm" for k, _ in found), "weekend effect should be found"
    assert any(k == "group" and cols == ("Customer Type", "Rating") for k, cols in found)
    text = " ".join(i["headline"] + i["explanation"] for i in r["insights"])
    assert "Oct 2024" in text, "the October catering spike should be mentioned"


def test_sample_ignores_noise_columns():
    r = run(SAMPLE)
    for ins in r["insights"]:
        assert "Payment Method" not in ins["columns"]
        assert "Barista" not in ins["columns"]


def test_sample_detects_derived_column():
    r = run(SAMPLE)
    assert any("Quantity' times 'Unit Price'" in n for n in r["health"]["notes"])


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_pure_noise_produces_no_findings(tmp_path, seed):
    """Random data must not produce 'discoveries'. This is the anti-hallucination test."""
    rng = np.random.default_rng(seed)
    n = 600
    df = pd.DataFrame({
        "Date": pd.date_range("2023-01-01", periods=n, freq="D").strftime("%Y-%m-%d"),
        "Region": rng.choice(["North", "South", "East", "West"], n),
        "Channel": rng.choice(["Web", "Store", "Phone"], n),
        "Team": rng.choice(list("ABCDEF"), n),
        "Sales": rng.normal(100, 15, n).round(2),
        "Score": rng.normal(50, 10, n).round(1),
        "Visits": rng.poisson(20, n),
    })
    p = tmp_path / "noise.csv"
    df.to_csv(p, index=False)
    r = run(p)
    tested = [i for i in r["insights"] if i["stats"]["p"] is not None]
    assert len(tested) == 0, [i["headline"] for i in tested]


def test_clear_group_difference_is_found(tmp_path):
    rng = np.random.default_rng(0)
    n = 400
    region = rng.choice(["North", "South", "East"], n)
    sales = rng.normal(100, 10, n) + np.where(region == "North", 40, 0)
    p = tmp_path / "groups.csv"
    pd.DataFrame({"Region": region, "Sales": sales.round(2)}).to_csv(p, index=False)
    r = run(p)
    groups = [i for i in r["insights"] if i["kind"] == "group"]
    assert groups and groups[0]["chart"]["categories"][0] == "North"
    assert "North" in groups[0]["headline"]


def test_correlation_found_and_explained(tmp_path):
    rng = np.random.default_rng(3)
    n = 300
    ad = rng.uniform(0, 100, n)
    sales = 3 * ad + rng.normal(0, 40, n)
    p = tmp_path / "corr.csv"
    pd.DataFrame({"Ad spend": ad.round(2), "Sales": sales.round(2)}).to_csv(p, index=False)
    r = run(p)
    c = [i for i in r["insights"] if i["kind"] == "correlation"]
    assert c and "not that one causes the other" in c[0]["explanation"]


def test_bh_adjust_matches_reference():
    p = [0.01, 0.04, 0.03, 0.005]
    # reference values computed by hand (Benjamini-Hochberg)
    assert np.allclose(insights.bh_adjust(p), [0.02, 0.04, 0.04, 0.02])


def test_no_em_dashes_in_generated_text():
    r = run(SAMPLE)
    blob = str(r)
    assert "\u2014" not in blob


def test_profile_roles():
    loaded = loader.load(SAMPLE)
    prof = classify(loaded.df, loaded.units)
    roles = {c.name: c.role for c in prof.columns.values()}
    assert roles["Order ID"] == "id"
    assert roles["Date"] == "time"
    assert roles["Store"] == "category"
    assert roles["Revenue"] == "measure"
    assert prof.columns["Revenue"].additive is True
    assert prof.columns["Unit Price"].additive is False
    assert prof.main_metric == "Revenue"


def test_every_chart_has_a_color_key():
    r = run(SAMPLE)
    for ins in r["insights"]:
        key = ins["chart"].get("key")
        assert key, f"{ins['kind']} chart is missing its 'how to read this' key"
        assert all(k["text"] for k in key)


def test_row_noun_is_used():
    r = run(SAMPLE)
    assert r["dataset"]["row_noun"] == "order"
    assert any("order" in i["headline"] or "order" in i["explanation"] for i in r["insights"])


def test_history_keeps_snapshots_but_prunes_old_files(tmp_path, monkeypatch):
    from tally import history
    monkeypatch.setenv("TALLY_DATA_DIR", str(tmp_path))
    ids = []
    for i in range(history.KEEP_SOURCES + 3):
        src = tmp_path / f"up{i}.csv"
        src.write_text("a,b\n1,2\n")
        rid = f"20260101-0000{i:02d}-abcdef"
        history.save({"id": rid, "story": {"title": "t"}, "file_name": "f.csv", "created_at": f"2026-01-01T00:00:{i:02d}",
                      "dataset": {"rows": 1}, "insights": []}, src)
        assert not src.exists(), "the upload should be moved, not copied"
        ids.append(rid)
    listing = history.listing()
    assert len(listing) == len(ids), "every snapshot is kept"
    assert sum(r["has_source"] for r in listing) == history.KEEP_SOURCES
    assert history.has_source(ids[-1]) and not history.has_source(ids[0])
