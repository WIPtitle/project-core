import json
import os
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session
from app.database.database_connector import DatabaseConnector
# Import all models so they register with SQLModel.metadata
from app.models.irrigation_models import (
    ValveServer, IrrigationZone, IrrigationSetup, SetupZoneSchedule, SetupDateRange
)
from app.database.migration_runner import MigrationRunner


class DatabaseConnectorImpl(DatabaseConnector):
    def __init__(self):
        credentials_file = os.environ.get("PG_CREDENTIALS_FILE", "/shared/pg_credentials.json")
        with open(credentials_file) as f:
            creds = json.load(f)
        db_url = (
            f"postgresql://{creds['user']}:{creds['password']}"
            f"@db:5432/{creds['dbname']}"
        )
        self._engine = create_engine(db_url)
        SQLModel.metadata.create_all(self._engine)
        MigrationRunner(self._engine).run()

    def get_new_session(self) -> Session:
        return Session(self._engine)
