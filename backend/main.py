"""
CompanySearch API: search and tags.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List

from regions import SUPPORTED_REGIONS
from search_service import build_search_body, get_client, parse_response, search
from tags_store import create_tag, delete_tag, get_tags

# Load .env from project root (parent of backend/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "https://localhost:9201")
OPENSEARCH_USER = os.getenv("OPENSEARCH_USER", "admin")
OPENSEARCH_PASSWORD = os.getenv(
    "OPENSEARCH_INITIAL_ADMIN_PASSWORD",
    os.getenv("OPENSEARCH_PASSWORD", ""),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.opensearch = get_client(OPENSEARCH_HOST, OPENSEARCH_USER, OPENSEARCH_PASSWORD) if OPENSEARCH_PASSWORD else None
    yield
    app.state.opensearch = None


app = FastAPI(title="CompanySearch API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response models ---

class SearchFilters(BaseModel):
    industry: Optional[list[str]] = None
    size_range: Optional[str] = None
    country: Optional[str] = None
    locality: Optional[str] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None


class SearchRequest(BaseModel):
    query: Optional[str] = None
    filters: Optional[SearchFilters] = None
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    sort: str = "relevance"  # relevance | name_asc | name_desc | size_asc | size_desc | year_asc | year_desc
    # Part Three: multi-country / localized
    locale: Optional[str] = None  # e.g. en-US, de-DE; used for number formatting in response
    country_scope: Optional[str] = None  # restrict to one country (code or name); normalized via regions
    indices: Optional[List[str]] = None  # explicit index names to search (overrides country_scope index)


class CreateTagRequest(BaseModel):
    name: str
    filter_snapshot: Optional[dict] = None


# --- Endpoints ---

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/regions")
def get_regions():
    """Return supported regions for multi-country search (id, label, locale, index_suffix)."""
    return {"regions": SUPPORTED_REGIONS}


@app.post("/search")
def post_search(req: SearchRequest):
    if not app.state.opensearch:
        raise HTTPException(status_code=503, detail="OpenSearch not configured")
    f = req.filters or SearchFilters()
    body = build_search_body(
        query=req.query,
        industry=f.industry,
        size_range=f.size_range,
        country=f.country,
        locality=f.locality,
        year_min=f.year_min,
        year_max=f.year_max,
        page=req.page,
        size=req.size,
        sort=req.sort,
        country_scope=req.country_scope,
    )
    resp = search(
        app.state.opensearch,
        body,
        country_scope=req.country_scope,
        indices=req.indices,
    )
    return parse_response(resp, locale=req.locale, country_scope=req.country_scope)


@app.get("/tags/{user_id}")
def list_tags(user_id: str):
    return {"tags": get_tags(user_id)}


@app.post("/tags/{user_id}")
def add_tag(user_id: str, body: CreateTagRequest):
    tag = create_tag(user_id, body.name, body.filter_snapshot)
    return tag


@app.delete("/tags/{user_id}/{tag_id}")
def remove_tag(user_id: str, tag_id: str):
    if not delete_tag(user_id, tag_id):
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
