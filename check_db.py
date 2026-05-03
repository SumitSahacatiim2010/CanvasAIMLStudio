from sqlalchemy import create_engine, inspect
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://canvasml:canvasml_dev_2024@localhost:5432/canvasml")
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

schemas = inspector.get_schema_names()
print(f"Schemas: {schemas}")

if 'ml' in schemas:
    tables = inspector.get_table_names(schema='ml')
    print(f"Tables in 'ml' schema: {tables}")
else:
    print("'ml' schema not found.")
