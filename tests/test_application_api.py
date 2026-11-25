import base64
import json
from pathlib import Path

import httpx
import pytest

from app.config import Settings, get_settings
from app.github_client import GitHubClient
from app.main import app

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "route, example, protocol, catalog_path",
    [
        ("saml", "saml-app-request.json", None, "custom/saml.json"),
        ("oauth", "oauth-app-request.json", "oauth2", "custom/oauth.json"),
        ("oauth", "oauth-web-app-request.json", "oauth2", "custom/oauth.json"),
        ("oidc", "oidc-app-request.json", "oidc", "custom/oauth.json"),
    ],
)
async def test_validate_and_submit_application(monkeypatch, route, example, protocol, catalog_path):
    settings = Settings(
        github_owner="test-org",
        github_repo="test-terraform",
        github_token="test-token",
        github_base_branch="review",
        github_catalog_path="custom/saml.json",
        github_oauth_catalog_path="custom/oauth.json",
    )
    monkeypatch.setitem(app.dependency_overrides, get_settings, lambda: settings)

    operations = []
    contents_path = f"/repos/test-org/test-terraform/contents/{catalog_path}"

    async def github_request(self, method, path, **kwargs):
        operations.append((method, path, kwargs))
        if path.endswith("/git/ref/heads/review"):
            return httpx.Response(200, json={"object": {"sha": "base-sha"}})
        if method == "GET" and path == contents_path:
            content = base64.b64encode(b'{"applications":{"existing":{}}}').decode()
            return httpx.Response(200, json={"content": content, "sha": "file-sha"})
        if path.endswith("/pulls"):
            return httpx.Response(201, json={"number": 3, "html_url": "https://example.com/pull/3"})
        return httpx.Response(201)

    monkeypatch.setattr(GitHubClient, "_request", github_request)
    payload = json.loads((EXAMPLES / example).read_text(encoding="utf-8"))
    endpoint = f"/v1/okta/{route}-applications"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        validation = await client.post(f"{endpoint}/validate", json=payload)
        assert validation.status_code == 200, validation.text
        assert validation.json()["application"] == payload["key"]
        assert operations == []

        submission = await client.post(endpoint, json=payload)

    assert submission.status_code == 201, submission.text
    result = submission.json()
    assert result["pull_request_number"] == 3
    assert result["branch"].startswith(f"onboard/{protocol or route}-")

    _, read, branch, write, pr = operations
    assert read == ("GET", contents_path, {"params": {"ref": "base-sha"}})
    assert branch[2]["json"] == {"ref": f"refs/heads/{result['branch']}", "sha": "base-sha"}
    assert write[:2] == ("PUT", contents_path)
    assert write[2]["json"]["sha"] == "file-sha"
    catalog = json.loads(base64.b64decode(write[2]["json"]["content"]))
    assert catalog["applications"]["existing"] == {}
    entry = catalog["applications"][payload["key"]]
    assert "key" not in entry
    if protocol is None:
        assert "protocol" not in entry
        assert entry == {k: v for k, v in validation.json()["normalized"].items() if k != "key"}
    else:
        assert entry["protocol"] == protocol
    assert pr[2]["json"]["base"] == "review"
    assert pr[2]["json"]["head"] == result["branch"]
