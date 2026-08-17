import base64
import json
from dataclasses import dataclass
from urllib.parse import quote

import httpx


class GitHubApiError(RuntimeError):
    pass


@dataclass
class RepositoryFile:
    content: str
    sha: str


class GitHubClient:
    def __init__(
        self,
        *,
        owner: str,
        repo: str,
        token: str,
        api_url: str = "https://api.github.com",
        api_version: str = "2026-03-10",
        timeout: float = 30.0,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self.base = api_url.rstrip("/")
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": api_version,
                "User-Agent": "gmf-okta-saml-api",
            },
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        response = await self.client.request(method, f"{self.base}{path}", **kwargs)
        if response.is_error:
            detail = response.text[:1500]
            raise GitHubApiError(f"GitHub API {method} {path} failed: {response.status_code}: {detail}")
        return response

    async def get_branch_sha(self, branch: str) -> str:
        encoded = quote(branch, safe="")
        response = await self._request(
            "GET", f"/repos/{self.owner}/{self.repo}/git/ref/heads/{encoded}"
        )
        return response.json()["object"]["sha"]

    async def create_branch(self, branch: str, sha: str) -> None:
        await self._request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": sha},
        )

    async def get_file(self, path: str, ref: str) -> RepositoryFile:
        encoded_path = quote(path, safe="/")
        response = await self._request(
            "GET",
            f"/repos/{self.owner}/{self.repo}/contents/{encoded_path}",
            params={"ref": ref},
        )
        payload = response.json()
        raw = base64.b64decode(payload["content"].replace("\n", "")).decode("utf-8")
        return RepositoryFile(content=raw, sha=payload["sha"])

    async def update_file(
        self,
        *,
        path: str,
        branch: str,
        old_sha: str,
        content: str,
        message: str,
    ) -> None:
        encoded_path = quote(path, safe="/")
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
        await self._request(
            "PUT",
            f"/repos/{self.owner}/{self.repo}/contents/{encoded_path}",
            json={
                "message": message,
                "content": encoded_content,
                "sha": old_sha,
                "branch": branch,
            },
        )

    async def create_pull_request(
        self, *, title: str, head: str, base: str, body: str
    ) -> tuple[int, str]:
        response = await self._request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/pulls",
            json={"title": title, "head": head, "base": base, "body": body},
        )
        payload = response.json()
        return payload["number"], payload["html_url"]


def dumps_catalog(catalog: dict) -> str:
    return json.dumps(catalog, indent=2, sort_keys=False) + "\n"
