"""Agent1 ML + rule-based department classifier."""



import logging



logger = logging.getLogger(__name__)



from .agent1_config import (  # noqa: E402

    AUTHORITY_MAP,

    BIJLI_TYPE_MAP,

    EDUCATION_CATEGORY_MAP,

    JAL_TYPE_MAP,

    PWD_CATEGORY_MAP,

)



_ml_ready = False

_vectorizer = None

_dept_model = None

_sub_model = None



_EDUCATION_ROLL_WORDS = ("number", "exam", "result", "admission", "class roll", "attendance roll")





def _valid_subcategories(dept: str) -> set[str]:

    if dept == "Electricity":

        return set(BIJLI_TYPE_MAP.keys()) | set(BIJLI_TYPE_MAP.values())

    if dept == "Water":

        return set(JAL_TYPE_MAP.keys()) | set(JAL_TYPE_MAP.values())

    if dept == "Education":

        return set(EDUCATION_CATEGORY_MAP.keys()) | set(EDUCATION_CATEGORY_MAP.values())

    if dept == "PWD":

        return set(PWD_CATEGORY_MAP.keys()) | set(PWD_CATEGORY_MAP.values())

    return {"Other", "Other Request"}





def _rule_department(text: str) -> str | None:

    """Keyword routing — runs before ML so subcategory stays aligned with department."""

    t = text.lower()



    if any(w in t for w in [

        "electric", "electricity", "power cut", "power supply", "no power", "no electricity",

        "transformer", "voltage", "meter", "bijli", "current", "outage", "load shedding",

    ]):

        return "Electricity"

    if "light" in t and any(w in t for w in ["street", "bulb", "lamp", "pole", "dark"]):

        return "Electricity"

    if any(w in t for w in [

        "water", "pipe", "tap", "sewage", "drain", "leakage", "leak", "flood",

        "borewell", "handpump", "tanker", "paani", "jal ",

    ]):

        return "Water"



    road_words = [

        "road", "roads", "sadak", "rasta", "pothole", "gaddha", "gaddhe", "footpath",

        "highway", "street", "bridge", "pathway", "broken road", "damaged road",

    ]

    if any(w in t for w in road_words):

        return "PWD"

    if any(w in t for w in ["broken", "damaged", "bad condition", "cracked"]) and any(

        w in t for w in ["road", "roads", "sadak", "rasta", "street", "path", "area", "mohalla", "colony"]

    ):

        return "PWD"

    # Common typo: "rolls" instead of "roads"

    if ("roll" in t or "rolls" in t) and not any(w in t for w in _EDUCATION_ROLL_WORDS):

        if any(w in t for w in ["damaged", "broken", "bad condition", "area", "mohalla", "colony", "street"]):

            return "PWD"



    if any(w in t for w in [

        "teacher", "school", "exam", "scholarship", "mid-day meal", "midday meal",

        "education", "student", "college", "textbook", "admission", "fee", "classroom",

    ]):

        return "Education"

    return None





def _rule_subcategory(dept: str, text: str) -> str | None:

    t = text.lower()

    if dept == "Electricity":

        if any(w in t for w in ["voltage", "dim", "surge", "low volt"]):

            return "Voltage Issue"

        if "bill" in t:

            return "Wrong Bill"

        if "meter" in t:

            return "Meter Fault"

        if "street light" in t or ("street" in t and "light" in t):

            return "Street Light Issue"

        if any(w in t for w in ["no power", "no electricity", "blackout", "power cut", "transformer"]):

            return "No Power Supply"

    if dept == "Water":

        if any(w in t for w in ["leak", "burst", "broken pipe"]):

            return "Pipe Leakage / Burst"

        if any(w in t for w in ["sewage", "drain", "sewer"]):

            return "Sewage / Drainage Problem"

        return "Water Supply Disruption"

    if dept == "PWD":

        if "encroach" in t:

            return "Encroachment on Road"

        if any(w in t for w in [

            "pothole", "gaddha", "gaddhe", "broken", "damaged", "bad condition",

            "cracked", "roll", "rolls", "road", "roads", "sadak", "rasta",

        ]):

            return "Road Pothole"

        if "bridge" in t:

            return "Bridge Condition"

        if any(w in t for w in ["garbage", "sanitation", "waste", "dump"]):

            return "Garbage / Sanitation Issue"

    if dept == "Education":

        if "mid" in t and "meal" in t:

            return "Mid-Day Meal Complaint"

        if any(w in t for w in ["scholar", "fee"]):

            return "Scholarship / Fee Issue"

        if any(w in t for w in ["exam", "result"]):

            return "Examination Related"

        if any(w in t for w in ["broken", "infrastructure", "building", "toilet", "classroom"]):

            return "School Infrastructure Problem"

    return None





def _get_priority(text: str) -> str:

    t = text.lower()

    if any(w in t for w in [

        "urgent", "danger", "accident", "serious", "immediately",

        "emergency", "help", "asap", "critical", "no water",

        "no power", "no electricity", "days", "weeks", "months",

    ]):

        return "High"

    try:

        from textblob import TextBlob



        polarity = TextBlob(text).sentiment.polarity

        if polarity < -0.4:

            return "High"

        if polarity < 0:

            return "Medium"

    except Exception:

        pass

    return "Low"





def _load_ml():

    global _ml_ready, _vectorizer, _dept_model, _sub_model

    if _ml_ready:

        return True

    try:

        from pathlib import Path



        import pandas as pd

        from django.conf import settings

        from sklearn.feature_extraction.text import TfidfVectorizer

        from sklearn.naive_bayes import MultinomialNB



        path = Path(getattr(settings, "AGENT1_TRAINING_DATA", ""))

        if not path.is_file():

            path = Path(__file__).resolve().parent.parent / "data" / "agent1_training.csv"

        df = pd.read_csv(path)

        _vectorizer = TfidfVectorizer()

        x_vec = _vectorizer.fit_transform(df["text"])

        _dept_model = MultinomialNB()

        _dept_model.fit(x_vec, df["department"])

        _sub_model = MultinomialNB()

        _sub_model.fit(x_vec, df["subcategory"])

        _ml_ready = True

        logger.info("Agent1 ML classifier loaded from %s", path)

        return True

    except Exception as exc:

        logger.warning("Agent1 ML classifier unavailable (%s); using rules only.", exc)

        return False





def _default_subcategory(dept: str, text: str) -> str:

    ruled = _rule_subcategory(dept, text)

    if ruled:

        return ruled

    if dept == "Electricity":

        return "No Power Supply"

    if dept == "Water":

        return "Water Supply Disruption"

    if dept == "PWD":

        return "Road Pothole"

    if dept == "Education":

        return "School Infrastructure Problem"

    return "Other Request"





def _resolve_subcategory(dept: str, text: str, ml_sub: str | None) -> str:

    ruled = _rule_subcategory(dept, text)

    if ruled:

        return ruled

    valid = _valid_subcategories(dept)

    if ml_sub and ml_sub in valid:

        return ml_sub

    return _default_subcategory(dept, text)





def classify_agent1(english_text: str) -> dict:

    text = (english_text or "").strip()

    if not text:

        return {

            "department": "Other",

            "subcategory": "Other",

            "priority": "Low",

            "authority": AUTHORITY_MAP["Other"],

            "model_version": "agent1-rules-empty",

        }



    rule_dept = _rule_department(text)

    ml_sub = None



    if _load_ml():

        vec = _vectorizer.transform([text])

        ml_dept = str(_dept_model.predict(vec)[0])

        ml_sub = str(_sub_model.predict(vec)[0])

        dept = rule_dept or ml_dept

        model_version = "agent1-ml-v1"

    else:

        dept = rule_dept or "Other"

        model_version = "agent1-rules-v1"



    subcategory = _resolve_subcategory(dept, text, ml_sub)

    priority = _get_priority(text)

    authority = AUTHORITY_MAP.get(dept, AUTHORITY_MAP["Other"])

    return {

        "department": dept,

        "subcategory": subcategory,

        "priority": priority,

        "authority": authority,

        "model_version": model_version,

    }


