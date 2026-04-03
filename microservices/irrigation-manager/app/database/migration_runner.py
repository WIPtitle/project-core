import os
from sqlalchemy import text


class MigrationRunner:
    MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

    def __init__(self, engine):
        self._engine = engine

    def run(self):
        with self._engine.connect() as conn:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS irrigation_migration_version "
                "(version VARCHAR PRIMARY KEY)"
            ))
            conn.commit()
            applied = {
                row[0] for row in conn.execute(
                    text("SELECT version FROM irrigation_migration_version")
                )
            }
            files = sorted(f for f in os.listdir(self.MIGRATIONS_DIR) if f.endswith(".sql"))
            for fname in files:
                version = fname.replace(".sql", "")
                if version not in applied:
                    with open(os.path.join(self.MIGRATIONS_DIR, fname)) as f:
                        sql = f.read()
                    conn.execute(text(sql))
                    conn.execute(
                        text("INSERT INTO irrigation_migration_version VALUES (:v)"),
                        {"v": version}
                    )
                    conn.commit()
