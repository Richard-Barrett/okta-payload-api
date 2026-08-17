import json
from uuid import uuid4

from .catalog import add_application
from .config import Settings
from .github_client import GitHubClient, dumps_catalog
from .models import PullRequestResult, SamlApplicationRequest


async def create_saml_application_pr(
    request: SamlApplicationRequest, settings: Settings
) -> PullRequestResult:
    branch = f"onboard/saml-{request.key}-{uuid4().hex[:8]}"

    async with GitHubClient(
        owner=settings.github_owner,
        repo=settings.github_repo,
        token=settings.github_token,
        api_url=settings.github_api_url,
        api_version=settings.github_api_version,
    ) as github:
        # Validate against the current base branch before creating a new branch.
        # This avoids leaving an orphan branch behind for duplicate/invalid requests.
        base_sha = await github.get_branch_sha(settings.github_base_branch)
        repo_file = await github.get_file(
            settings.github_catalog_path, settings.github_base_branch
        )
        catalog = json.loads(repo_file.content)
        updated = add_application(catalog, request)

        await github.create_branch(branch, base_sha)
        await github.update_file(
            path=settings.github_catalog_path,
            branch=branch,
            old_sha=repo_file.sha,
            content=dumps_catalog(updated),
            message=f"feat(okta): onboard SAML app {request.key}",
        )

        pr_number, pr_url = await github.create_pull_request(
            title=f"Onboard Okta SAML application: {request.label}",
            head=branch,
            base=settings.github_base_branch,
            body=(
                "Automated Okta SAML application onboarding request.\n\n"
                f"- **Key:** `{request.key}`\n"
                f"- **Owner:** `{request.owner}`\n"
                f"- **Environment:** `{request.environment}`\n"
                f"- **SAL:** `{request.sal or 'not specified'}`\n"
                f"- **Requested by:** `{request.requested_by}`\n\n"
                "The Terraform PR workflow should validate the catalog and run `terraform plan`."
            ),
        )

    return PullRequestResult(
        application=request.key,
        branch=branch,
        pull_request_number=pr_number,
        pull_request_url=pr_url,
    )
