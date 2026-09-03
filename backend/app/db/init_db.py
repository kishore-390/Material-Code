from sqlalchemy import text

from app.db.session import engine


def init_extensions() -> None:
    """Ensure required PostgreSQL extensions exist. Called on startup and from migrations."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        conn.commit()
