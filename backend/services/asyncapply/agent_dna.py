"""Agent DNA: a small set of predefined vibe questions plus free-text notes,
composed into the writing-style instructions injected into every generated
cover letter and outreach message.

Structured, not free-form markdown: a user picks from a fixed taxonomy
(rhythm, tone, formality, certainty, punctuation, opening style) rather than
writing prose rules by hand. Each option maps to one fixed instruction line,
so the final prompt text is always coherent even if a user never touches the
form -- every question falls back to its first option as the default.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Option:
    """One answer to one question."""

    value: str
    label: str
    instruction: str


@dataclass(frozen=True)
class Question:
    """One vibe question, with its answer options in default-first order."""

    key: str
    label: str
    options: list[Option]


QUESTIONS: list[Question] = [
    Question(
        key="rhythm",
        label="Sentence rhythm",
        options=[
            Option("punchy", "Short and punchy", "Short paragraphs, 1-2 sentences. Vary sentence length -- short punchy lines mixed with longer ones."),
            Option("balanced", "Balanced", "Balanced paragraph length, 2-4 sentences. Natural variation, not mechanical."),
            Option("thorough", "Thorough", "Fuller paragraphs when the point needs room. Still no padding."),
        ],
    ),
    Question(
        key="tone",
        label="Tone",
        options=[
            Option("direct", "Direct and confident", "Direct and confident. Take a stance rather than hedge."),
            Option("warm", "Warm", "Warm and approachable, still professional."),
            Option("formal", "Formal", "Formal and polished throughout."),
            Option("playful", "A little playful", "Some personality and light humor where it fits naturally."),
        ],
    ),
    Question(
        key="formality",
        label="Formality",
        options=[
            Option("casual", "Casual", "Casual register: contractions (don't, can't, it's), direct address with 'I' and 'you'."),
            Option("professional", "Professional but human", "Professional but human -- not stiff, not casual."),
            Option("strict", "Strictly formal", "Strictly formal, no contractions."),
        ],
    ),
    Question(
        key="certainty",
        label="Certainty",
        options=[
            Option("commit", "Commit to claims", "Commit to claims plainly. Avoid hedge words like 'may,' 'could,' 'often considered' unless genuinely uncertain."),
            Option("hedge", "Hedge when unsure", "Hedge openly when uncertain ('I think,' 'probably') -- that honesty reads as real."),
        ],
    ),
    Question(
        key="punctuation",
        label="Punctuation",
        options=[
            Option("no_em_dash", "No em dashes", "No em dashes. Use periods, commas, or parentheses instead."),
            Option("any", "Whatever reads best", "Whatever punctuation reads best in context."),
        ],
    ),
    Question(
        key="opening",
        label="Opening style",
        options=[
            Option("straight_to_point", "Straight to the point", "Get to the point immediately. No warm-up sentence before the actual content."),
            Option("brief_context", "A little context first", "A brief line of context is fine before the main point."),
        ],
    ),
]

_BY_KEY: dict[str, Question] = {q.key: q for q in QUESTIONS}


def render_agent_dna(choices: dict[str, str] | None, notes: str | None, admin_note: str | None) -> str:
    """Compose the final writing-style instructions from a user's choices.

    Every question resolves to something: an unrecognized or missing answer
    falls back to that question's first (default) option, so a user who never
    opens this form still gets a coherent, deliberate voice, not silence.

    Args:
        choices: Map of question key to chosen option value.
        notes: The user's own free-text "anything else" addition.
        admin_note: A fixed rule block the admin sets for every user, or None.

    Returns:
        Plain, prompt-ready text.
    """
    choices = choices or {}
    lines = []
    for question in QUESTIONS:
        chosen_value = choices.get(question.key)
        option = next((o for o in question.options if o.value == chosen_value), question.options[0])
        lines.append(f"- {option.instruction}")

    parts = ["\n".join(lines)]
    if notes and notes.strip():
        parts.append(f"## Notes\n{notes.strip()}")
    if admin_note and admin_note.strip():
        parts.append(f"## House rules (set by the workspace admin)\n{admin_note.strip()}")

    return "\n\n".join(parts)


def questions_payload() -> list[dict]:
    """The QUESTIONS taxonomy as plain dicts, for the API response.

    Returns:
        One dict per question: {key, label, options: [{value, label}]}.
        Instruction text is deliberately left out -- it's prompt content,
        not something the frontend needs to render or should be able to see
        as if it were editable copy.
    """
    return [
        {
            "key": q.key,
            "label": q.label,
            "options": [{"value": o.value, "label": o.label} for o in q.options],
        }
        for q in QUESTIONS
    ]
