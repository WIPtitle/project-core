import httpx


class AuthUser:
    def __init__(self, data: dict):
        self.username = data.get("username", "")
        self.permissions: list[str] = data.get("permissions", [])


class AuthClient:
    AUTH_URL = "http://project-auth:8000"

    async def get_authenticated_user(self, token: str | None) -> AuthUser | None:
        if not token:
            return None
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{self.AUTH_URL}/auth/user",
                    headers={"Authorization": token},
                    timeout=5.0
                )
            if r.status_code == 200:
                return AuthUser(r.json())
        except Exception:
            pass
        return None
