import httpx
from fastapi import HTTPException

from app.config import settings
from app.schemas import ConnectionCredentials
from app.token_cache import token_cache


class MyDentaClient:
    def __init__(self, credentials: ConnectionCredentials) -> None:
        self.credentials = credentials
        host = credentials.host.strip("/")
        self.base_url = f"https://{host}/fmi/data/v1/databases/{credentials.database}"

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=settings.mydenta_request_timeout,
            verify=settings.mydenta_verify_ssl,
            http2=False,
        )

    async def _send(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            async with self._client() as client:
                return await client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=504,
                detail={"message": "MyDenta request timed out", "error": str(exc)},
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail={"message": "MyDenta connection failed", "error": str(exc)},
            ) from exc

    async def _get_token(self, *, force_refresh: bool = False) -> str:
        creds = self.credentials
        if not force_refresh:
            cached = await token_cache.get(creds.host, creds.database, creds.username)
            if cached:
                return cached

        response = await self._send(
            "POST",
            f"{self.base_url}/sessions",
            json={},
            auth=(creds.username, creds.password),
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "MyDenta authorization failed",
                    "status_code": response.status_code,
                    "body": response.text,
                },
            )

        payload = response.json()
        token = payload.get("response", {}).get("token")
        if not token:
            raise HTTPException(
                status_code=502,
                detail={"message": "MyDenta did not return a session token", "body": payload},
            )

        await token_cache.set(creds.host, creds.database, creds.username, token)
        return token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        retry_on_unauthorized: bool = True,
    ) -> dict:
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}

        response = await self._send(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            params=params,
        )

        if response.status_code == 401 and retry_on_unauthorized:
            await token_cache.invalidate(
                self.credentials.host,
                self.credentials.database,
                self.credentials.username,
            )
            token = await self._get_token(force_refresh=True)
            headers = {"Authorization": f"Bearer {token}"}
            response = await self._send(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                params=params,
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "MyDenta request failed",
                    "status_code": response.status_code,
                    "body": response.text,
                },
            )

        return response.json()

    async def run_script(self, script_name: str, script_param: str) -> dict:
        payload = await self._request(
            "GET",
            f"/layouts/time_free/script/{script_name}",
            params={"script.param": script_param},
        )
        response_data = payload.get("response", {})
        return {
            "script_result": response_data.get("scriptResult", ""),
            "script_error": str(response_data.get("scriptError", "")),
            "raw": payload,
        }

    async def logout(self, token: str | None = None) -> dict:
        session_token = token or await self._get_token()
        response = await self._send(
            "DELETE",
            f"{self.base_url}/sessions/{session_token}",
        )

        await token_cache.invalidate(
            self.credentials.host,
            self.credentials.database,
            self.credentials.username,
        )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "MyDenta logout failed",
                    "status_code": response.status_code,
                    "body": response.text,
                },
            )

        return response.json()
