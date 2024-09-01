from abc import abstractmethod

from fastapi import APIRouter


class RouterWrapper:
    def __init__(self, prefix: str):
        self.router = APIRouter(prefix=prefix)
        self._define_routes()

    @abstractmethod
    def _define_routes(self):
        pass

    def get_fastapi_router(self):
        return self.router