import json

from sales_data_audit import checks
from sales_data_audit.cli import load, main, render_markdown
from sales_data_audit.sample import PLANTED, make_sample


def rows_of(path):
    return load(path)


def by_check(findings, name):
    return [f for f in findings if f["check"] == name]


def test_sample_findings(tmp_path):
    path = tmp_path / "s.csv"
    make_sample(path)
    f = checks.run_all(rows_of(path))
    assert sum(len(x["rows"]) for x in by_check(f, "duplicate_key")) == PLANTED["duplicates"] * 2
    assert len(by_check(f, "non_positive")[0]["rows"]) == PLANTED["negative_units"]
    assert len(by_check(f, "price_outlier")) >= 1
    assert sum(len(x["rows"]) for x in by_check(f, "price_outlier")) == PLANTED["price_typo"]
    assert len(by_check(f, "missing_value")[0]["rows"]) == PLANTED["empty_product"]
    assert len(by_check(f, "bad_date")[0]["rows"]) == PLANTED["bad_date"]


def test_date_gap_in_s02(tmp_path):
    path = tmp_path / "s.csv"
    make_sample(path)
    gaps = by_check(checks.run_all(rows_of(path)), "date_gap")
    assert len(gaps) == 1
    assert "S02" in gaps[0]["message"] and f"{PLANTED['gap_days']} days" in gaps[0]["message"]


def test_near_duplicate_names(tmp_path):
    path = tmp_path / "s.csv"
    make_sample(path)
    dup = by_check(checks.run_all(rows_of(path)), "name_near_duplicate")
    assert any("P001" in d["message"] and "P006" in d["message"] for d in dup)


def test_clean_file_has_no_high_findings(tmp_path):
    path = tmp_path / "c.csv"
    path.write_text("date,store,sku,product,units,price\n"
                    "2026-01-01,S1,A,Tea,5,3.00\n2026-01-02,S1,A,Tea,6,3.00\n"
                    "2026-01-03,S1,A,Tea,4,3.00\n")
    f = checks.run_all(rows_of(path))
    assert [x for x in f if x["severity"] == "high"] == []


def test_missing_column_exits(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("date,store\n2026-01-01,S1\n")
    try:
        load(path)
    except SystemExit as e:
        assert "Missing columns" in str(e)
    else:
        raise AssertionError("expected SystemExit")


def test_cli_exit_code_and_json(tmp_path, capsys):
    path = tmp_path / "s.csv"
    make_sample(path)
    assert main([str(path), "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert any(x["check"] == "duplicate_key" for x in data)


def test_markdown_has_score(tmp_path):
    path = tmp_path / "s.csv"
    make_sample(path)
    rows = rows_of(path)
    md = render_markdown(rows, checks.run_all(rows))
    assert "Quality score:" in md and "## High" in md


def test_sample_is_deterministic(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    make_sample(a)
    make_sample(b)
    assert a.read_bytes() == b.read_bytes()
