"""Shared fixture builder, so the suite states this shape once."""
from tpsermons.models import CheatRow, Guide, Icebreaker, Section


def sections(n=3, per=4):
    out = []
    for i in range(n):
        qs = ["Have you ever noticed this in section %d, question %d?" % (i, j)
              for j in range(per)]
        out.append(Section(
            title="Section %d" % i,
            setup="A setup paragraph grounding the section in the passage. "
                  "It runs a few sentences and borrows one phrase from the message.",
            questions=qs,
            reflection_questions=[q.replace("you", "I") for q in qs]))
    return out


def make_guide(**kw):
    base = dict(
        title="Presence Over Position", series="The Urgent Kingdom",
        speaker="Aaron Brockett", date="2026-08-30", passage="Mark 9:30-50",
        links={"tpcc": "https://tpcc.org/messages/presence-over-position",
               "youtube": "https://youtu.be/-F6w9h2Jpg8"},
        goal="Move the room from knowing about servanthood to naming one place "
             "it is missing this week.",
        leader_notes=[
            "The sermon runs on a single contrast between position and presence.",
            "Divorce and fatherhood come up briefly. Someone here has lived it.",
            "Keep your own talking under a quarter of the night.",
        ],
        scripture_instructions="Read Mark 9:33-37 aloud, then Mark 9:42-48.",
        icebreakers=[
            Icebreaker("A", "What is a title you once wanted badly?", "A newer group"),
            Icebreaker("B", "Think about a time you were overlooked.", "Storytellers"),
            Icebreaker("C", "Where are you quietly keeping score?", "A high-trust group"),
        ],
        sections=sections(),
        closing_go_around="Go around the circle. Each man names one specific step.",
        prayer="Close by praying for the man on your left, out loud, by name.",
        cheat_sheet=[
            CheatRow("Silence after a question", "Count to ten before you fill it."),
            CheatRow("One man dominating", "Thank him, then ask who else has one."),
            CheatRow("Surface answers", "Ask for the specific week it happened."),
            CheatRow("A tangent", "Name it, park it, offer to pick it up after."),
            CheatRow("Someone gets emotional", "Stop the clock. Do not rush past it."),
        ],
        key_themes=["Position is borrowed, presence is chosen.",
                    "Greatness runs downward.",
                    "Serving without an audience is the test.",
                    "Sin gets dealt with seriously, not managed.",
                    "Peace costs something."],
        commitment_prompt="Name one specific step for this week, and the man who "
                          "will ask you about it.",
        source="whisper",
    )
    base.update(kw)
    return Guide(**base)
