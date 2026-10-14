"""Messy files should come out clean, with every fix written down."""

from pathlib import Path

import pandas as pd

from tally import loader


def write_xlsx(path: Path, rows: list[list]):
    pd.DataFrame(rows).to_excel(path, header=False, index=False)


def test_title_rows_and_total_row_are_handled(tmp_path):
    p = tmp_path / "messy.xlsx"
    write_xlsx(p, [
        ["Quarterly sales report", None, None],
        ["Prepared by finance", None, None],
        [None, None, None],
        ["Region", "Month", "Sales"],
        ["North", "Jan", "$1,200.50"],
        ["south", "Jan", "$950"],
        ["South", "Feb", "(100)"],
        ["Total", None, "$2,050.50"],
    ])
    out = loader.load(p)
    df = out.df
    assert list(df.columns) == ["Region", "Month", "Sales"]
    assert len(df) == 3, "the Total row must be dropped"
    assert df["Sales"].tolist() == [1200.5, 950.0, -100.0]
    assert out.units["Sales"] == {"kind": "currency", "symbol": "$"}
    assert set(df["Region"]) == {"North", "South"}, "case variants should merge"
    notes = " ".join(out.notes)
    assert "Total" in notes and "Skipped" in notes and "capital letters" in notes


def test_csv_with_semicolons_and_percent(tmp_path):
    p = tmp_path / "eu.csv"
    p.write_text("Team;Rate;When\nA;45%;03/04/2024\nB;12,5%;15/04/2024\nC;N/A;20/04/2024\n", encoding="utf-8")
    out = loader.load(p)
    df = out.df
    assert df["Rate"].iloc[0] == 45.0
    assert pd.isna(df["Rate"].iloc[2])
    assert pd.api.types.is_datetime64_any_dtype(df["When"])
    assert df["When"].iloc[1].day == 15, "day-first dates should be detected"


def test_csv_title_line_above_table(tmp_path):
    p = tmp_path / "titled.csv"
    p.write_text("My export\n\nName,Score\nAnn,3\nBob,5\n", encoding="utf-8")
    df = loader.load(p).df
    assert list(df.columns) == ["Name", "Score"]
    assert df["Score"].tolist() == [3.0, 5.0]


def test_multi_sheet_listing(tmp_path):
    p = tmp_path / "book.xlsx"
    with pd.ExcelWriter(p) as w:
        pd.DataFrame({"a": [1, 2]}).to_excel(w, sheet_name="Small", index=False)
        pd.DataFrame({"a": range(50), "b": range(50)}).to_excel(w, sheet_name="Big", index=False)
    sheets = loader.list_sheets(p)
    assert {s["name"] for s in sheets} == {"Small", "Big"}
    assert loader.best_sheet(sheets) == "Big"


def test_unsupported_file(tmp_path):
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF")
    try:
        loader.load(p)
    except loader.LoadError as e:
        assert "CSV or Excel" in str(e)
    else:
        raise AssertionError("expected LoadError")
