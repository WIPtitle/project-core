from abc import ABC, abstractmethod
from sqlmodel import Session


class DatabaseConnector(ABC):
    @abstractmethod
    def get_new_session(self) -> Session:
        pass
