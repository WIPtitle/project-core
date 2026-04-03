from fastapi import APIRouter


class RouterWrapper:
    def __init__(self, prefix: str):
        self.router = APIRouter(prefix=prefix)
        self._define_routes()

    def _define_routes(self):
        raise NotImplementedError

    def get_fastapi_router(self) -> APIRouter:
        return self.router
