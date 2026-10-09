# Jagruti Cancer Check

A teaching prototype of a **clinical AI agent** that helps ordinary adults in India recognise cancer warning signs, see which free screening tests are due, and know where to go next.

Built for medical-student demonstrations at the Department of Community Medicine, Shridevi Institute of Medical Sciences & Research Hospital, Tumkur.

> **Not a medical device and not validated.** It does not diagnose cancer. It exists to show how an AI agent can be built so that the AI never makes the clinical decision.

## How the agent works

| Step | Who | What happens |
|---|---|---|
| 1. Perceive | Claude | Reads a free-text story (English, Kannada, Hindi or mixed) and fills the questionnaire, then asks up to three follow-up questions about what is missing. |
| 2. Confirm | The person | Checks every answer Claude filled; all answers stay visible and editable. |
| 3. Reason | Plain Python (`rules.py`) | Applies fixed rules to give a level of concern for each cancer area. No AI, so the same answers always give the same result. |
| 4. Act | Fixed text, then Claude | Shows protocol advice, then Claude can explain it in 8 Indian languages. Claude only receives the result, not the story, and is told not to change any level. |

Levels of concern: Low · Routine screening · Check-up within 1 month · See a doctor within 2 weeks · Go to hospital today.

**Why no percentage?** No calculator that turns self-reported answers into a percentage chance of cancer has been validated in Indian adults (the Gail breast model, for example, overestimates risk in Indian women). A number would look more precise than the evidence allows.

## Where the rules come from

| Area | Basis |
|---|---|
| Mouth and throat | NP-NCD oral visual examination (30+); CBAC Part B warning signs |
| Lung | NICE NG12 red flags; NTEP rule that a cough of 2 weeks or more means a free TB test; USPSTF 2021 low-dose CT criteria |
| Breast | NP-NCD clinical breast examination (women 30–65); CBAC Part B |
| Cervix | NP-NCD VIA (women 30–65); WHO 2021 (women living with HIV from 25) |
| Bowel | **Asia-Pacific Colorectal Screening score** (Yeoh et al., *Gut* 2011), the only validated score in the tool |
| Food pipe, stomach, liver, gallbladder | NICE NG12 red flags; NCRP regional patterns (North-East India, Gangetic plains) |
| Other warning signs | Park's danger signals of cancer; NICE NG12 |

Risk points in the other areas are a **teaching heuristic** built from established risk factors, and the app labels them as such.

## Files

| File | Purpose |
|---|---|
| `streamlit_app.py` | The Streamlit interface |
| `rules.py` | The rules engine (no AI) |
| `questionnaire.py` | Questions, example cases, and the answer schema Claude fills |
| `ai.py` | The two Claude calls (read story, explain result) |
| `tests/` | Rules and app tests (`pytest`) |
| `index.html` | A standalone single-page version of the same agent, for use as a claude.ai Artifact |

## Run locally

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml   # then paste your Anthropic API key
streamlit run streamlit_app.py
```

Without an API key the questionnaire and rules engine still work fully; only the two Claude buttons are switched off.

Run the tests with `pip install pytest` then `pytest`.

## Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. **Create app → Deploy a public app from GitHub**: choose this repository, branch `main`, main file `streamlit_app.py`.
3. Under **Advanced settings → Secrets**, paste:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
4. Deploy. Each "Read my story" or "Explain my result" press is billed to that API key.

## Privacy

Answers are not stored. Text sent with the two Claude buttons goes to Anthropic's API. Users are told not to type names, phone numbers or Aadhaar numbers.
