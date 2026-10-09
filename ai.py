"""Claude's two jobs: read a free-text story into questionnaire answers, and explain the result.

Neither job decides a level of concern; rules.py does that.
"""
import json

import anthropic

from questionnaire import FIELDS, coerce
from rules import TIERS

MODEL = "claude-opus-5-5"
# Server-side fallback: if a safety classifier declines (possible with medical text), the API
# re-runs the request on Anthropic's recommended fallback model instead of returning a refusal.
FALLBACK = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
LANGUAGES = ["English", "Kannada", "Hindi", "Telugu", "Tamil", "Marathi", "Malayalam", "Bengali"]


class AIError(Exception):
    """A failure with a message fit to show the person using the app."""


def make_client(api_key):
    return anthropic.Anthropic(api_key=api_key) if api_key else None


def _field_list():
    lines = []
    for fid, f in FIELDS.items():
        if f["type"] == "check":
            lines.append(f'- {fid}: "true" only if clearly stated. ({f["label"]})')
        elif f["type"] == "number":
            lines.append(f'- {fid}: a number {f["min"]}-{f["max"]}. ({f["label"]})')
        else:
            opts = ", ".join(f'"{o[0]}"' for o in f["opts"] if o[0])
            lines.append(f'- {fid}: one of {opts}. ({f["label"]})')
    return "\n".join(lines)


STORY_SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {"type": "array", "items": {
            "type": "object",
            "properties": {"id": {"type": "string", "enum": list(FIELDS)}, "value": {"type": "string"}},
            "required": ["id", "value"], "additionalProperties": False}},
        "follow_up_questions": {"type": "array", "items": {"type": "string"}},
        "language": {"type": "string"},
    },
    "required": ["answers", "follow_up_questions", "language"],
    "additionalProperties": False,
}


def friendly(e):
    """Map an SDK error to a message for the person using the app (most specific first)."""
    if isinstance(e, anthropic.AuthenticationError):
        return "The Anthropic API key is not valid. Check ANTHROPIC_API_KEY in the app's secrets."
    if isinstance(e, anthropic.RateLimitError):
        return "Too many requests just now. Wait a minute and try again."
    if isinstance(e, anthropic.APIStatusError):
        return f"Claude could not answer (error {e.status_code}). Try again in a moment."
    if isinstance(e, anthropic.APIConnectionError):
        return "Could not reach Claude. Check the internet connection."
    return "Claude could not answer just now. Try again in a moment."


def _call(fn):
    try:
        return fn()
    except anthropic.APIError as e:
        raise AIError(friendly(e)) from e


def read_story(client, text):
    """Returns (answers dict, follow-up questions, detected language). Only facts the person stated."""
    prompt = f"""You are the intake step of a cancer early-detection checklist used by ordinary people in India.
Read the person's description below. It may be in English, Kannada, Hindi or a mix, and may use local words (gutka, khaini, beedi, paan, supari, mawa).
Extract only facts the person clearly states. Do not guess and do not infer a diagnosis. Leave out anything not mentioned.
Give every value as a string. Add up to 3 short follow-up questions, in the person's own language, about important things they did not mention (for example age, sex, tobacco use, or for women their last cervical test).

Allowed answer ids and values:
{_field_list()}

Description:
\"\"\"
{text[:4000]}
\"\"\""""
    resp = _call(lambda: client.beta.messages.create(
        model=MODEL, max_tokens=4000, **FALLBACK,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": STORY_SCHEMA}},
        messages=[{"role": "user", "content": prompt}]))
    if resp.stop_reason == "refusal":
        raise AIError("Claude declined to read this text. Try rephrasing it.")
    raw = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise AIError("Claude's answer could not be read. Press the button again.")
    answers = {}
    for item in data.get("answers", []):
        f = FIELDS.get(item.get("id"))
        val = coerce(f, item.get("value")) if f else None
        if val is not None:
            answers[item["id"]] = val
    return answers, [str(q) for q in data.get("follow_up_questions", [])][:3], str(data.get("language", ""))


def explain(client, result, d, language):
    """Yields the explanation text as it streams. Claude gets only the engine's output, not the story."""
    summary = {
        "overall_level": TIERS[result["overall"]]["label"],
        "age": d.get("age"), "sex": d.get("sex"),
        "areas": [{"area": m.name, "level": TIERS[m.tier]["label"], "warning_signs": m.flags,
                   "risk_factors": [t for t, _ in m.factors], "actions": m.actions}
                  for m in result["mods"] if m.tier >= 1],
    }
    prompt = f"""You are explaining the result of a cancer early-detection checklist to an ordinary person in India.
A fixed rules engine (not you) has already decided every level of concern. Your only job is to explain it kindly and clearly in {language}, written in {language} script.

Rules:
- Simple everyday words, as you would speak to someone with school-level education. Second person ("you").
- Start with the overall level exactly as given, translated.
- Never change, raise or lower any level. Never give a percentage. Never say they have or do not have cancer.
- Give the 2 or 3 most important next steps from the actions, including where to go. Government health centres (Ayushman Arogya Mandir, PHC) screen for free.
- If there is a warning sign, say calmly that most such signs are not cancer but must be checked soon.
- Keep the Quitline number exactly if it appears.
- 120 to 180 words. Short paragraphs. No headings, no bullet symbols, no markdown.
- End with one sentence saying this is not a diagnosis and only a doctor's examination can tell.

Result:
{json.dumps(summary, ensure_ascii=False)}"""

    try:
        with client.beta.messages.stream(
            model=MODEL, max_tokens=4000, **FALLBACK,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            yield from stream.text_stream
            if stream.get_final_message().stop_reason == "refusal":
                yield "\n\n(Claude stopped this explanation. The result and advice above still apply.)"
    except anthropic.APIError as e:
        yield f"\n\n{friendly(e)}"
