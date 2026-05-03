import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from services.gateway.app.database import Base, get_db
from services.gateway.app.main import app
from services.gateway.app.auth import get_current_user, Role, CurrentUser
from services.connectors.catalog_api import SourceResponse, DatasetResponse, LineageEdgeResponse
from services.connectors.base import BaseConnector, SchemaInfo, FieldInfo, ConnectorStatus

# Use local postgres container
DATABASE_URL = "postgresql+asyncpg://canvasml:canvasml_dev_2024@localhost:5432/canvasml"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    
    # Patch the global engine in database module
    import services.gateway.app.database as db_module
    db_module.engine = engine
    
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(test_engine):
    TestingSessionLocal = async_sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=test_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    # Patch the global sessionmaker in database module
    import services.gateway.app.database as db_module
    db_module.AsyncSessionLocal = TestingSessionLocal
    
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture(autouse=True)
async def setup_overrides(db_session):
    def override_get_db_sync():
        # This is tricky because get_db is an async generator
        pass
    
    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return CurrentUser(user_id="test-user", email="test@example.com", role=Role.PLATFORM_ADMIN)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.clear()

class MockConnector(BaseConnector):
    def validate_config(self): return True, []
    def test_connectivity(self): return True, "Connected"
    def discover_schemas(self):
        return [
            SchemaInfo(
                name="test_table",
                fields=[FieldInfo(name="id", dtype="int", nullable=False)],
                row_count=100,
                size_bytes=1024
            )
        ]
    def extract(self, *args, **kwargs): pass
    def connect(self): pass
    def disconnect(self): pass

@pytest.fixture(autouse=True)
def patch_registry(monkeypatch):
    from services.connectors.factory import CONNECTOR_REGISTRY
    monkeypatch.setitem(CONNECTOR_REGISTRY, "mock", MockConnector)

@pytest.mark.asyncio
async def test_catalog_lifecycle(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register Source
        resp = await ac.post(
            "/api/v1/catalog/sources",
            json={
                "name": "Integration Test Source",
                "type": "mock",
                "config": {"key": "val"},
                "description": "persisted metadata test"
            }
        )
        assert resp.status_code == 201
        source_id = resp.json()["id"]

        # 2. List Sources
        resp = await ac.get("/api/v1/catalog/sources")
        assert resp.status_code == 200
        sources = resp.json()
        assert any(s["id"] == source_id for s in sources)

        # 3. Discover Datasets
        resp = await ac.post(f"/api/v1/catalog/sources/{source_id}/discover")
        assert resp.status_code == 200
        discovery_data = resp.json()
        assert discovery_data["datasets_discovered"] == 1
        dataset_id = discovery_data["datasets"][0]["id"]

        # 4. List Datasets
        resp = await ac.get("/api/v1/catalog/datasets")
        assert resp.status_code == 200
        datasets = resp.json()
        assert any(d["id"] == dataset_id for d in datasets)

        # 5. Create Lineage
        # Create another dataset for lineage
        resp = await ac.post(
            "/api/v1/catalog/sources",
            json={"name": "Source 2", "type": "mock", "config": {}}
        )
        source2_id = resp.json()["id"]
        resp = await ac.post(f"/api/v1/catalog/sources/{source2_id}/discover")
        dataset2_id = resp.json()["datasets"][0]["id"]

        resp = await ac.post(
            "/api/v1/catalog/lineage",
            json={
                "upstream_dataset_id": dataset_id,
                "downstream_dataset_id": dataset2_id,
                "transform_type": "etl"
            }
        )
        assert resp.status_code == 201
        
        # 6. Get Lineage
        resp = await ac.get(f"/api/v1/catalog/lineage/{dataset2_id}?direction=upstream")
        assert resp.status_code == 200
        lineage = resp.json()
        assert len(lineage["upstream"]) == 1
        assert lineage["upstream"][0]["upstream_dataset_id"] == dataset_id
