# GMF Okta SAML Intake API

FastAPI service that accepts an Okta SAML application request, validates it, updates the flat application catalog in the Terraform repository, and opens a GitHub pull request. It **does not** have Okta credentials and it **does not** run `terraform apply`.

## Flow

```text
Caller -> FastAPI -> GitHub branch -> catalog/saml_apps.json -> Pull Request
                                                      |
                                                      v
                                             Terraform CI / Okta
```

## Local Mac setup

```bash
cp .env.example .env
# edit .env

docker compose up --build
```

Open `http://localhost:8000/docs`.

Validate a request without changing GitHub:

```bash
curl -sS -X POST http://localhost:8000/v1/okta/saml-applications/validate \
  -H 'Content-Type: application/json' \
  --data @examples/saml-app-request.json
```

Create a PR:

```bash
curl -sS -X POST http://localhost:8000/v1/okta/saml-applications \
  -H 'Content-Type: application/json' \
  --data @examples/saml-app-request.json
```

## GitHub token permissions

For local development, use a fine-grained PAT restricted to the Terraform repository with:

- **Contents: Read and write** — read the catalog, create a branch, and update the catalog file.
- **Pull requests: Read and write** — create the PR.

For enterprise use, replace the personal token with a GitHub App installation token.

## Environment variables

| Variable | Purpose |
|---|---|
| `GITHUB_OWNER` | Owner/org of Terraform repository |
| `GITHUB_REPO` | Terraform repository name |
| `GITHUB_TOKEN` | Fine-grained PAT or GitHub App token |
| `GITHUB_BASE_BRANCH` | Usually `main` |
| `GITHUB_CATALOG_PATH` | Defaults to `catalog/saml_apps.json` |
| `GITHUB_API_VERSION` | Defaults to `2026-03-10` |

## Security boundary

This service can request a configuration change. The Terraform repository is responsible for validation, approval, state, and Okta deployment. Do not put the Okta private key in this repository.
