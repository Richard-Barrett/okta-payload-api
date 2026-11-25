# GMF Okta Application Intake API

FastAPI service that validates Okta SAML, OAuth 2.0, and OpenID Connect (OIDC) application requests and opens GitHub pull requests against the Terraform catalog.

## Flow

```text
Caller -> FastAPI -> GitHub branch -> Application catalog -> Pull request -> Terraform CI
```

## Endpoints

| Application | Submit a PR | Example payload |
|---|---|---|
| SAML 2.0 | `POST /v1/okta/saml-applications` | [SAML app](examples/saml-app-request.json) |
| OAuth 2.0 | `POST /v1/okta/oauth-applications` | [Service client](examples/oauth-app-request.json), [delegated web client](examples/oauth-web-app-request.json) |
| OIDC | `POST /v1/okta/oidc-applications` | [OIDC app](examples/oidc-app-request.json) |

Append `/validate` to check a payload and see its normalized form without calling GitHub. Submit to the base endpoint to create a PR and receive HTTP 201 with its URL.

OAuth service clients use the client credentials grant, `private_key_jwt`, and an HTTPS URL for their public JWKS. Interactive OAuth and OIDC clients use authorization code and registered redirect URLs. Browser and native clients require PKCE and token authentication method `none`. Callbacks use HTTPS, with HTTP loopback redirects accepted in `dev` and `test`. OIDC supports an optional dashboard bookmark through `include_bookmark` and `bookmark_url`. OAuth and OIDC requests default to `INACTIVE` and reject unknown fields, including client secret and private key fields.

## Local setup

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

curl -sS -X POST http://localhost:8000/v1/okta/oauth-applications/validate \
  -H 'Content-Type: application/json' \
  --data @examples/oauth-app-request.json
```

Create a PR:

```bash
curl -sS -X POST http://localhost:8000/v1/okta/saml-applications \
  -H 'Content-Type: application/json' \
  --data @examples/saml-app-request.json
```

## Developer checks

With the project's Python virtual environment active, install the developer dependencies and Git hooks once per checkout.

```bash
python -m pip install -e '.[dev]'
python -m pre_commit install --install-hooks
```

The hooks run on staged files and check Ruff lint, JSON, TOML and YAML syntax, merge markers, private keys, and whitespace. First-time setup downloads the hook environments. If a hook fixes whitespace, review and stage the change before retrying the commit.

```bash
python -m pre_commit run --all-files
python -m pytest -q
```

GitHub Actions runs the same hooks and tests the API on Python 3.12–3.14. A separate workflow builds the Docker image and checks `/healthz` and the SAML, OAuth, and OIDC validation endpoints. Both workflows run on pull requests and pushes to `main` without provisioning credentials.

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
| `GITHUB_OAUTH_CATALOG_PATH` | Shared OAuth and OIDC catalog. Defaults to `catalog/oauth_apps.json` |
| `GITHUB_API_VERSION` | Defaults to `2026-03-10` |

## Terraform integration

The configured base branch must already contain the catalog for the selected endpoint. OAuth and OIDC entries live under the shared catalog's top-level `applications` object, keyed by the request's `key`. Each entry carries the `protocol` value `oauth2` or `oidc`. The companion Terraform repository must validate the OAuth catalog and consume its entries in its plan before it can provision these applications. The current companion checkout contains only the SAML catalog and module.

## Security boundary

This service can request a configuration change. The Terraform repository is responsible for validation, approval, state, and Okta deployment. Do not put the Okta private key in this repository.
