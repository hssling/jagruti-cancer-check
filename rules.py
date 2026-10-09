"""Rules engine: plain Python, no AI. Every level of concern is decided here.

The same answers always give the same result. Claude never changes a level; it only
reads stories into answers (ai.py) and explains this module's output.
"""
from dataclasses import dataclass, field

TIERS = [
    {"label": "Low concern", "short": "Low",
     "line": "No warning signs and few risk factors. Keep healthy habits and know the warning signs."},
    {"label": "Routine screening", "short": "Routine",
     "line": "No warning signs. Get the free screening tests that are due for your age."},
    {"label": "Check-up due soon", "short": "Within 1 month",
     "line": "No warning signs, but your risk factors or overdue screening mean you should visit a health centre within a month."},
    {"label": "See a doctor within 2 weeks", "short": "Within 2 weeks",
     "line": "You reported a warning sign. Most such signs turn out not to be cancer, but each one must be examined by a doctor."},
    {"label": "Go to hospital today", "short": "Today",
     "line": "You reported a sign that needs emergency care."},
]

QUIT = "Quitting tobacco is the biggest single step you can take. National Tobacco Quitline (free): 1800-11-2356."


@dataclass
class Module:
    id: str
    name: str
    max: int
    basis: list
    points: int = 0
    factors: list = field(default_factory=list)   # (text, points or None)
    flags: list = field(default_factory=list)     # warning signs
    actions: list = field(default_factory=list)
    tier: int = 0
    score_label: str | None = None

    def add(self, cond, pts, text):
        if cond:
            self.points += pts
            self.factors.append((text, pts))

    def flag(self, cond, text):
        if cond:
            self.flags.append(text)


def num(d, k):
    try:
        return float(d.get(k) or 0)
    except (TypeError, ValueError):
        return 0.0


def bmi_of(d):
    h, w = num(d, "height"), num(d, "weight")
    return w / (h / 100) ** 2 if h > 0 and w > 0 else None


def pack_years(d):
    if d.get("smoking") not in ("current", "past"):
        return 0.0
    return num(d, "sticksPerDay") / 20 * num(d, "smokeYears")


def assess(d):
    """d: dict of answers keyed by questionnaire id. Returns dict(mods, overall, fired, bmi, py)."""
    age = num(d, "age")
    female, male = d.get("sex") == "female", d.get("sex") == "male"
    bmi, py = bmi_of(d), pack_years(d)
    smoke_now = d.get("smoking") == "current"
    smoke_ever = d.get("smoking") in ("current", "past")
    chew_now = d.get("smokeless") == "current"
    tobacco_now = smoke_now or chew_now
    alcohol_daily = d.get("alcohol") == "daily"
    g = lambda k: bool(d.get(k))
    mods = []

    # Oral cavity and throat: the commonest cancer in Indian men
    o = Module("oral", "Mouth and throat", 10, [
        ("Programme", "NP-NCD oral visual examination for all adults 30+"),
        ("Warning signs", "CBAC Part B; NICE NG12 (hoarseness >3 weeks)"),
        ("Risk points", "teaching heuristic from established risk factors, not a validated score")])
    o.flag(g("mouthUlcer"), "Mouth sore not healed in 2 weeks")
    o.flag(g("mouthPatch"), "White or red patch in the mouth (can be pre-cancer)")
    o.flag(g("mouthOpening"), "Difficulty opening the mouth (possible oral submucous fibrosis)")
    o.flag(g("mouthGrowth"), "Growth or lump in the mouth")
    o.flag(g("hoarseness"), "Hoarse voice for more than 3 weeks")
    o.add(chew_now, 3, "Chews tobacco now")
    o.add(d.get("smokeless") == "past", 1, "Chewed tobacco in the past")
    o.add(d.get("smokeless") not in (None, "never") and num(d, "smokelessYears") >= 10, 1, "Chewed tobacco for 10+ years")
    o.add(g("areca"), 2, "Regular paan or supari (areca nut)")
    o.add(smoke_now, 2, "Smokes now")
    o.add(d.get("smoking") == "past", 1, "Smoked in the past")
    o.add(alcohol_daily, 1, "Drinks alcohol daily")
    o.add(alcohol_daily and tobacco_now, 1, "Alcohol with tobacco multiplies the risk")
    o.tier = 3 if o.flags else 2 if o.points >= 4 else 1 if age >= 30 else 0
    if o.tier == 3:
        o.actions.append("Show your mouth or throat to a doctor or dentist within 2 weeks. A patch or sore that does not heal needs examination and may need a small biopsy. Pre-cancer found now can be treated fully.")
    if o.tier == 2:
        o.actions.append("Get a free oral visual examination at your nearest Ayushman Arogya Mandir or PHC now, and every year while you use tobacco or areca nut.")
    if o.tier == 1:
        o.actions.append("Free oral visual examination every 5 years from age 30 under the national NCD programme.")
    if tobacco_now:
        o.actions.append(QUIT)
    if o.points > 0:
        o.actions.append("Look inside your mouth with a mirror once a month for white or red patches and sores.")
    mods.append(o)

    # Lung, with the Indian TB overlap
    lu = Module("lung", "Lung (and TB check)", 7, [
        ("Warning signs", "NICE NG12 (blood in sputum, cough with weight loss)"),
        ("TB rule", "NTEP: cough of 2 weeks or more is presumptive TB"),
        ("Scan eligibility", "USPSTF 2021: age 50–80 with 20+ pack-years (not part of India's national programme)"),
        ("Risk points", "teaching heuristic")])
    lu.flag(g("haemoptysis"), "Blood in sputum")
    lu.flag(g("cough2w") and (g("weightLoss") or g("feverNightSweats")), "Long cough together with weight loss or fever")
    lu.add(py >= 20, 3, f"Heavy smoking: about {round(py)} pack-years")
    lu.add(10 <= py < 20, 2, f"Smoking: about {round(py)} pack-years")
    lu.add(0 < py < 10, 1, "Some smoking history")
    lu.add(smoke_ever and py == 0, 1, "Smoking history (amount not given)")
    lu.add(g("biomass"), 1, "Years of indoor smoke from cooking fuel")
    lu.add(g("occupational"), 1, "Work exposure to asbestos, silica or mining dust")
    lu.add(g("fhLung"), 1, "Lung cancer in a parent or sibling")
    ldct = 50 <= age <= 80 and py >= 20
    lu.tier = 3 if lu.flags else 2 if (g("cough2w") or ldct or lu.points >= 3) else 1 if lu.points > 0 else 0
    if g("cough2w"):
        lu.actions.append("A cough of 2 weeks or more must be tested for TB first. The sputum test (NAAT) is free at any government health facility.")
    if lu.tier == 3:
        lu.actions.append("See a doctor within 2 weeks for a chest X-ray and examination.")
    if ldct:
        lu.score_label = "Meets USPSTF scan criteria"
        lu.actions.append("Ask a chest physician whether a low-dose CT scan of the chest is right for you.")
    if smoke_now:
        lu.actions.append(QUIT)
    if g("biomass"):
        lu.actions.append("Use LPG (Ujjwala scheme) or cook in a well-ventilated space to reduce smoke exposure.")
    mods.append(lu)

    if female:
        # Breast: the commonest cancer in Indian women
        b = Module("breast", "Breast", 10, [
            ("Programme", "NP-NCD clinical breast examination, women 30–65, every 5 years"),
            ("Warning signs", "CBAC Part B; NICE NG12"),
            ("Risk points", "teaching heuristic from reproductive and family risk factors (the Gail model overestimates risk in Indian women, so it is not used)")])
        b.flag(g("breastLump"), "Lump in the breast or armpit")
        b.flag(g("nippleDischarge"), "Blood-stained nipple discharge")
        b.flag(g("breastChange"), "Change in breast shape, skin or nipple")
        b.add(g("fhBreast"), 2, "Breast or ovarian cancer in mother, sister or daughter")
        b.add(age >= 50, 1, "Age 50 or above")
        b.add(g("menarcheEarly"), 1, "Periods started before 12")
        b.add(g("menopauseLate"), 1, "Late menopause")
        b.add(g("firstChildLate") or d.get("children") == 0, 1, "First child after 30, or no children")
        b.add(g("noBreastfeed"), 1, "Never breastfed")
        b.add(g("hrt"), 1, "Hormone therapy after menopause")
        b.add(bmi is not None and bmi >= 25 and d.get("menopause") == "yes", 1, f"Overweight after menopause (BMI {bmi:.1f})" if bmi else "")
        b.add(alcohol_daily, 1, "Daily alcohol")
        b.tier = 3 if b.flags else 2 if (g("fhBreast") or b.points >= 4) else 1 if 30 <= age <= 65 else 0
        if b.tier == 3:
            b.actions.append("See a doctor within 2 weeks for a breast examination and ultrasound or mammogram. Most breast lumps are not cancer, but every lump must be checked.")
        if b.tier == 2:
            b.actions.append("Get a clinical breast examination now, and ask a doctor about mammography from age 40"
                             + (" (or earlier, because of your family history)." if g("fhBreast") else "."))
        if b.tier == 1:
            b.actions.append("Free clinical breast examination every 5 years from age 30 at your health centre.")
        b.actions.append("Know how your breasts normally look and feel, and report any change.")
        mods.append(b)

        # Cervix: second commonest in Indian women, and almost fully preventable
        c = Module("cervix", "Cervix (mouth of the womb)", 10, [
            ("Programme", "NP-NCD VIA screening, women 30–65, every 5 years"),
            ("Warning signs", "CBAC Part B; NICE NG12 (post-menopausal bleeding)"),
            ("HIV rule", "WHO 2021: women living with HIV screen from age 25, every 3 years"),
            ("Risk points", "teaching heuristic")])
        c.flag(g("bleedPostcoital"), "Bleeding after intercourse")
        c.flag(g("bleedIntermenstrual"), "Bleeding between periods")
        c.flag(g("bleedPostmeno"), "Bleeding after menopause")
        c.flag(g("dischargeFoul"), "Foul-smelling vaginal discharge")
        screen = d.get("lastCervicalScreen") or "never"
        c.add(screen == "never", 2, "Never had a cervical screening test")
        c.add(screen == "over5", 1, "Last cervical test more than 5 years ago")
        c.add(g("earlyMarriage"), 2, "Sexually active before 18")
        c.add(num(d, "children") >= 4, 1, "Four or more deliveries")
        c.add(g("multiplePartners"), 1, "More than one sexual partner")
        c.add(g("hiv"), 3, "Living with HIV")
        c.add(smoke_now, 1, "Smokes")
        c.add(g("ocp"), 1, "Long-term birth-control pills")
        due = 30 <= age <= 65 and screen != "within5"
        hiv_due = g("hiv") and age >= 25
        c.tier = 3 if c.flags else 2 if (due or hiv_due) else 1 if 30 <= age <= 65 else 0
        if c.tier == 3:
            c.actions.append("See a doctor (gynaecologist) within 2 weeks for a speculum examination and screening test.")
        if c.tier == 2:
            c.actions.append("Get a cervical screening test now and every 3 years, at your ART centre or health centre." if hiv_due
                             else "Your cervical screening test is due. VIA is free at your nearest Ayushman Arogya Mandir or PHC; it takes a few minutes.")
        if c.tier == 1:
            c.actions.append("Keep up cervical screening every 5 years until age 65.")
        c.actions.append("HPV vaccination of girls aged 9–14 prevents most cervical cancers. Ask about it for your daughters.")
        mods.append(c)

    # Colorectal: the only module using a validated Asian score (APCS)
    k = Module("bowel", "Bowel (colon and rectum)", 7, [
        ("Validated score", "Asia-Pacific Colorectal Screening (APCS) score, Yeoh et al., Gut 2011"),
        ("Warning signs", "NICE NG12"),
        ("Note", "India has no national bowel cancer screening programme")])
    k.flag(g("bloodStool"), "Blood in stool")
    k.flag(g("blackStool"), "Black, tar-like stools")
    k.flag(g("bowelChange"), "Change in bowel habit for 4+ weeks")
    k.flag(g("anaemia"), "Unexplained anaemia")
    k.add(50 <= age < 70, 2, "APCS: age 50–69")
    k.add(age >= 70, 3, "APCS: age 70+")
    k.add(male, 1, "APCS: male")
    k.add(g("fhColorectal"), 2, "APCS: bowel cancer in a first-degree relative")
    k.add(smoke_ever, 1, "APCS: current or past smoker")
    k.score_label = f"APCS {k.points}/7: " + ("high" if k.points >= 4 else "moderate" if k.points >= 2 else "average") + " risk"
    k.tier = 3 if k.flags else 2 if k.points >= 4 else 1 if k.points >= 2 else 0
    if k.tier == 3:
        k.actions.append("See a doctor within 2 weeks. Piles and infections are common causes, but bleeding or a lasting change in bowel habit must be examined, especially after 40.")
    if k.tier == 2:
        k.actions.append("High risk on the APCS score: ask a doctor whether you need a colonoscopy.")
    if k.tier == 1:
        k.actions.append("Moderate risk on the APCS score: ask a doctor about a stool test for hidden blood (FIT).")
    if g("lowVeg") or g("inactive"):
        k.actions.append("Daily vegetables, fruit and whole grains, and 30 minutes of walking, lower bowel cancer risk.")
    mods.append(k)

    # Food pipe and stomach
    u = Module("upper", "Food pipe and stomach", 5, [
        ("Warning signs", "NICE NG12 (difficulty swallowing at any age; age 55+ with weight loss and indigestion)"),
        ("Region", "higher oesophageal and stomach cancer rates in North-East India (NCRP)"),
        ("Risk points", "teaching heuristic")])
    u.flag(g("dysphagia"), "Difficulty swallowing")
    u.flag(age >= 55 and g("weightLoss") and g("dyspepsia"), "Age 55+ with indigestion and weight loss")
    u.flag(g("dyspepsia") and (g("blackStool") or g("anaemia")), "Indigestion with black stools or anaemia")
    u.add(smoke_now, 1, "Smokes")
    u.add(chew_now, 1, "Chews tobacco")
    u.add(alcohol_daily, 1, "Daily alcohol")
    u.add(d.get("region") == "northeast", 2, "Lives in North-East India")
    u.tier = 4 if g("vomitBlood") else 3 if u.flags else 2 if (g("dyspepsia") and age >= 55) else 1 if u.points >= 2 else 0
    if g("vomitBlood"):
        u.flags.insert(0, "Vomiting blood")
        u.actions.append("Go to the nearest hospital emergency today.")
    elif u.tier == 3:
        u.actions.append("See a doctor within 2 weeks; you may need an endoscopy.")
    if u.tier == 2:
        u.actions.append("Recurring indigestion after 55 should be checked by a doctor within a month.")
    if u.tier <= 1 and u.points > 0:
        u.actions.append("Avoid very hot tea or drinks, tobacco and alcohol.")
    mods.append(u)

    # Liver and gallbladder: hepatitis B, alcohol, and the Gangetic gallbladder belt
    h = Module("liver", "Liver and gallbladder", 6, [
        ("Warning signs", "NICE NG12 (jaundice, abdominal mass)"),
        ("Region", "gallbladder cancer is among the commonest cancers in women of the Gangetic plains (NCRP)"),
        ("Risk points", "teaching heuristic")])
    h.flag(g("jaundice"), "Yellow eyes or skin")
    h.flag(g("abdSwelling"), "Swelling or lump in the abdomen")
    gangetic = d.get("region") in ("north", "east")
    h.add(g("hepBC"), 2, "Hepatitis B or C")
    h.add(alcohol_daily, 2, "Daily alcohol")
    h.add(g("gallstones"), 1, "Gallstones")
    h.add(g("gallstones") and gangetic, 1, "Gallstones in a high-risk region")
    h.tier = 3 if h.flags else 2 if (g("hepBC") or alcohol_daily or (g("gallstones") and gangetic)) else 1 if h.points > 0 else 0
    if h.tier == 3:
        h.actions.append("See a doctor within 2 weeks for liver tests and an abdominal ultrasound.")
    if g("hepBC"):
        h.actions.append("Hepatitis B or C needs regular follow-up and treatment, often free under the National Viral Hepatitis Control Programme. Family members should get the hepatitis B vaccine.")
    if alcohol_daily:
        h.actions.append("Daily alcohol damages the liver. Ask a doctor for a liver check-up and help to cut down.")
    if g("gallstones") and gangetic:
        h.actions.append("Discuss your gallstones with a surgeon; in this region they are usually removed even with mild symptoms.")
    mods.append(h)

    # Other warning signs (Park's danger signals of cancer)
    w = Module("general", "Other warning signs", 0, [
        ("Warning signs", "Park's danger signals of cancer; NICE NG12 (unexplained weight loss, visible blood in urine at 45+)")])
    w.flag(g("weightLoss"), "Losing weight without trying")
    w.flag(g("lumpElsewhere"), "Lump in the neck, armpit, groin or elsewhere")
    w.flag(g("haematuria"), "Blood in urine")
    w.flag(g("moleChange"), "Changing or bleeding mole")
    prostate = g("urineDifficulty") and male and age >= 50
    soft = [t for cond, t in [(g("feverNightSweats"), "Fever over 2 weeks or night sweats"),
                              (g("appetiteLoss"), "Loss of appetite"),
                              (prostate, "Difficulty passing urine at 50+")] if cond]
    w.factors = [(s, None) for s in soft]
    w.tier = 3 if w.flags else 2 if soft else 0
    if w.tier == 3:
        w.actions.append("See a doctor within 2 weeks and describe each of these signs.")
    if g("feverNightSweats"):
        w.actions.append("Long fever or night sweats: get tested for TB at a government health facility (free).")
    if prostate:
        w.actions.append("See a doctor about your urine flow; ask whether a prostate examination or PSA test is needed.")
    if w.tier > 0:
        mods.append(w)

    overall = max(m.tier for m in mods)
    fired = sum(len(m.flags) + len(m.factors) for m in mods)
    return {"mods": mods, "overall": overall, "fired": fired, "bmi": bmi, "py": py}


def screening_due(d):
    """Free NP-NCD screening for this age and sex."""
    age, out = num(d, "age"), []
    if age >= 30:
        out.append("Oral visual examination, every 5 years")
        if d.get("sex") == "female" and age <= 65:
            out += ["Clinical breast examination, every 5 years", "Cervical screening by VIA, every 5 years"]
        out.append("Blood pressure and blood sugar check")
    return out
