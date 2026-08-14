from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import require_admin
from app.core.exceptions import BusinessValidationError
from app.models import User
from app.schemas.common import DataResponse
from app.schemas.web_search import (
    WebSearchProviderStatusResponse,
    WebSearchResultRead,
    WebSearchTestRequest,
    WebSearchTestResponse,
)
from app.web_search.errors import WebSearchError
from app.web_search.service import WebSearchService

router = APIRouter(prefix="/web-search", tags=["Web Search"])


@router.get(
    "/provider-status",
    response_model=DataResponse[WebSearchProviderStatusResponse],
)
async def provider_status(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
) -> DataResponse[WebSearchProviderStatusResponse]:
    _ = current_user
    manager = request.app.state.web_search_provider_manager
    health = manager.configuration_health()
    return DataResponse[WebSearchProviderStatusResponse](
        data=WebSearchProviderStatusResponse(
            provider=health.provider,
            display_name=health.display_name,
            status=health.status,
            configured=health.configured,
            external_allowed=health.external_allowed,
            connectivity_checked=health.connectivity_checked,
            message=health.message,
            request_id=health.request_id,
        ),
        meta=None,
    )


@router.post(
    "/test",
    response_model=DataResponse[WebSearchTestResponse],
)
async def test_search(
    request: Request,
    payload: WebSearchTestRequest,
    current_user: Annotated[User, Depends(require_admin)],
) -> DataResponse[WebSearchTestResponse]:
    _ = current_user
    manager = request.app.state.web_search_provider_manager
    service = WebSearchService(
        settings=manager.settings,
        provider_factory=manager.get_provider,
    )
    try:
        results = await service.search(query=payload.query)
    except WebSearchError as exc:
        raise BusinessValidationError(exc.safe_message) from exc
    return DataResponse[WebSearchTestResponse](
        data=WebSearchTestResponse(
            provider=results.provider,
            query=results.query,
            result_count=len(results.results),
            results=[
                WebSearchResultRead(
                    title=result.title,
                    source_url=result.url,
                    snippet=result.snippet,
                    provider=result.provider,
                    rank=result.rank,
                )
                for result in results.results
            ],
        ),
        meta=None,
    )
