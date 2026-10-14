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
