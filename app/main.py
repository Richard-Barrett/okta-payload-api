from fastapi import Depends, FastAPI, HTTPException

from .config import Settings, get_settings
from .github_client import GitHubApiError
from .models import PullRequestResult, SamlApplicationRequest
from .service import create_saml_application_pr

app = FastAPI(
    title="GMF Okta SAML Application Intake API",
    version="0.1.0",
    description="Validates SAML app requests and raises a PR against the Terraform catalog.",
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/okta/saml-applications/validate")
async def validate_saml_application(request: SamlApplicationRequest) -> dict:
    return {"valid": True, "application": request.key, "normalized": request.model_dump(mode="json")}


@app.post("/v1/okta/saml-applications", response_model=PullRequestResult, status_code=201)
async def submit_saml_application(
    request: SamlApplicationRequest,
    settings: Settings = Depends(get_settings),
) -> PullRequestResult:
    try:
        return await create_saml_application_pr(request, settings)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GitHubApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
