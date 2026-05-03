"""Metadata Catalog API — REST endpoints for data platform metadata.

Provides CRUD operations for sources, datasets, fields, and lineage.
Registered as a router on the gateway service.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from services.gateway.app.auth import CurrentUser, Role, get_current_user, require_roles
from services.gateway.app.database import get_db
from services.connectors.models import Source, Dataset, LineageEdge

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
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetResponse(BaseModel):
    id: str
    source_id: str
    name: str
    row_count: int | None
    size_bytes: int | None
    field_count: int
    tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


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
    created_at: datetime

    model_config = {"from_attributes": True}



# ── Source Endpoints ─────────────────────────────────────


@router.post("/sources", status_code=status.HTTP_201_CREATED, response_model=SourceResponse)
async def register_source(
    source: SourceCreate,
    user: CurrentUser = Depends(require_roles(Role.PLATFORM_ADMIN, Role.DATA_ENGINEER)),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Register a new data source."""
    new_source = Source(
        name=source.name,
        type=source.type,
        config=source.config,
        status="inactive",
        description=source.description,
        created_by=user.user_id,
    )
    session.add(new_source)
    await session.commit()
    await session.refresh(new_source)
    return new_source


@router.get("/sources", response_model=list[SourceResponse])
async def list_sources(
    user: CurrentUser = Depends(get_current_user),
    status_filter: str | None = Query(None, alias="status"),
    type_filter: str | None = Query(None, alias="type"),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """List all registered data sources."""
    stmt = select(Source)
    if status_filter:
        stmt = stmt.where(Source.status == status_filter)
    if type_filter:
        stmt = stmt.where(Source.type == type_filter)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Get a specific data source by ID."""
    source = await session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    return source


@router.post("/sources/{source_id}/test")
async def test_source_connectivity(
    source_id: str,
    user: CurrentUser = Depends(require_roles(Role.PLATFORM_ADMIN, Role.DATA_ENGINEER)),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Test connectivity to a data source."""
    source = await session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")

    # Use connector factory to test
    from services.connectors.base import ConnectorConfig
    from services.connectors.factory import create_connector

    try:
        config = ConnectorConfig(
            name=source.name,
            connector_type=source.type,
            config=source.config,
        )
        connector = create_connector(config)
        success, message = connector.test_connectivity()
        source.status = "active" if success else "error"
        await session.commit()
        return {"source_id": source_id, "connected": success, "message": message}
    except Exception as e:
        source.status = "error"
        await session.commit()
        return {"source_id": source_id, "connected": False, "message": str(e)}


@router.post("/sources/{source_id}/discover")
async def discover_schemas(
    source_id: str,
    user: CurrentUser = Depends(require_roles(Role.PLATFORM_ADMIN, Role.DATA_ENGINEER)),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Discover schemas/tables in a data source and register as datasets."""
    source = await session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")

    from services.connectors.base import ConnectorConfig
    from services.connectors.factory import create_connector

    config = ConnectorConfig(
        name=source.name,
        connector_type=source.type,
        config=source.config,
    )
    connector = create_connector(config)

    with connector:
        schemas = connector.discover_schemas()

    # Register discovered schemas as datasets
    registered = []
    for schema in schemas:
        dataset = Dataset(
            source_id=source_id,
            name=schema.name,
            row_count=schema.row_count,
            size_bytes=schema.size_bytes,
            fields=[
                {"name": f.name, "dtype": f.dtype, "nullable": f.nullable, "pii_classification": f.pii_classification}
                for f in schema.fields
            ],
            field_count=len(schema.fields),
            tags=[],
        )
        session.add(dataset)
        registered.append(dataset)

    await session.commit()

    return {"source_id": source_id, "datasets_discovered": len(registered), "datasets": [{"id": d.id, "name": d.name} for d in registered]}


# ── Dataset Endpoints ────────────────────────────────────


@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(
    user: CurrentUser = Depends(get_current_user),
    source_id: str | None = Query(None),
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """List all registered datasets."""
    stmt = select(Dataset)
    if source_id:
        stmt = stmt.where(Dataset.source_id == source_id)
    if search:
        stmt = stmt.where(Dataset.name.ilike(f"%{search}%"))
    
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Get dataset details including fields."""
    dataset = await session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    # Return as SQLAlchemy model instance, handled by FastAPI since response_model isn't specified...
    # Wait, the previous signature had no response_model. FastAPI defaults to auto. 
    # Let's map it to DatasetResponse to be safe.
    return DatasetResponse.model_validate(dataset)


# ── Lineage Endpoints ────────────────────────────────────


@router.post("/lineage", status_code=status.HTTP_201_CREATED, response_model=LineageEdgeResponse)
async def create_lineage_edge(
    edge: LineageEdgeCreate,
    user: CurrentUser = Depends(require_roles(Role.PLATFORM_ADMIN, Role.DATA_ENGINEER)),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Create a lineage relationship between datasets."""
    new_edge = LineageEdge(
        upstream_dataset_id=edge.upstream_dataset_id,
        downstream_dataset_id=edge.downstream_dataset_id,
        transform_type=edge.transform_type,
    )
    session.add(new_edge)
    await session.commit()
    await session.refresh(new_edge)
    return new_edge


@router.get("/lineage/{dataset_id}")
async def get_dataset_lineage(
    dataset_id: str,
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get lineage for a dataset — upstream sources, downstream consumers, or both."""
    result: dict[str, Any] = {"dataset_id": dataset_id}
    
    if direction in ("upstream", "both"):
        stmt = select(LineageEdge).where(LineageEdge.downstream_dataset_id == dataset_id)
        upstream_res = await session.execute(stmt)
        result["upstream"] = [LineageEdgeResponse.model_validate(e) for e in upstream_res.scalars().all()]
        
    if direction in ("downstream", "both"):
        stmt = select(LineageEdge).where(LineageEdge.upstream_dataset_id == dataset_id)
        downstream_res = await session.execute(stmt)
        result["downstream"] = [LineageEdgeResponse.model_validate(e) for e in downstream_res.scalars().all()]
        
    return result


# ── Search Endpoint ──────────────────────────────────────


@router.get("/search")
async def search_catalog(
    q: str = Query(..., min_length=1, description="Search query"),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Search across sources and datasets."""
    # Search sources
    stmt_src = select(Source).where(Source.name.ilike(f"%{q}%"))
    sources_res = await session.execute(stmt_src)
    matching_sources = sources_res.scalars().all()
    
    # Search datasets
    stmt_ds = select(Dataset).where(Dataset.name.ilike(f"%{q}%"))
    datasets_res = await session.execute(stmt_ds)
    matching_datasets = datasets_res.scalars().all()

    return {
        "query": q,
        "sources": [SourceResponse.model_validate(s) for s in matching_sources],
        "datasets": [DatasetResponse.model_validate(d) for d in matching_datasets],
        "total_results": len(matching_sources) + len(matching_datasets),
    }
