import os

from sqlmodel import Session, create_engine, SQLModel
from app.database.database_connector import DatabaseConnector
from app.utils.read_credentials import read_credentials


class DatabaseConnectorImpl(DatabaseConnector):
    def __init__(self):
        credentials_file = os.getenv('PG_CREDENTIALS_FILE')
        credentials = read_credentials(credentials_file)

        self.session_instance = None
        self.engine = create_engine(
            f"postgresql://{credentials['POSTGRES_USER']}:{credentials['POSTGRES_PASSWORD']}@db:5432/{credentials['POSTGRES_DB']}",
            echo=True)

        SQLModel.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        if self.session_instance is None:
            self.session_instance = Session(self.engine)
        return self.session_instance