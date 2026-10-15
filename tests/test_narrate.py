"""The AI may reword, but it may never invent numbers."""

from tally import narrate


def test_numbers_ok_accepts_facts():
    allowed = narrate.allowed_numbers("Revenue grew 36% to $4,461 (from $2.1K)")
    assert narrate.numbers_ok("Sales rose about 36% to $4,461.", allowed)
    assert narrate.numbers_ok("It went from $2.1K up.", allowed)
    assert narrate.numbers_ok("The top 3 stores did best.", allowed)  # small counts are fine


def test_numbers_ok_rejects_invented_numbers():
    allowed = narrate.allowed_numbers("Revenue grew 36%")
    assert not narrate.numbers_ok("Revenue grew 42%.", allowed)
    assert not narrate.numbers_ok("That's about $9,000 extra.", allowed)
    assert not narrate.numbers_ok("Since 2019 it has grown.", allowed)


def test_tidy_removes_em_dashes():
    assert "\u2014" not in narrate.tidy("Sales rose \u2014 a lot")


class FakeClient:
    def __init__(self, reply):
        self.reply = reply

    def chat(self, *a, **k):
        return {"content": self.reply}


def base_insight():
    return {"kind": "trend", "title": "Sales are rising", "headline": "Sales grew 36% from Jan to Dec.",
            "explanation": "It went up steadily.", "ideas": ["Do more of it."], "facts": {"percent_change": "36%"}}


def test_rewrite_keeps_good_ai_text():
    c = FakeClient('{"title":"Sales keep climbing","headline":"Sales grew about 36% over the year.",'
                   '"explanation":"Month after month it went up.","ideas":["You could plan for more demand."]}')
    out = narrate.rewrite_insight(c, "m", base_insight(), "")
    assert out["title"] == "Sales keep climbing"
    assert out["ai_written"] is True


def test_rewrite_falls_back_when_ai_invents_numbers():
    c = FakeClient('{"title":"Sales up","headline":"Sales grew 58% this year.",'
                   '"explanation":"Fine.","ideas":["Hire 40 more people."]}')
    out = narrate.rewrite_insight(c, "m", base_insight(), "")
    assert out["headline"] == "Sales grew 36% from Jan to Dec."  # template kept
    assert out["ideas"] == ["Do more of it."]


def test_rewrite_survives_garbage():
    out = narrate.rewrite_insight(FakeClient("not json at all"), "m", base_insight(), "")
    assert out["headline"] == base_insight()["headline"]


def chapter():
    ins = base_insight()
    ins["explanation"] = "The blue line goes up. Sales grew each month."
    ins["chart"] = {"type": "line", "x": ["Jan", "Dec"], "key": [{"swatch": "line", "text": "Blue line: sales each month"}]}
    return ins


def test_review_keeps_clear_chapters():
    out = narrate.review_insight(FakeClient('{"clear": true, "problems": []}'), "m", chapter(), "")
    assert out["headline"] == chapter()["headline"]
    assert out["review"] == {"checked": True, "clear": True, "fixed": False, "problems": []}


def test_review_rewrites_unclear_chapters():
    c = FakeClient('{"clear": false, "problems": ["Too vague"], "title": "Sales went up all year",'
                   '"headline": "Sales grew about 36% from Jan to Dec.",'
                   '"explanation": "Follow the blue line: it climbs. That means more money each month."}')
    out = narrate.review_insight(c, "m", chapter(), "")
    assert out["title"] == "Sales went up all year"
    assert out["review"]["fixed"] is True and out["review"]["problems"] == ["Too vague"]


def test_review_cannot_sneak_in_new_numbers():
    c = FakeClient('{"clear": false, "problems": ["x"], "headline": "Sales grew 80% in Dec."}')
    out = narrate.review_insight(c, "m", chapter(), "")
    assert out["headline"] == chapter()["headline"]
    assert out["review"]["fixed"] is False


def test_readability_flags_catch_jargon_and_missing_chart_pointer():
    ins = base_insight()
    ins["explanation"] = "The correlation coefficient is positive."
    flags = narrate.readability_flags(ins)
    assert any("correlation" in f for f in flags)
    assert any("doesn't tell the reader what to look at" in f for f in flags)


def test_writer_rules_come_from_the_storytelling_guide():
    rules = narrate.writer_rules()
    assert rules != narrate.FALLBACK_RULES, "the guide's rules block should be found and loaded"
    assert "5 seconds" in rules and "Interpret, don't just name columns" in rules
    assert rules in narrate.style()
    assert "—" not in rules
