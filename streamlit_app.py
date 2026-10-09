"""Jagruti Cancer Check: a teaching prototype of a clinical AI agent for early cancer detection in India.

Perceive (Claude reads a story) -> Confirm (the person checks the form) ->
Reason (rules.py, no AI) -> Act (fixed advice; Claude explains it in the person's language).
"""
import hashlib
import json
import os

import streamlit as st

import ai
from questionnaire import CASES, DEFAULTS, FIELDS, SECTIONS
from rules import TIERS, assess, screening_due

st.set_page_config(page_title="Jagruti Cancer Check", page_icon="🩺", layout="wide")

TIER_STYLE = {  # (text, background) per level of concern
    0: ("#1f6b42", "#e3f3e9"), 1: ("#1d5fa8", "#e3edf9"), 2: ("#9a4705", "#fcefdc"),
    3: ("#b42318", "#fde7e4"), 4: ("#ffffff", "#8f1a12"),
}
ss = st.session_state
K = lambda fid: f"f_{fid}"


def api_key():
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:  # no secrets file at all
        key = None
    return key or os.environ.get("ANTHROPIC_API_KEY")


client = ai.make_client(api_key())
for name, default in {"ai_filled": set(), "followups": [], "perceive": None, "explain": None,
                      "active_case": None, "story_status": None}.items():
    ss.setdefault(name, default)


def current(fid):
    return ss.get(K(fid), DEFAULTS.get(fid))


def answers():
    """The answers the rules engine sees: only fields currently visible in the form."""
    snapshot = {fid: current(fid) for fid in FIELDS}
    return {fid: v for fid, v in snapshot.items() if FIELDS[fid]["visible"](snapshot) and v not in (None, "")}


def reset_form():
    for fid in FIELDS:
        ss.pop(K(fid), None)
    ss.ai_filled, ss.followups, ss.perceive, ss.explain, ss.story_status = set(), [], None, None, None


def load_case(case):
    reset_form()
    for fid, v in case["d"].items():
        ss[K(fid)] = v
    ss.active_case = case["key"]


def clear_all():
    reset_form()
    ss.active_case = None
    ss.story = ""


def mark_manual(fid):
    ss.ai_filled.discard(fid)
    ss.active_case = None


if "booted" not in ss:  # open on a realistic example, clearly marked as invented
    load_case(CASES[0])
    ss.booted = True

# ---------- Header ----------
st.title("Jagruti Cancer Check")
st.caption("Early-warning agent for adults in India · Teaching prototype, not a medical device")
st.write("Answer the questions, or describe your health in your own words in English, ಕನ್ನಡ or हिंदी. "
         "The agent checks your answers against Indian national screening rules and established cancer "
         "warning-sign guidelines, then tells you what to do next. It does not diagnose cancer.")

st.markdown("**Example cases** (invented, for teaching)")
case_cols = st.columns(len(CASES))
for col, case in zip(case_cols, CASES):
    if col.button(case["label"], key=f"case_{case['key']}", use_container_width=True,
                  type="primary" if ss.active_case == case["key"] else "secondary"):
        load_case(case)
if ss.active_case:
    st.info(f"Showing invented example case {ss.active_case}. Change any answer, or clear the form to try your own.")

def show_results(d):
    r = assess(d)
    fg, bg = TIER_STYLE[r["overall"]]
    top = [m for m in r["mods"] if m.tier == r["overall"]]
    why = ""
    if r["overall"] >= 3:
        why = "<br>".join(f"<b>{m.name}:</b> {'; '.join(m.flags)}" for m in top)
    elif r["overall"] == 2:
        why = ", ".join(f"<b>{m.name}</b>" for m in top)
    st.markdown(
        f"""<div style="background:{bg};color:{fg};border-radius:10px;padding:16px 18px;margin-bottom:8px">
        <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;font-weight:600">Overall result</div>
        <div style="font-size:28px;font-weight:800;line-height:1.15;margin:4px 0">{TIERS[r['overall']]['label']}</div>
        <div>{TIERS[r['overall']]['line']}</div>
        {f'<div style="margin-top:8px">{why}</div>' if why else ''}</div>""",
        unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("**How the agent decided**")
        steps = [
            ("Perceive", "Claude", ss.perceive or 'Questionnaire filled by hand. ("Read my story" lets Claude fill it from free text.)'),
            ("Confirm", "You", f"{len(ss.ai_filled)} answers filled by Claude are marked *from story* in the form, waiting for you to check them."
             if ss.ai_filled else "You can see and change every answer the decision uses."),
            ("Reason", "Code", f"Rules engine checked {len(r['mods'])} cancer areas and matched {r['fired']} rules. "
             "No AI is used in this step, so the same answers always give the same result."),
            ("Act", "Claude", (ss.explain or {}).get("trace") or "Advice is fixed protocol text. Claude can explain it in your language, but cannot change any level."),
        ]
        for i, (name, who, desc) in enumerate(steps, 1):
            st.markdown(f"**{i}. {name}** `{who}`  \n{desc}")

    for m in sorted(r["mods"], key=lambda m: (-m.tier, -(m.points / (m.max or 1)))):
        with st.expander(f"{m.name} — {TIERS[m.tier]['short']}", expanded=m.tier >= 2):
            if m.max:
                st.progress(min(1.0, m.points / m.max), text=m.score_label or f"{m.points} of {m.max} risk points")
            elif m.score_label:
                st.caption(m.score_label)
            if m.flags:
                st.markdown("**Warning signs**\n" + "\n".join(f"- :red[{f}]" for f in m.flags))
            if m.factors:
                st.markdown("**Risk factors found**  \n" + " · ".join(
                    f"{t} (+{p})" if p is not None else t for t, p in m.factors))
            if m.actions:
                st.markdown("**What to do**\n" + "\n".join(f"- {a}" for a in m.actions))
            else:
                st.caption("Nothing of concern found in your answers.")
            st.caption(" · ".join(f"**{k}:** {v}" for k, v in m.basis))

    due = screening_due(d)
    if due:
        with st.container(border=True):
            st.markdown("**Free screening due for you**  \nUnder the national NCD programme, at your Ayushman Arogya Mandir, PHC or government hospital.")
            st.markdown("\n".join(f"- {s}" for s in due))

    with st.container(border=True):
        st.markdown("**Explain my result** `Claude`")
        st.caption("Claude rewrites the result above in simple words. It receives only the levels and advice, not your story, and is told not to change them.")
        result_id = hashlib.sha1(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()
        lang = st.selectbox("Language", ai.LANGUAGES, key="lang")
        if st.button("Explain my result", type="primary", disabled=not client):
            text = st.write_stream(ai.explain(client, r, d, lang))
            ss.explain = {"id": result_id, "text": text,
                          "trace": f"Claude explained the result in {lang}. The levels and advice it explained came from the rules engine."}
        elif ss.explain and ss.explain["id"] == result_id:
            st.write(ss.explain["text"])
        if not client:
            st.caption("Claude is not connected, so explanations are off.")

    st.caption("**Why no percentage?** No calculator that turns self-reported answers into a percentage chance of cancer "
               "has been validated in Indian adults. A number would look more precise than the evidence allows, so the "
               "agent reports levels of concern tied to what you should do next.")


left, right = st.columns([1, 1.1], gap="large")

# ---------- Left: Perceive + Confirm ----------
with left:
    with st.container(border=True):
        st.subheader("Tell your story · Claude")
        st.caption("Claude reads what you write and fills the questionnaire below. You then check every answer it filled.")
        story = st.text_area("Your story", key="story", height=120, label_visibility="collapsed",
                             placeholder="Example: ನನಗೆ 48 ವರ್ಷ. 15 ವರ್ಷದಿಂದ ಗುಟ್ಕಾ ತಿನ್ನುತ್ತೇನೆ. ಬಾಯಲ್ಲಿ ಬಿಳಿ ಮಚ್ಚೆ ಇದೆ. / "
                                         "I am a 48-year-old man, I chew gutka for 15 years and have a white patch in my mouth.")
        if not client:
            st.caption("Claude is not connected (no ANTHROPIC_API_KEY), so this box is off. The questionnaire and rules engine work fully.")
        if st.button("Read my story", type="primary", disabled=not client):
            if not story.strip():
                ss.story_status = ("warning", "Write a few sentences first.")
            else:
                try:
                    with st.spinner("Claude is reading…"):
                        found, followups, lang = ai.read_story(client, story)
                    for fid, v in found.items():  # widgets below are not created yet, so this is allowed
                        ss[K(fid)] = v
                    ss.ai_filled = set(found)
                    ss.followups = followups
                    ss.active_case = None
                    ss.explain = None
                    if lang in ai.LANGUAGES:
                        ss.lang = lang
                    ss.perceive = (f"Claude read your {lang} story and filled {len(found)} answers"
                                   + (f", and asked {len(followups)} follow-up questions." if followups else "."))
                    ss.story_status = ("success", f"Filled {len(found)} answers. Please check them in the form below."
                                       if found else "No answers could be filled. Try adding age, sex, habits and symptoms.")
                except ai.AIError as e:
                    ss.story_status = ("error", str(e))
        if ss.story_status:
            getattr(st, ss.story_status[0])(ss.story_status[1])
        if ss.ai_filled:
            st.markdown("**Filled from your story, please check:** " + ", ".join(FIELDS[f]["label"] for f in ss.ai_filled))
        for q in ss.followups:
            st.markdown(f"- {q}")

    snapshot = {fid: current(fid) for fid in FIELDS}
    for section in SECTIONS:
        if section.get("when") and not section["when"](snapshot):
            continue
        with st.container(border=True):
            st.subheader(section["title"])
            group = None
            for f in section["fields"]:
                fid = f["id"]
                if not FIELDS[fid]["visible"](snapshot):
                    continue
                if f.get("group") and f["group"] != group:
                    group = f["group"]
                    st.markdown(f"**{group}**")
                label = f["label"] + ("  ·  *from story*" if fid in ss.ai_filled else "")
                kw = dict(key=K(fid), on_change=mark_manual, args=(fid,))
                fresh = K(fid) not in ss  # give a default only to widgets with no stored value
                if f["type"] == "number":
                    st.number_input(label, min_value=f["min"], max_value=f["max"], step=1,
                                    **({"value": None} if fresh else {}), **kw)
                elif f["type"] == "choice":
                    opts = [o[0] for o in f["opts"]]
                    names = dict(f["opts"])
                    default = DEFAULTS.get(fid)
                    st.radio(label, opts, format_func=names.get, horizontal=True,
                             **({"index": opts.index(default) if default in opts else None} if fresh else {}), **kw)
                elif f["type"] == "select":
                    opts = [o[0] for o in f["opts"]]
                    names = dict(f["opts"])
                    default = DEFAULTS.get(fid, opts[0])
                    st.selectbox(label, opts, format_func=names.get,
                                 **({"index": opts.index(default)} if fresh else {}), **kw)
                else:
                    st.checkbox(label, **({"value": False} if fresh else {}), **kw)

    st.button("Clear all answers", on_click=clear_all)

# ---------- Right: Reason + Act ----------
with right:
    d = answers()
    if not d.get("age") or not d.get("sex"):
        st.info("Enter your age and sex to see your result, or load an example case above.")
    else:
        show_results(d)


st.divider()
with st.expander("Where the rules come from"):
    st.markdown("""
1. Ministry of Health & Family Welfare. Operational Guidelines for Prevention, Screening and Control of Common Non-Communicable Diseases (NP-NCD): oral visual examination, clinical breast examination and VIA for adults aged 30–65, every 5 years.
2. NP-NCD Community Based Assessment Checklist (CBAC), Part B: cancer warning signs asked by ASHAs.
3. Yeoh KG, et al. The Asia-Pacific Colorectal Screening score: a validated tool that stratifies risk for colorectal advanced neoplasia in asymptomatic Asian subjects. *Gut* 2011;60:1236–41.
4. National Institute for Health and Care Excellence. NG12: Suspected cancer: recognition and referral.
5. World Health Organization. WHO guideline for screening and treatment of cervical pre-cancer lesions, 2nd ed., 2021.
6. US Preventive Services Task Force. Screening for lung cancer. *JAMA* 2021;325:962–70.
7. National TB Elimination Programme: cough of 2 weeks or more is presumptive TB; sputum NAAT is free at government facilities.
8. Park K. *Textbook of Preventive and Social Medicine*: danger signals of cancer.
""")
st.caption("**Teaching prototype. Not a medical device and not validated.** Built to show students how a clinical AI agent "
           "separates language (AI) from decisions (fixed rules). Answers are not saved. \"Read my story\" and \"Explain my result\" "
           "send text to Anthropic's API. Do not type your name, phone number or Aadhaar number.")
