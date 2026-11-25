from collections.abc import Awaitable
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from .config import Settings, get_settings
from .github_client import GitHubApiError
from .models import (
    OAuth2ApplicationRequest,
    OidcApplicationRequest,
    PullRequestResult,
    SamlApplicationRequest,
)
from .service import (
    create_oauth_application_pr,
    create_oidc_application_pr,
    create_saml_application_pr,
)

app = FastAPI(
    title="GMF Okta Application Intake API",
    version="0.2.0",
    description="Validates SAML, OIDC, and OAuth 2.0 requests and opens Terraform pull requests.",
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/okta/saml-applications/validate")
async def validate_saml_application(request: SamlApplicationRequest) -> dict:
    return {"valid": True, "application": request.key, "normalized": request.model_dump(mode="json")}


@app.post("/v1/okta/oidc-applications/validate")
async def validate_oidc_application(request: OidcApplicationRequest) -> dict:
    return {"valid": True, "application": request.key, "normalized": request.model_dump(mode="json")}


@app.post("/v1/okta/oauth-applications/validate")
async def validate_oauth_application(request: OAuth2ApplicationRequest) -> dict:
    return {"valid": True, "application": request.key, "normalized": request.model_dump(mode="json")}


async def _submit(submission: Awaitable[PullRequestResult]) -> PullRequestResult:
    try:
        return await submission
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GitHubApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/v1/okta/saml-applications", response_model=PullRequestResult, status_code=201)
async def submit_saml_application(
    request: SamlApplicationRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PullRequestResult:
    return await _submit(create_saml_application_pr(request, settings))


@app.post("/v1/okta/oidc-applications", response_model=PullRequestResult, status_code=201)
async def submit_oidc_application(
    request: OidcApplicationRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PullRequestResult:
    return await _submit(create_oidc_application_pr(request, settings))


@app.post("/v1/okta/oauth-applications", response_model=PullRequestResult, status_code=201)
async def submit_oauth_application(
    request: OAuth2ApplicationRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PullRequestResult:
    return await _submit(create_oauth_application_pr(request, settings))
