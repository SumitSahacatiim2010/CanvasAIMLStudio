"""Metadata Catalog API — REST endpoints for data platform metadata.

Provides CRUD operations for sources, datasets, fields, and lineage.
Registered as a router on the gateway service.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from services.gateway.app.auth import CurrentUser, Role, get_current_user, require_roles

router = APIRouter(prefix="/api/v1/catalog", tags=["Data Catalog"])


# ── Pydantic Models ──────────────────────────────────────


class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., description="Connector type: postgres, s3, csv, etc.")
    config: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class SourceResponse(BaseModel):
    id: str
    name: str
    type: str
    status: str
    description: str
    created_at: str


class DatasetResponse(BaseModel):
    id: str
    source_id: str
    name: str
    row_count: int | None
    size_bytes: int | None
    field_count: int
    tags: list[str]
    created_at: str


class FieldResponse(BaseModel):
    name: str
    dtype: str
    nullable: bool
    pii_classification: str


class LineageEdgeCreate(BaseModel):
    upstream_dataset_id: str
    downstream_dataset_id: str
    transform_type: str = "derived"  # etl, federation, derived


class LineageEdgeResponse(BaseModel):
    id: str
    upstream_dataset_id: str
    downstream_dataset_id: str
    transform_type: str
    created_at: str


# ── In-Memory Store (replaced by DB in Phase 1.5) ───────

_sources: dict[str, dict[str, Any]] = {}
_datasets: dict[str, dict[str, Any]] = {}
_lineage: list[dict[str, Any]] = []
_id_counter = 0


def _next_id() -> str:
    global _id_counter
    _id_counter += 1
    return f"src-{_id_counter:04d}"


# ── Source Endpoints ─────────────────────────────────────


@router.post("/sources", status_code=status.HTTP_201_CREATED, response_model=SourceResponse)
async def register_source(
    source: SourceCreate,
    user: CurrentUser = Depends(require_roles(Role.PLATFORM_ADMIN, Role.DATA_ENGINEER)),
) -> dict[str, Any]:
    """Register a new data source."""
    source_id = _next_id()
    record = {
        "id": source_id,
        "name": source.name,
        "type": source.type,
        "config": source.config,
        "status": "inactive",
        "description": source.description,
        "created_by": user.user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _sources[source_id] = record
    return record


@router.get("/sources", response_model=list[SourceResponse])
async def list_sources(
    user: CurrentUser = Depends(get_current_user),
    status_filter: str | None = Query(None, alias="status"),
    type_filter: str | None = Query(None, alias="type"),
) -> list[dict[str, Any]]:
    """List all registered data sources."""
    results = list(_sources.values())
    if status_filter:
        results = [s for s in results if s["status"] == status_filter]
    if type_filter:
        results = [s for s in results if s["type"] == type_filter]
    return results


@router.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a specific data source by ID."""
    if source_id not in _sources:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    return _sources[source_id]


@router.post("/sources/{source_id}/test")
async def test_source_connectivity(
    source_id: str,
    user: CurrentUser = Depends(require_roles(Role.PLATFORM_ADMIN, Role.DATA_ENGINEER)),
) -> dict[str, Any]:
    """Test connectivity to a data source."""
    if source_id not in _sources:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")

    source = _sources[source_id]

    # Use connector factory to test
    from services.connectors.base import ConnectorConfig
    from services.connectors.factory import create_connector

    try:
        config = ConnectorConfig(
            name=source["name"],
            connector_type=source["type"],
            config=source["config"],
        )
        connector = create_connector(config)
        success, message = connector.test_connectivity()
        source["status"] = "active" if success else "error"
        return {"source_id": source_id, "connected": success, "message": message}
    except Exception as e:
        source["status"] = "error"
        return {"source_id": source_id, "connected": False, "message": str(e)}


@router.post("/sources/{source_id}/discover")
async def discover_schemas(
    source_id: str,
    user: CurrentUser = Depends(require_roles(Role.PLATFORM_ADMIN, Role.DATA_ENGINEER)),
) -> dict[str, Any]:
    """Discover schemas/tables in a data source and register as datasets."""
    if source_id not in _sources:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")

    source = _sources[source_id]

    from services.connectors.base import ConnectorConfig
    from services.connectors.factory import create_connector

    config = ConnectorConfig(
        name=source["name"],
        connector_type=source["type"],
        config=source["config"],
    )
    connector = create_connector(config)

    with connector:
        schemas = connector.discover_schemas()

    # Register discovered schemas as datasets
    registered = []
    for schema in schemas:
        ds_id = _next_id()
        dataset = {
            "id": ds_id,
            "source_id": source_id,
            "name": schema.name,
            "row_count": schema.row_count,
            "size_bytes": schema.size_bytes,
            "fields": [
                {"name": f.name, "dtype": f.dtype, "nullable": f.nullable, "pii_classification": f.pii_classification}
                for f in schema.fields
            ],
            "field_count": len(schema.fields),
            "tags": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _datasets[ds_id] = dataset
        registered.append(dataset)

    return {"source_id": source_id, "datasets_discovered": len(registered), "datasets": registered}


# ── Dataset Endpoints ────────────────────────────────────


@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(
    user: CurrentUser = Depends(get_current_user),
    source_id: str | None = Query(None),
    search: str | None = Query(None),
) -> list[dict[str, Any]]:
    """List all registered datasets."""
    results = list(_datasets.values())
    if source_id:
        results = [d for d in results if d["source_id"] == source_id]
    if search:
        results = [d for d in results if search.lower() in d["name"].lower()]
    return results


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get dataset details including fields."""
    if dataset_id not in _datasets:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return _datasets[dataset_id]


# ── Lineage Endpoints ────────────────────────────────────


@router.post("/lineage", status_code=status.HTTP_201_CREATED, response_model=LineageEdgeResponse)
async def create_lineage_edge(
    edge: LineageEdgeCreate,
    user: CurrentUser = Depends(require_roles(Role.PLATFORM_ADMIN, Role.DATA_ENGINEER)),
) -> dict[str, Any]:
    """Create a lineage relationship between datasets."""
    record = {
        "id": _next_id(),
        "upstream_dataset_id": edge.upstream_dataset_id,
        "downstream_dataset_id": edge.downstream_dataset_id,
        "transform_type": edge.transform_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _lineage.append(record)
    return record


@router.get("/lineage/{dataset_id}")
async def get_dataset_lineage(
    dataset_id: str,
    direction: str = Query("both", regex="^(upstream|downstream|both)$"),
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get lineage for a dataset — upstream sources, downstream consumers, or both."""
    upstream = [e for e in _lineage if e["downstream_dataset_id"] == dataset_id]
    downstream = [e for e in _lineage if e["upstream_dataset_id"] == dataset_id]

    result: dict[str, Any] = {"dataset_id": dataset_id}
    if direction in ("upstream", "both"):
        result["upstream"] = upstream
    if direction in ("downstream", "both"):
        result["downstream"] = downstream
    return result


# ── Search Endpoint ──────────────────────────────────────


@router.get("/search")
async def search_catalog(
    q: str = Query(..., min_length=1, description="Search query"),
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Search across sources and datasets."""
    query_lower = q.lower()

    matching_sources = [s for s in _sources.values() if query_lower in s["name"].lower()]
    matching_datasets = [d for d in _datasets.values() if query_lower in d["name"].lower()]

    return {
        "query": q,
        "sources": matching_sources,
        "datasets": matching_datasets,
        "total_results": len(matching_sources) + len(matching_datasets),
    }
