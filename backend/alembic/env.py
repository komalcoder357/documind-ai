from alembic import context
from app.db import Base, engine
from app import models  # noqa: register tables

def run_migrations_online():
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=Base.metadata, render_as_batch=engine.dialect.name == "sqlite")
        with context.begin_transaction(): context.run_migrations()

run_migrations_online()
