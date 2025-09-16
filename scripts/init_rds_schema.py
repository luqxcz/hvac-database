import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from db.models import Base


def main() -> None:
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    dbname = os.getenv("DB_NAME", "thermolio")

    if not host or not user or not password:
        raise SystemExit("DB_HOST, DB_USER, and DB_PASSWORD env vars are required")

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=user,
        password=password,
        host=host,
        port=5432,
        database=dbname,
        query={"sslmode": "require"},
    )

    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)

    print("Schema created.")


if __name__ == "__main__":
    main()


