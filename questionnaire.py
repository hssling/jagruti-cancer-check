"""Questionnaire definition: the single source for the form AND for Claude's extraction schema."""

NEVER_PAST_NOW = [("never", "Never"), ("past", "In the past"), ("current", "Now")]


def is_female(d):
    return d.get("sex") == "female"


def is_male(d):
    return d.get("sex") == "male"


# Each section: title, optional `when` predicate, list of fields.
# Field types: number, choice (radio), select, check (checkbox). Checks may carry a `group` heading.
SECTIONS = [
    {"title": "About you", "fields": [
        {"id": "age", "type": "number", "label": "Age (years)", "min": 15, "max": 100},
        {"id": "sex", "type": "choice", "label": "Sex", "opts": [("male", "Male"), ("female", "Female")]},
        {"id": "region", "type": "select", "label": "Where do you live?", "opts": [
            ("", "Choose…"), ("south", "South India"), ("north", "North India (Gangetic plains)"),
            ("east", "East India (incl. Bihar, Bengal)"), ("northeast", "North-East India"),
            ("west", "West India"), ("central", "Central India")]},
        {"id": "height", "type": "number", "label": "Height (cm)", "min": 100, "max": 220},
        {"id": "weight", "type": "number", "label": "Weight (kg)", "min": 25, "max": 200},
    ]},
    {"title": "Tobacco, alcohol and daily life", "fields": [
        {"id": "smokeless", "type": "choice", "label": "Chewing tobacco: gutka, khaini, zarda, mawa, paan with tobacco", "opts": NEVER_PAST_NOW},
        {"id": "smokelessYears", "type": "number", "label": "Years of chewing tobacco", "min": 0, "max": 80,
         "when": lambda d: d.get("smokeless") not in (None, "never")},
        {"id": "smoking", "type": "choice", "label": "Smoking: bidi, cigarette, hookah", "opts": NEVER_PAST_NOW},
        {"id": "sticksPerDay", "type": "number", "label": "Bidis or cigarettes per day", "min": 0, "max": 100,
         "when": lambda d: d.get("smoking") not in (None, "never")},
        {"id": "smokeYears", "type": "number", "label": "Years of smoking", "min": 0, "max": 80,
         "when": lambda d: d.get("smoking") not in (None, "never")},
        {"id": "alcohol", "type": "choice", "label": "Alcohol", "opts": [("none", "None"), ("occasional", "Sometimes"), ("daily", "Daily")]},
        {"id": "areca", "type": "check", "label": "Paan or supari (areca nut) without tobacco, regularly"},
        {"id": "biomass", "type": "check", "label": "Cooked for 10+ years on wood, dung cakes, coal or kerosene indoors"},
        {"id": "occupational", "type": "check", "label": "Worked with asbestos, silica dust, mining or dye chemicals"},
        {"id": "inactive", "type": "check", "label": "Less than 150 minutes of brisk walking or exercise a week"},
        {"id": "lowVeg", "type": "check", "label": "Eat fruit or vegetables on fewer than 5 days a week"},
    ]},
    {"title": "Family and medical history", "fields": [
        {"id": "fhBreast", "type": "check", "label": "Mother, sister or daughter had breast or ovarian cancer"},
        {"id": "fhColorectal", "type": "check", "label": "Parent, brother, sister or child had bowel (colon or rectum) cancer"},
        {"id": "fhLung", "type": "check", "label": "Parent, brother or sister had lung cancer"},
        {"id": "fhOther", "type": "check", "label": "Any other cancer in a close family member"},
        {"id": "hiv", "type": "check", "label": "Living with HIV"},
        {"id": "hepBC", "type": "check", "label": "Hepatitis B or hepatitis C infection"},
        {"id": "gallstones", "type": "check", "label": "Known gallstones"},
    ]},
    {"title": "Women's health", "when": is_female, "fields": [
        {"id": "menopause", "type": "choice", "label": "Have your periods stopped for good?", "opts": [("no", "No"), ("yes", "Yes")]},
        {"id": "children", "type": "number", "label": "Number of children (deliveries)", "min": 0, "max": 15},
        {"id": "lastCervicalScreen", "type": "select", "label": "Last cervical test (VIA, Pap or HPV)", "opts": [
            ("never", "Never tested"), ("over5", "More than 5 years ago"), ("within5", "Within the last 5 years")]},
        {"id": "menarcheEarly", "type": "check", "label": "Periods started before age 12"},
        {"id": "menopauseLate", "type": "check", "label": "Periods stopped after age 55", "when": lambda d: d.get("menopause") == "yes"},
        {"id": "firstChildLate", "type": "check", "label": "First child after age 30, or no children"},
        {"id": "noBreastfeed", "type": "check", "label": "Never breastfed a child"},
        {"id": "hrt", "type": "check", "label": "Took hormone tablets after menopause (HRT)"},
        {"id": "earlyMarriage", "type": "check", "label": "Married or sexually active before age 18"},
        {"id": "multiplePartners", "type": "check", "label": "More than one sexual partner (you or your husband)"},
        {"id": "ocp", "type": "check", "label": "Took birth-control pills for 5 years or more"},
        {"id": "hpvVaccine", "type": "check", "label": "Received the HPV vaccine"},
    ]},
    {"title": "Symptoms you have now", "fields": [
        {"id": "mouthUlcer", "type": "check", "group": "Mouth and throat", "label": "A sore or ulcer in the mouth that has not healed in 2 weeks"},
        {"id": "mouthPatch", "type": "check", "group": "Mouth and throat", "label": "A white or red patch inside the mouth"},
        {"id": "mouthOpening", "type": "check", "group": "Mouth and throat", "label": "Difficulty opening the mouth fully"},
        {"id": "mouthGrowth", "type": "check", "group": "Mouth and throat", "label": "A growth or lump in the mouth"},
        {"id": "hoarseness", "type": "check", "group": "Mouth and throat", "label": "Hoarse or changed voice for more than 3 weeks"},
        {"id": "dysphagia", "type": "check", "group": "Mouth and throat", "label": "Difficulty swallowing food"},
        {"id": "cough2w", "type": "check", "group": "Chest", "label": "Cough for 2 weeks or more"},
        {"id": "haemoptysis", "type": "check", "group": "Chest", "label": "Blood in sputum (when coughing)"},
        {"id": "breastLump", "type": "check", "group": "Breast", "when": is_female, "label": "A lump in the breast or armpit"},
        {"id": "nippleDischarge", "type": "check", "group": "Breast", "when": is_female, "label": "Blood-stained discharge from the nipple"},
        {"id": "breastChange", "type": "check", "group": "Breast", "when": is_female, "label": "Change in breast size or shape, puckered skin, or pulled-in nipple"},
        {"id": "bleedIntermenstrual", "type": "check", "group": "Bleeding and discharge", "when": is_female, "label": "Bleeding between periods"},
        {"id": "bleedPostcoital", "type": "check", "group": "Bleeding and discharge", "when": is_female, "label": "Bleeding after intercourse"},
        {"id": "bleedPostmeno", "type": "check", "group": "Bleeding and discharge", "when": is_female, "label": "Bleeding after periods have stopped (after menopause)"},
        {"id": "dischargeFoul", "type": "check", "group": "Bleeding and discharge", "when": is_female, "label": "Foul-smelling vaginal discharge"},
        {"id": "bloodStool", "type": "check", "group": "Stomach and bowel", "label": "Blood in stool"},
        {"id": "blackStool", "type": "check", "group": "Stomach and bowel", "label": "Black, tar-like stools"},
        {"id": "bowelChange", "type": "check", "group": "Stomach and bowel", "label": "Loose motions or constipation that is new and has lasted 4+ weeks"},
        {"id": "anaemia", "type": "check", "group": "Stomach and bowel", "label": "Told you have anaemia (low haemoglobin) without a clear reason"},
        {"id": "dyspepsia", "type": "check", "group": "Stomach and bowel", "label": "Indigestion or upper stomach pain that keeps coming back"},
        {"id": "vomitBlood", "type": "check", "group": "Stomach and bowel", "label": "Vomiting blood"},
        {"id": "weightLoss", "type": "check", "group": "Whole body", "label": "Losing weight without trying"},
        {"id": "appetiteLoss", "type": "check", "group": "Whole body", "label": "Loss of appetite"},
        {"id": "feverNightSweats", "type": "check", "group": "Whole body", "label": "Fever for more than 2 weeks, or drenching night sweats"},
        {"id": "lumpElsewhere", "type": "check", "group": "Whole body", "label": "A lump in the neck, armpit, groin or elsewhere"},
        {"id": "haematuria", "type": "check", "group": "Whole body", "label": "Blood in urine"},
        {"id": "urineDifficulty", "type": "check", "group": "Whole body", "when": is_male, "label": "Weak stream or difficulty passing urine"},
        {"id": "moleChange", "type": "check", "group": "Whole body", "label": "A mole or wart that is growing, changing colour or bleeding"},
        {"id": "jaundice", "type": "check", "group": "Whole body", "label": "Yellow eyes or skin (jaundice)"},
        {"id": "abdSwelling", "type": "check", "group": "Whole body", "label": "Swelling or a lump in the abdomen"},
    ]},
]

# Flat index: id -> field (with the section's `when` folded into the field's own)
FIELDS = {}
for _s in SECTIONS:
    for _f in _s["fields"]:
        conds = [c for c in (_s.get("when"), _f.get("when")) if c]
        FIELDS[_f["id"]] = {**_f, "visible": (lambda cs: lambda d: all(c(d) for c in cs))(conds)}

DEFAULTS = {"smokeless": "never", "smoking": "never", "alcohol": "none", "menopause": "no", "lastCervicalScreen": "never"}


def coerce(field, value):
    """Turn a value from Claude (always a string in our schema) into the form's type. None = reject."""
    v = str(value).strip().lower() if value is not None else ""
    t = field["type"]
    if t == "check":
        return True if v in ("true", "yes", "1") else None
    if t == "number":
        try:
            n = float(v)
        except ValueError:
            return None
        return int(n) if field["min"] <= n <= field["max"] else None
    allowed = [o[0] for o in field["opts"] if o[0]]
    return v if v in allowed else None


# Invented example cases for teaching
CASES = [
    {"key": "A", "label": "A · Man, 52, chews gutka, white patch", "d": {
        "age": 52, "sex": "male", "region": "south", "height": 166, "weight": 58, "smokeless": "current",
        "smokelessYears": 20, "areca": True, "alcohol": "occasional", "mouthPatch": True}},
    {"key": "B", "label": "B · Woman, 46, bleeding after intercourse", "d": {
        "age": 46, "sex": "female", "region": "north", "height": 152, "weight": 61, "children": 4,
        "earlyMarriage": True, "lastCervicalScreen": "never", "biomass": True, "bleedPostcoital": True}},
    {"key": "C", "label": "C · Man, 61, bidi smoker, long cough", "d": {
        "age": 61, "sex": "male", "region": "east", "height": 162, "weight": 50, "smoking": "current",
        "sticksPerDay": 25, "smokeYears": 40, "biomass": True, "cough2w": True, "weightLoss": True}},
    {"key": "D", "label": "D · Woman, 42, mother had breast cancer", "d": {
        "age": 42, "sex": "female", "region": "west", "height": 158, "weight": 68, "children": 1,
        "firstChildLate": True, "fhBreast": True, "lastCervicalScreen": "over5", "inactive": True}},
    {"key": "E", "label": "E · Woman, 34, no symptoms", "d": {
        "age": 34, "sex": "female", "region": "south", "height": 155, "weight": 54, "children": 2,
        "lastCervicalScreen": "within5"}},
]
