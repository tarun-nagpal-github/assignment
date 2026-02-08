"""
OpenSearch search and facets for the company index.
Supports query understanding, semantic matching, and multi-country (Part Three).
"""
import os
from typing import Optional, List

from opensearchpy import OpenSearch

from query_understanding import understand_query
from regions import normalize_country, get_index_suffix_for_country

INDEX_NAME = "company"
INDEX_PATTERN_ENV = "OPENSEARCH_INDEX_PER_COUNTRY"  # when set, use company_{suffix} per country


def get_client(host: str, user: str, password: str) -> OpenSearch:
    return OpenSearch(
        hosts=[host],
        http_compress=True,
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False,
        http_auth=(user, password),
    )


def build_search_body(
    query: Optional[str] = None,
    industry: Optional[list] = None,
    size_range: Optional[str] = None,
    country: Optional[str] = None,
    locality: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    page: int = 1,
    size: int = 20,
    sort: str = "relevance",
    use_query_understanding: bool = True,
    country_scope: Optional[str] = None,
) -> dict:
    """Build OpenSearch request body: bool query + aggs for facets.
    When use_query_understanding is True, phrases like 'tech companies in california'
    are parsed into industry and location filters automatically.
    country_scope: restrict results to one country (localized view); normalized via regions.
    """
    must = []
    # Part Three: country_scope for localized search (normalize code/name -> index value)
    effective_country = country
    if country_scope and country is None:
        effective_country = normalize_country(country_scope)

    # Query understanding: parse natural language into filters when no explicit filters given
    parsed_industry_keywords = []
    parsed_location = None
    if use_query_understanding and query and query.strip():
        understood = understand_query(query)
        if understood["industry_keywords"] and industry is None:
            parsed_industry_keywords = understood["industry_keywords"]
        if understood["location"] and country is None and locality is None:
            parsed_location = understood["location"]

    # Free-text search (original query still used for name/industry/domain/locality match)
    if query and query.strip():
        must.append({
            "multi_match": {
                "query": query.strip(),
                "fields": ["name^2", "industry", "domain", "locality", "country"],
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        })

    filter_clauses = []
    # Explicit industry filter (exact terms)
    if industry:
        filter_clauses.append({"terms": {"industry.keyword": industry}})
    # Parsed industry from query understanding (match technology-related terms on industry text)
    elif parsed_industry_keywords:
        filter_clauses.append({
            "bool": {
                "should": [
                    {"match": {"industry": kw}}
                    for kw in parsed_industry_keywords
                ],
                "minimum_should_match": 1,
            }
        })
    if size_range:
        filter_clauses.append({"term": {"size_range": size_range}})
    if effective_country:
        filter_clauses.append({"term": {"country": effective_country}})
    if locality:
        filter_clauses.append({"match": {"locality": locality}})
    # Parsed location from query understanding (match on locality or country)
    elif parsed_location:
        filter_clauses.append({
            "bool": {
                "should": [
                    {"match": {"locality": parsed_location}},
                    {"match": {"country": parsed_location}},
                ],
                "minimum_should_match": 1,
            }
        })
    if year_min is not None:
        filter_clauses.append({"range": {"year_founded": {"gte": year_min}}})
    if year_max is not None:
        filter_clauses.append({"range": {"year_founded": {"lte": year_max}}})

    if filter_clauses:
        must.append({"bool": {"filter": filter_clauses}})

    bool_query = {"bool": {"must": must}} if must else {"match_all": {}}

    # Sort
    if sort == "name_asc":
        sort_spec = [{"name.keyword": "asc"}]
    elif sort == "name_desc":
        sort_spec = [{"name.keyword": "desc"}]
    elif sort == "size_desc":
        sort_spec = [{"current_employee_estimate": "desc"}, "_score"]
    elif sort == "size_asc":
        sort_spec = [{"current_employee_estimate": "asc"}, "_score"]
    elif sort == "year_desc":
        sort_spec = [{"year_founded": "desc"}, "_score"]
    elif sort == "year_asc":
        sort_spec = [{"year_founded": "asc"}, "_score"]
    else:
        sort_spec = ["_score"]

    from_idx = (page - 1) * size

    body = {
        "query": bool_query,
        "from": from_idx,
        "size": size,
        "sort": sort_spec,
        "aggs": {
            "industries": {"terms": {"field": "industry.keyword", "size": 100}},
            "countries": {"terms": {"field": "country", "size": 100}},
            "size_ranges": {"terms": {"field": "size_range", "size": 20}},
            "year_range": {
                "stats": {"field": "year_founded"},
            },
        },
    }
    return body


def resolve_search_indices(
    country_scope: Optional[str] = None,
    indices: Optional[List[str]] = None,
) -> str:
    """Resolve which index/indices to search. Returns index name or comma-separated list."""
    if indices:
        return ",".join(indices)
    if os.getenv(INDEX_PATTERN_ENV) and country_scope:
        canonical = normalize_country(country_scope)
        suffix = get_index_suffix_for_country(canonical) if canonical else None
        if suffix:
            return f"company_{suffix}"
    return INDEX_NAME


def search(
    client: OpenSearch,
    body: dict,
    index: Optional[str] = None,
    indices: Optional[List[str]] = None,
    country_scope: Optional[str] = None,
) -> dict:
    """Execute search. Use index or resolve from indices/country_scope."""
    target = index
    if target is None:
        target = resolve_search_indices(country_scope=country_scope, indices=indices)
    resp = client.search(index=target, body=body)
    return resp


def _format_number_by_locale(value: Optional[int], locale: Optional[str]) -> Optional[str]:
    """Format integer for display by locale (e.g. en-US: 1000 -> 1,000; de-DE: 1.000)."""
    if value is None:
        return None
    if not locale:
        return str(value)
    try:
        if locale.startswith("de") or locale.startswith("fr") or locale.startswith("pt") or locale.startswith("es"):
            return f"{value:,}".replace(",", ".")
        return f"{value:,}"
    except Exception:
        return str(value)


def _regional_employee_value(
    src: dict,
    field: str,
    region_suffix: Optional[str],
) -> Optional[int]:
    """Return region-specific employee value if available, else global. field is current_employee_estimate or total_employee_estimate."""
    if region_suffix:
        by_region = src.get(f"{field}_by_region") or {}
        if isinstance(by_region, dict) and region_suffix in by_region:
            val = by_region[region_suffix]
            if val is not None:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    pass
    return src.get(field)


def parse_response(
    resp: dict,
    locale: Optional[str] = None,
    country_scope: Optional[str] = None,
) -> dict:
    """Convert OpenSearch response to API shape: { hits, total, facets, meta }.
    Optionally format numbers by locale, include country_scope in meta, and use
    regional employee counts (current_employee_estimate_by_region, total_employee_estimate_by_region)
    when country_scope is set.
    """
    total = resp["hits"]["total"].get("value", resp["hits"]["total"])
    region_suffix = None
    if country_scope:
        canonical = normalize_country(country_scope)
        region_suffix = get_index_suffix_for_country(canonical) if canonical else None
    hits = []
    for h in resp["hits"].get("hits", []):
        src = h.get("_source", {})
        current_emp = _regional_employee_value(src, "current_employee_estimate", region_suffix)
        total_emp = _regional_employee_value(src, "total_employee_estimate", region_suffix)
        hit = {
            "id": src.get("id"),
            "name": src.get("name"),
            "domain": src.get("domain"),
            "industry": src.get("industry"),
            "size_range": src.get("size_range"),
            "locality": src.get("locality"),
            "country": src.get("country"),
            "year_founded": src.get("year_founded"),
            "current_employee_estimate": current_emp,
            "total_employee_estimate": total_emp,
            "linkedin_url": src.get("linkedin_url"),
        }
        if locale:
            hit["current_employee_estimate_formatted"] = _format_number_by_locale(
                current_emp, locale
            )
            hit["total_employee_estimate_formatted"] = _format_number_by_locale(
                total_emp, locale
            )
        hits.append(hit)

    aggs = resp.get("aggregations") or {}
    facets = {
        "industry": [{"value": b["key"], "count": b["doc_count"]} for b in aggs.get("industries", {}).get("buckets", [])],
        "country": [{"value": b["key"], "count": b["doc_count"]} for b in aggs.get("countries", {}).get("buckets", [])],
        "size_range": [{"value": b["key"], "count": b["doc_count"]} for b in aggs.get("size_ranges", {}).get("buckets", [])],
        "year": {},
    }
    yr = aggs.get("year_range", {})
    if yr:
        facets["year"] = {"min": yr.get("min"), "max": yr.get("max")}

    meta = {}
    if country_scope:
        meta["country_scope"] = country_scope
    if locale:
        meta["locale"] = locale

    return {"hits": hits, "total": total, "facets": facets, "meta": meta}
