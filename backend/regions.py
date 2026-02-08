"""
Multi-country and locale support for Part Three (Going global).
Maps country codes/names to normalized index values and optional per-country indices.
"""
from typing import Optional

# Normalize user input (code or name) -> canonical value stored in index (lowercase country name)
COUNTRY_NORMALIZE = {
    "us": "united states",
    "usa": "united states",
    "united states": "united states",
    "united states of america": "united states",
    "in": "india",
    "india": "india",
    "ind": "india",
    "br": "brazil",
    "brazil": "brazil",
    "bra": "brazil",
    "gb": "united kingdom",
    "uk": "united kingdom",
    "united kingdom": "united kingdom",
    "de": "germany",
    "germany": "germany",
    "deu": "germany",
    "fr": "france",
    "france": "france",
    "fra": "france",
    "jp": "japan",
    "japan": "japan",
    "jpn": "japan",
    "cn": "china",
    "china": "china",
    "chn": "china",
    "ca": "canada",
    "canada": "canada",
    "can": "canada",
    "au": "australia",
    "australia": "australia",
    "aus": "australia",
    "mx": "mexico",
    "mexico": "mexico",
    "mex": "mexico",
    "es": "spain",
    "spain": "spain",
    "esp": "spain",
    "ie": "ireland",
    "ireland": "ireland",
    "irl": "ireland",
    "nl": "netherlands",
    "netherlands": "netherlands",
    "nld": "netherlands",
    "sg": "singapore",
    "singapore": "singapore",
    "sgp": "singapore",
    "ar": "argentina",
    "argentina": "argentina",
    "arg": "argentina",
}

# Canonical country -> optional index suffix for index-per-country (company_{suffix})
# When OPENSEARCH_INDEX_PER_COUNTRY is used, search company_us, company_in, etc.
COUNTRY_INDEX_SUFFIX = {
    "united states": "us",
    "india": "in",
    "brazil": "br",
    "united kingdom": "uk",
    "germany": "de",
    "france": "fr",
    "japan": "jp",
    "china": "cn",
    "canada": "ca",
    "australia": "au",
    "mexico": "mx",
    "spain": "es",
    "ireland": "ie",
    "netherlands": "nl",
    "singapore": "sg",
    "argentina": "ar",
}

# Supported regions for GET /regions: id, label, locale, index_suffix
SUPPORTED_REGIONS = [
    {"id": "united states", "label": "United States", "locale": "en-US", "index_suffix": "us"},
    {"id": "india", "label": "India", "locale": "en-IN", "index_suffix": "in"},
    {"id": "brazil", "label": "Brazil", "locale": "pt-BR", "index_suffix": "br"},
    {"id": "united kingdom", "label": "United Kingdom", "locale": "en-GB", "index_suffix": "uk"},
    {"id": "germany", "label": "Germany", "locale": "de-DE", "index_suffix": "de"},
    {"id": "france", "label": "France", "locale": "fr-FR", "index_suffix": "fr"},
    {"id": "japan", "label": "Japan", "locale": "ja-JP", "index_suffix": "jp"},
    {"id": "china", "label": "China", "locale": "zh-CN", "index_suffix": "cn"},
    {"id": "canada", "label": "Canada", "locale": "en-CA", "index_suffix": "ca"},
    {"id": "australia", "label": "Australia", "locale": "en-AU", "index_suffix": "au"},
    {"id": "mexico", "label": "Mexico", "locale": "es-MX", "index_suffix": "mx"},
    {"id": "spain", "label": "Spain", "locale": "es-ES", "index_suffix": "es"},
    {"id": "ireland", "label": "Ireland", "locale": "en-IE", "index_suffix": "ie"},
    {"id": "netherlands", "label": "Netherlands", "locale": "nl-NL", "index_suffix": "nl"},
    {"id": "singapore", "label": "Singapore", "locale": "en-SG", "index_suffix": "sg"},
    {"id": "argentina", "label": "Argentina", "locale": "es-AR", "index_suffix": "ar"},
]


def normalize_country(country_scope: Optional[str]) -> Optional[str]:
    """Normalize country_scope (code or name) to canonical value used in the index."""
    if not country_scope or not country_scope.strip():
        return None
    key = country_scope.strip().lower()
    return COUNTRY_NORMALIZE.get(key) or key


def get_index_suffix_for_country(canonical_country: str) -> Optional[str]:
    """Return index suffix for index-per-country pattern (e.g. 'us' for United States)."""
    return COUNTRY_INDEX_SUFFIX.get(canonical_country)
