"""Claude's two jobs: read a free-text story into questionnaire answers, and explain the result.

Neither job decides a level of concern; rules.py does that.

Claude is reached either through OpenRouter (OPENROUTER_API_KEY) or directly through the
Anthropic API (ANTHROPIC_API_KEY). Both backends expose the same two methods.
"""
import json

import anthropic
import openai

from questionnaire import FIELDS, coerce
from rules import TIERS

LANGUAGES = ["English", "Kannada", "Hindi", "Telugu", "Tamil", "Marathi", "Malayalam", "Bengali"]
OPENROUTER_DEFAULT_MODEL = "anthropic/claude-opus-5.5"


class AIError(Exception):
    """A failure with a message fit to show the person using the app."""


class OpenRouterBackend:
    def __init__(self, key, model=None):
        self.model = model or OPENROUTER_DEFAULT_MODEL
        self.label = f"OpenRouter · {self.model}"
        self.client = openai.OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1",
                                    default_headers={"X-Title": "Jagruti Cancer Check"})
        self.extra = {"reasoning": {"effort": "low"}}  # short, routine tasks: keep thinking light

    def json(self, prompt, schema):
        resp = self.client.chat.completions.create(
            model=self.model, max_tokens=4000, extra_body=self.extra,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_schema", "json_schema": {"name": "answers", "strict": True, "schema": schema}})
        choice = resp.choices[0]
        if choice.finish_reason == "content_filter":
            raise AIError("Claude declined to read this text. Try rephrasing it.")
        return choice.message.content or ""

    def stream(self, prompt):
        for chunk in self.client.chat.completions.create(
                model=self.model, max_tokens=4000, extra_body=self.extra, stream=True,
                messages=[{"role": "user", "content": prompt}]):
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicBackend:
    model = "claude-opus-5-5"
    label = f"Anthropic API · {model}"
    # Server-side fallback: if a safety classifier declines (possible with medical text), the API
    # re-runs the request on Anthropic's recommended fallback model instead of returning a refusal.
    fallback = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

    def __init__(self, key):
        self.client = anthropic.Anthropic(api_key=key)

    def json(self, prompt, schema):
        resp = self.client.beta.messages.create(
            model=self.model, max_tokens=4000, **self.fallback,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}])
        if resp.stop_reason == "refusal":
            raise AIError("Claude declined to read this text. Try rephrasing it.")
        return next((b.text for b in resp.content if b.type == "text"), "")

    def stream(self, prompt):
        with self.client.beta.messages.stream(
                model=self.model, max_tokens=4000, **self.fallback, output_config={"effort": "low"},
                messages=[{"role": "user", "content": prompt}]) as s:
            yield from s.text_stream
            if s.get_final_message().stop_reason == "refusal":
                yield "\n\n(Claude stopped this explanation. The result and advice above still apply.)"


def make_client(openrouter_key=None, openrouter_model=None, anthropic_key=None):
    """OpenRouter if its key is set, else the Anthropic API, else None (AI features off)."""
    if openrouter_key:
        return OpenRouterBackend(openrouter_key, openrouter_model)
    if anthropic_key:
        return AnthropicBackend(anthropic_key)
    return None


def friendly(e):
    """Map an SDK error (either library) to a message for the person using the app."""
    if isinstance(e, (anthropic.AuthenticationError, openai.AuthenticationError)):
        return "The API key is not valid. Check the key in the app's secrets."
    if isinstance(e, (anthropic.RateLimitError, openai.RateLimitError)):
        return "Too many requests just now. Wait a minute and try again."
    if isinstance(e, (anthropic.APIStatusError, openai.APIStatusError)):
        if e.status_code == 402:
            return "The OpenRouter account has run out of credits."
        return f"Claude could not answer (error {e.status_code}). Try again in a moment."
    if isinstance(e, (anthropic.APIConnectionError, openai.APIConnectionError)):
        return "Could not reach Claude. Check the internet connection."
    return "Claude could not answer just now. Try again in a moment."


API_ERRORS = (anthropic.APIError, openai.APIError)


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


def _parse_json(raw):
    """Strict parse, then the outermost {...} in case a provider wrapped the JSON in text."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
    raise AIError("Claude's answer could not be read. Press the button again.")


def read_story(client, text):
    """Returns (answers dict, follow-up questions, detected language). Only facts the person stated."""
    prompt = f"""You are the intake step of a cancer early-detection checklist used by ordinary people in India.
Read the person's description below. It may be in English, Kannada, Hindi or a mix, and may use local words (gutka, khaini, beedi, paan, supari, mawa).
Extract only facts the person clearly states. Do not guess and do not infer a diagnosis. Leave out anything not mentioned.
Give every value as a string. Add up to 3 short follow-up questions, in the person's own language, about important things they did not mention (for example age, sex, tobacco use, or for women their last cervical test).
Reply with only a JSON object with keys "answers" (a list of {{"id", "value"}}), "follow_up_questions" and "language".

Allowed answer ids and values:
{_field_list()}

Description:
\"\"\"
{text[:4000]}
\"\"\""""
    try:
        data = _parse_json(client.json(prompt, STORY_SCHEMA))
    except API_ERRORS as e:
        raise AIError(friendly(e)) from e
    answers = {}
    for item in data.get("answers", []):
        f = FIELDS.get(item.get("id")) if isinstance(item, dict) else None
        val = coerce(f, item.get("value")) if f else None
        if val is not None:
            answers[item["id"]] = val
    language = str(data.get("language", "")).strip().title()  # models vary: "kannada", "KANNADA"
    return answers, [str(q) for q in data.get("follow_up_questions", [])][:3], language


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
    wrote = False
    try:
        for piece in client.stream(prompt):
            wrote = True
            yield piece
    except API_ERRORS as e:
        yield f"\n\n{friendly(e)}"
        return
    if not wrote:
        yield "Claude returned an empty explanation. Press the button again. The result and advice above still apply."
