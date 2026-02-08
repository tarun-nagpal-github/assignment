"""
Parse natural-language search queries into structured filters for industry and location.
Uses spaCy (https://spacy.io/models#quickstart) for NER and lemmatization.

E.g. "tech companies in california" -> industry_keywords for technology, location "california".

Requires:
  pip install spacy
  python -m spacy download en_core_web_sm
"""
import re
from typing import Optional

# Semantic matching: user terms -> phrases that appear in the index (e.g. "information technology and services")
# So "software" matches docs with industry "information technology and services" or "computer software"
INDUSTRY_EXPANSION = {
    "tech": ["technology", "software", "information technology", "information technology and services", "computer", "it services", "computer software"],
    "technology": ["technology", "software", "information technology", "information technology and services", "computer", "computer software"],
    "software": ["software", "information technology", "information technology and services", "computer software", "it services"],
    "it": ["information technology", "information technology and services", "it services", "computer", "computer software"],
    "fintech": ["financial", "fintech", "banking", "financial services"],
    "finance": ["financial", "finance", "banking", "investment"],
    "healthcare": ["healthcare", "hospital", "medical", "health"],
    "health": ["healthcare", "health", "medical"],
    "retail": ["retail", "consumer", "e-commerce", "ecommerce"],
    "manufacturing": ["manufacturing", "industrial", "production"],
    "consulting": ["consulting", "professional services", "business services"],
    "education": ["education", "e-learning", "edtech", "training"],
    "media": ["media", "entertainment", "publishing", "broadcast"],
    "real estate": ["real estate", "real estate development", "property"],
    "energy": ["energy", "oil", "gas", "renewable", "utilities"],
    "transport": ["transport", "transportation", "logistics", "shipping"],
    "food": ["food", "restaurant", "food & beverage", "hospitality"],
    "marketing": ["marketing", "advertising", "market research"],
    "hr": ["human resources", "hr", "staffing", "recruiting"],
    "recruiting": ["recruiting", "staffing", "human resources", "talent"],
}

# spaCy NER labels we treat as location (GPE=geo-political, LOC=location, FAC=facility)
LOCATION_ENTITY_LABELS = ("GPE", "LOC", "FAC")

_nlp = None


def _get_nlp():
    """Lazy-load spaCy model (en_core_web_sm). Returns None if not installed."""
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
        return _nlp
    except Exception:
        _nlp = False  # mark as attempted
        return None


def _normalize(s: str) -> str:
    return (s or "").strip().lower()


def _expand_industry(user_term: str) -> list:
    """Map a user industry term to a list of keywords to match on the industry field."""
    t = _normalize(user_term)
    if not t:
        return []
    if t in INDUSTRY_EXPANSION:
        return list(INDUSTRY_EXPANSION[t])
    if t.endswith("s") and t[:-1] in INDUSTRY_EXPANSION:
        return list(INDUSTRY_EXPANSION[t[:-1]])
    return [t]


def understand_query(query: Optional[str]) -> dict:
    """
    Parse a query like "tech companies in california" into structured filters using spaCy.
    Uses NER for locations (GPE, LOC, FAC) and lemmatization + INDUSTRY_EXPANSION for industry.
    Returns:
      - industry_keywords: list of terms to match on industry (text)
      - location: string to match on locality/country, or None
      - residual_query: remaining query for free-text, or None

    If spaCy is not installed, returns empty filters. Install with:
      pip install spacy && python -m spacy download en_core_web_sm
    """
    if not query or not query.strip():
        return {"industry_keywords": [], "location": None, "residual_query": None}

    nlp = _get_nlp()
    if nlp is None:
        return {"industry_keywords": [], "location": None, "residual_query": None}

    doc = nlp(query.strip())
    industry_keywords = []
    location = None

    # 1) Extract location from named entities (GPE, LOC, FAC)
    locations = [
        ent.text.strip()
        for ent in doc.ents
        if ent.label_ in LOCATION_ENTITY_LABELS
    ]
    if locations:
        location = _normalize(locations[0])
        if len(locations) > 1:
            location = " ".join(_normalize(l) for l in locations[:2])

    # 2) Find industry: token(s) before "companies", lemmatized for better matching
    q_lower = query.lower()
    m = re.search(r"^(.+?)\s+companies?\s+(?:in\s+.+)?$", q_lower)
    if m:
        industry_part = _normalize(m.group(1))
        if industry_part and industry_part != "all":
            industry_keywords = _expand_industry(industry_part)
            if not industry_keywords:
                for token in doc:
                    if token.text.lower() in industry_part.split():
                        lemma = token.lemma_.lower()
                        if lemma and lemma not in ("company", "companies"):
                            industry_keywords = _expand_industry(lemma)
                            break
    else:
        # No "X companies" pattern: use noun chunks as industry hint
        skip = ("company", "companies", "california", "india", "new york", "york")
        for np in doc.noun_chunks:
            root = np.root.text.lower()
            if root not in skip:
                industry_keywords = _expand_industry(root)
                if industry_keywords:
                    break

    return {
        "industry_keywords": industry_keywords,
        "location": location,
        "residual_query": None,
    }
