"""Submit catalog changes for review through GitHub pull requests."""

import json
from uuid import uuid4

from .catalog import add_application
from .config import Settings
from .github_client import GitHubClient, dumps_catalog
from .models import (
    OAuth2ApplicationRequest,
    OidcApplicationRequest,
    PullRequestResult,
    SamlApplicationRequest,
)


async def _create_application_pr(
    request: SamlApplicationRequest | OidcApplicationRequest | OAuth2ApplicationRequest,
    settings: Settings,
    *,
    app_kind: str,
    catalog_path: str,
) -> PullRequestResult:
    branch = f"onboard/{app_kind}-{request.key}-{uuid4().hex[:8]}"
    async with GitHubClient(
        owner=settings.github_owner,
        repo=settings.github_repo,
        token=settings.github_token,
        api_url=settings.github_api_url,
        api_version=settings.github_api_version,
    ) as github:
        # Detect duplicate keys before creating a branch to avoid orphan refs.
        base_sha = await github.get_branch_sha(settings.github_base_branch)
        repo_file = await github.get_file(catalog_path, base_sha)
        catalog = json.loads(repo_file.content)
        updated = add_application(catalog, request)
        await github.create_branch(branch, base_sha)
        await github.update_file(
            path=catalog_path,
            branch=branch,
            old_sha=repo_file.sha,
            content=dumps_catalog(updated),
            message=f"feat(okta): onboard {app_kind.upper()} app {request.key}",
        )
        bookmark_line = (
            f"- **Include bookmark:** `{request.include_bookmark}`\n"
            if isinstance(request, OidcApplicationRequest)
            else ""
        )
        pr_number, pr_url = await github.create_pull_request(
            title=f"Onboard Okta {app_kind.upper()} application: {request.label}",
            head=branch,
            base=settings.github_base_branch,
            body=(
                f"Automated Okta {app_kind.upper()} application onboarding request.\n\n"
                f"- **Key:** `{request.key}`\n"
                f"- **Owner:** `{request.owner}`\n"
                f"- **Environment:** `{request.environment}`\n"
                f"- **SAL:** `{request.sal or 'not specified'}`\n"
                f"- **Requested by:** `{request.requested_by}`\n"
                f"{bookmark_line}\n"
                "The Terraform PR workflow should validate the catalog and run `terraform plan`."
            ),
        )
    return PullRequestResult(
        application=request.key,
        branch=branch,
        pull_request_number=pr_number,
        pull_request_url=pr_url,
    )


async def create_saml_application_pr(
    request: SamlApplicationRequest, settings: Settings
) -> PullRequestResult:
    return await _create_application_pr(
        request, settings, app_kind="saml", catalog_path=settings.github_catalog_path
    )


async def create_oidc_application_pr(
    request: OidcApplicationRequest, settings: Settings
) -> PullRequestResult:
    return await _create_application_pr(
        request, settings, app_kind="oidc", catalog_path=settings.github_oauth_catalog_path
    )


async def create_oauth_application_pr(
    request: OAuth2ApplicationRequest, settings: Settings
) -> PullRequestResult:
    return await _create_application_pr(
        request, settings, app_kind="oauth2", catalog_path=settings.github_oauth_catalog_path
    )
