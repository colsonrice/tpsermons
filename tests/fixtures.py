"""Shared fixture builders, so the suite states these shapes once."""
from tpsermons.models import CheatRow, Guide, Icebreaker, Question, Section

_SENTENCE = ("The sermon kept returning to one idea and pressed it from several angles "
             "so a leader can retell it plainly without notes. ")
SETUP = ("Verses one through eight set the scene and the preacher leaned on a single "
         "image to hold the section together. The men will recognise the tension quickly. "
         "Name the verse range, tell the image briefly, and move to the questions without "
         "turning it into a lecture or a recap of Sunday.")


def sections(n=3, per=4, edition="classic"):
    out = []
    for i in range(n):
        qs = [Question(ask="Have you ever noticed this in section %d, question %d?" % (i, j),
                       lead="The sermon made a point here.",
                       probe="Which week was that, specifically?" if edition == "new" else "",
                       star=(edition == "new" and j == 0))
              for j in range(per)]
        out.append(Section(
            title="Section %d" % i, setup=SETUP, questions=qs,
            reflection_questions=["Have I ever noticed this in section %d, question %d?"
                                  % (i, j) for j in range(per)],
            minutes="12-15" if edition == "classic" else "",
            say="Let's turn to the next part of the passage." if edition == "new" else ""))
    return out


def _common(**kw):
    base = dict(
        title="Presence Over Position", series="The Urgent Kingdom",
        speaker="Aaron Brockett", speaker_role="Lead Pastor",
        date="2026-08-30", passage="Mark 9:30-50",
        links={"tpcc": "https://tpcc.org/messages/presence-over-position",
               "youtube": "https://youtu.be/-F6w9h2Jpg8"},
        guide_title="Position or Presence",
        goal="Name one place you are working for position and one step to change it.",
        scripture_instructions="Have one man read verses 30-37 and another read 38-50.",
        icebreakers=[
            Icebreaker("A", "newer group, lower trust", "What did you most want to win as a kid?",
                       "Keep it light."),
            Icebreaker("B", "storytellers", "Think about a season harder than you wanted.",
                       "Gets formation onto the table through story."),
            Icebreaker("C", "high-trust group", "Where are you quietly keeping score?", ""),
        ],
        closing_go_around="Go around the room. Each man names one specific step.",
        prayer="Each man prays one sentence for the man who spoke before him.",
        cheat_sheet=[CheatRow("Silence after a hard question", "Count to ten, then go first."),
                     CheatRow("Tangents", "Park it and bring it back to his week."),
                     CheatRow("One voice dominating", "Hand the next question to a quiet man."),
                     CheatRow("Surface answers", "Ask for the true answer, not the right one."),
                     CheatRow("Emotional moment", "Stop the guide. Do not fix it.")],
        key_themes=["Formation over circumstances: God shapes the soul over time.",
                    "Position versus presence: you can stand near Jesus and miss Him.",
                    "Greatness relocated: serve the one who cannot pay you back.",
                    "Self-reliance: fear dressed as competence.",
                    "Sin managed: the lie is that you can handle it."],
        commitment_prompt="Name one step for this week and the man who will ask you about it.",
        source="whisper",
    )
    base.update(kw)
    return base


def make_guide(**kw):
    """A valid classic-edition guide."""
    base = _common(mode="classic", sections=sections(),
                   leader_notes=[_SENTENCE * 5, _SENTENCE * 4, _SENTENCE * 4, _SENTENCE * 3])
    base.update(kw)
    return Guide(**base)


def make_new_guide(**kw):
    """A valid new-edition guide."""
    base = _common(mode="new", sections=sections(edition="new"),
                   thesis="God cares more about forming your soul than fixing your week.",
                   outline=["Serve without an agenda", "Surrender being territorial",
                            "Stop tolerating sin", "Stay salty"],
                   sensitivities=["Someone here is in a hard season tonight. Do not rush him."],
                   read_refs=["Mark 9:33-37", "Mark 9:42-48"],
                   obstacle="What will realistically stop you before next Monday?",
                   carry="Next week we ask each other whether that step happened.")
    base.update(kw)
    return Guide(**base)
