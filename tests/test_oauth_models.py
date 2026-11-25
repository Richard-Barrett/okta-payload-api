import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models import OAuth2ApplicationRequest, OidcApplicationRequest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def payload(filename):
    return json.loads((EXAMPLES / filename).read_text())


def test_valid_oidc_bookmark_request():
    request = OidcApplicationRequest.model_validate(payload("oidc-app-request.json"))
    assert request.include_bookmark is True
    assert request.bookmark_url.host == "finance-dev.example.com"
    assert request.token_endpoint_auth_method == "client_secret_basic"


def test_oidc_without_bookmark():
    example = payload("oidc-app-request.json")
    example.pop("bookmark_url")
    example.pop("bookmark_label")
    example["include_bookmark"] = False
    assert OidcApplicationRequest.model_validate(example).include_bookmark is False


def test_oidc_bookmark_requires_url():
    example = payload("oidc-app-request.json")
    example.pop("bookmark_url")
    with pytest.raises(ValidationError, match="bookmark_url"):
        OidcApplicationRequest.model_validate(example)


def test_oidc_browser_requires_pkce_and_public_client():
    example = payload("oidc-app-request.json")
    example["client_type"] = "browser"
    example["pkce_required"] = False
    with pytest.raises(ValidationError, match="PKCE"):
        OidcApplicationRequest.model_validate(example)
    example["pkce_required"] = True
    example["token_endpoint_auth_method"] = "none"
    assert OidcApplicationRequest.model_validate(example).token_endpoint_auth_method == "none"


def test_oidc_rejects_wildcard_redirect():
    example = payload("oidc-app-request.json")
    example["redirect_uris"] = ["https://*.example.com/callback"]
    with pytest.raises(ValidationError):
        OidcApplicationRequest.model_validate(example)


def test_oidc_rejects_non_https_production_redirect():
    example = payload("oidc-app-request.json")
    example["redirect_uris"] = ["http://finance-dev.example.com/callback"]
    example["environment"] = "prod"
    with pytest.raises(ValidationError, match="HTTPS"):
        OidcApplicationRequest.model_validate(example)


def test_oidc_preserves_exact_redirect_uri():
    example = payload("oidc-app-request.json")
    example["redirect_uris"] = ["https://EXAMPLE.com:443"]
    request = OidcApplicationRequest.model_validate(example)
    assert request.model_dump(mode="json")["redirect_uris"] == example["redirect_uris"]


def test_service_jwks_requires_https_even_in_dev():
    example = payload("oauth-app-request.json")
    example["jwks_uri"] = "http://localhost/jwks"
    with pytest.raises(ValidationError, match="HTTPS"):
        OAuth2ApplicationRequest.model_validate(example)


def test_valid_oauth2_service_request():
    request = OAuth2ApplicationRequest.model_validate(payload("oauth-app-request.json"))
    assert request.grant_types == ["client_credentials"]
    assert request.include_bookmark is False
    assert request.jwks_uri.scheme == "https"


def test_oauth2_rejects_bookmark():
    example = payload("oauth-app-request.json")
    example["include_bookmark"] = True
    example["bookmark_url"] = "https://example.com/login"
    with pytest.raises(ValidationError, match="bookmarks"):
        OAuth2ApplicationRequest.model_validate(example)


def test_oauth2_rejects_missing_jwks():
    example = payload("oauth-app-request.json")
    del example["jwks_uri"]
    with pytest.raises(ValidationError):
        OAuth2ApplicationRequest.model_validate(example)


def test_oauth2_rejects_secret_field():
    example = payload("oauth-app-request.json")
    example["client_secret"] = "DO_NOT_RECORD"
    with pytest.raises(ValidationError, match="Extra inputs"):
        OAuth2ApplicationRequest.model_validate(example)


def test_valid_delegated_oauth2_web_client():
    example = payload("oauth-web-app-request.json")
    request = OAuth2ApplicationRequest.model_validate(example)
    assert request.client_type == "web"
    assert request.grant_types == ["authorization_code"]
    assert request.include_bookmark is False


def test_delegated_oauth2_web_rejects_bookmark():
    example = payload("oauth-web-app-request.json")
    example["include_bookmark"] = True
    example["bookmark_url"] = "https://reports-dev.example.com/login"
    with pytest.raises(ValidationError, match="Bookmarks"):
        OAuth2ApplicationRequest.model_validate(example)


def test_delegated_oauth2_browser_enforces_pkce():
    example = payload("oauth-web-app-request.json")
    example["client_type"] = "browser"
    example["pkce_required"] = False
    with pytest.raises(ValidationError, match="PKCE"):
        OAuth2ApplicationRequest.model_validate(example)
    example["pkce_required"] = True
    example["token_endpoint_auth_method"] = "none"
    request = OAuth2ApplicationRequest.model_validate(example)
    assert request.client_type == "browser"
