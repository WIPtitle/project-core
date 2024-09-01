from abc import abstractmethod, ABC

from sqlmodel import Session


class DatabaseConnector(ABC):
    @abstractmethod
    def get_session(self) -> Session:
        pass