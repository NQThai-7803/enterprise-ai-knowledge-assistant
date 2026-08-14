from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WebSearchProviderStatusResponse(BaseModel):
    provider: str
    display_name: str | None
    status: str
    configured: bool
    external_allowed: bool
    connectivity_checked: bool
    message: str | None
    request_id: str | None


class WebSearchTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=4000)


class WebSearchResultRead(BaseModel):
    title: str
    source_url: str
    snippet: str
    provider: str
    rank: int = Field(ge=1)


class WebSearchTestResponse(BaseModel):
    provider: str
    query: str
    result_count: int = Field(ge=0)
    results: list[WebSearchResultRead]
