from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class AttributeStatement(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: Literal["EXPRESSION", "GROUP"] = "EXPRESSION"
    values: list[str] = Field(default_factory=list)
    filter_type: Literal[
        "STARTS_WITH", "EQUALS", "CONTAINS", "REGEX"
    ] | None = None
    filter_value: str | None = None

    @field_validator("values")
    @classmethod
    def expression_requires_values(cls, value: list[str], info):
        if info.data.get("type") == "EXPRESSION" and not value:
            raise ValueError("EXPRESSION attribute statements require at least one value")
        return value


class SamlApplicationRequest(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,62}$")
    label: str = Field(min_length=2, max_length=100)
    sso_url: HttpUrl
    audience: str = Field(min_length=1, max_length=512)
    recipient: HttpUrl | None = None
    destination: HttpUrl | None = None
    subject_name_id_template: str = "${user.email}"
    subject_name_id_format: str = (
        "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    )
    status: Literal["ACTIVE", "INACTIVE"] = "ACTIVE"
    response_signed: bool = True
    assertion_signed: bool = True
    signature_algorithm: Literal["RSA_SHA256", "RSA_SHA1"] = "RSA_SHA256"
    digest_algorithm: Literal["SHA256", "SHA1"] = "SHA256"
    honor_force_authn: bool = False
    attribute_statements: list[AttributeStatement] = Field(default_factory=list)
    owner: str = Field(min_length=2, max_length=150)
    requested_by: str = Field(min_length=2, max_length=150)
    environment: Literal["dev", "test", "stage", "prod"] = "dev"
    sal: Literal["SAL1", "SAL2", "SAL3", "SAL4"] | None = None


RedirectUri = Annotated[str, Field(min_length=1, max_length=2083)]


class OAuthApplicationBase(BaseModel):
    """Shared OIDC / OAuth2 fields; raw secrets are explicitly rejected."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,62}$")
    label: str = Field(min_length=2, max_length=100)
    protocol: Literal["oidc", "oauth2"]
    client_type: Literal["web", "browser", "native", "service"]
    grant_types: list[Literal["authorization_code", "refresh_token", "client_credentials"]]
    response_types: list[Literal["code", "token"]]
    redirect_uris: list[RedirectUri] = Field(default_factory=list)
    post_logout_redirect_uris: list[RedirectUri] = Field(default_factory=list)
    login_uri: HttpUrl | None = None
    token_endpoint_auth_method: Literal["none", "client_secret_basic", "private_key_jwt"] | None = None
    pkce_required: bool = True
    jwks_uri: HttpUrl | None = None
    refresh_token_rotation: Literal["ROTATE", "STATIC"] | None = None
    refresh_token_leeway: int | None = Field(default=None, ge=0, le=60)
    include_bookmark: bool = False
    bookmark_url: HttpUrl | None = None
    bookmark_label: str | None = Field(default=None, min_length=2, max_length=100)
    group_ids: list[str] = Field(default_factory=list)
    status: Literal["ACTIVE", "INACTIVE"] = "INACTIVE"
    owner: str = Field(min_length=2, max_length=150)
    requested_by: str = Field(min_length=2, max_length=150)
    environment: Literal["dev", "test", "stage", "prod"] = "dev"
    sal: Literal["SAL1", "SAL2", "SAL3", "SAL4"] | None = None

    @model_validator(mode="after")
    def validate_oauth_settings(self) -> "OAuthApplicationBase":
        self._validate_urls()
        for field in (
            "redirect_uris", "post_logout_redirect_uris", "group_ids", "grant_types", "response_types",
        ):
            items = getattr(self, field)
            if len(set(items)) != len(items):
                raise ValueError(f"{field} must not contain duplicates")

        if "refresh_token" in self.grant_types:
            if self.refresh_token_rotation is None:
                self.refresh_token_rotation = "ROTATE"
            if self.refresh_token_leeway is None:
                self.refresh_token_leeway = 30
        elif self.refresh_token_rotation is not None or self.refresh_token_leeway is not None:
            raise ValueError("Refresh token rotation settings require the refresh_token grant")

        if self.client_type == "service":
            self._validate_service_client()
        else:
            self._validate_interactive_client()

        if self.token_endpoint_auth_method == "private_key_jwt" and self.jwks_uri is None:
            raise ValueError("private_key_jwt requires a public jwks_uri")
        return self

    def _validate_urls(self) -> None:
        # OAuth clients must send the exact registered redirect URI.
        for raw_uri in [*self.redirect_uris, *self.post_logout_redirect_uris]:
            if any(char.isspace() for char in raw_uri) or "\\" in raw_uri:
                raise ValueError("Redirect URIs cannot contain whitespace or backslashes")
            if not urlsplit(raw_uri).netloc:
                raise ValueError("Redirect URIs must include an HTTP or HTTPS scheme and host")
            self._validate_url(
                HttpUrl(raw_uri), raw_uri, allow_loopback=self.environment in {"dev", "test"}
            )

        for url in (self.login_uri, self.jwks_uri, self.bookmark_url):
            if url is not None:
                self._validate_url(url, str(url))

    @staticmethod
    def _validate_url(url: HttpUrl, original: str, *, allow_loopback: bool = False) -> None:
        if "@" in urlsplit(original).netloc or "#" in original or "*" in original:
            raise ValueError("URLs cannot contain credentials, fragments, or wildcards")
        if url.scheme != "https" and not (
            allow_loopback and url.host in {"localhost", "127.0.0.1", "[::1]"}
        ):
            raise ValueError("URLs must use HTTPS except for loopback redirects in dev or test")

    def _validate_service_client(self) -> None:
        if self.grant_types != ["client_credentials"] or self.response_types != ["token"]:
            raise ValueError("OAuth2 service clients require client_credentials and token response")
        if self.token_endpoint_auth_method is None:
            self.token_endpoint_auth_method = "private_key_jwt"
        if self.token_endpoint_auth_method != "private_key_jwt":
            raise ValueError("OAuth2 service clients require private_key_jwt")
        if (
            self.redirect_uris
            or self.post_logout_redirect_uris
            or self.login_uri
            or self.include_bookmark
            or self.bookmark_url
            or self.bookmark_label
            or self.group_ids
        ):
            raise ValueError("OAuth2 service clients cannot have redirects, bookmarks, or user groups")

    def _validate_interactive_client(self) -> None:
        if not self.redirect_uris:
            raise ValueError("Interactive OAuth/OIDC clients require redirect_uris")
        if "authorization_code" not in self.grant_types or "client_credentials" in self.grant_types:
            raise ValueError("Interactive OAuth/OIDC clients require authorization_code grant")
        if self.response_types != ["code"]:
            raise ValueError("Interactive OAuth/OIDC clients support code response only")

        public_client = self.client_type in {"browser", "native"}
        if self.token_endpoint_auth_method is None:
            self.token_endpoint_auth_method = "none" if public_client else "client_secret_basic"
        if public_client and (self.token_endpoint_auth_method != "none" or not self.pkce_required):
            raise ValueError("Browser/native clients must use token auth 'none' and PKCE")
        if not public_client and self.token_endpoint_auth_method == "none":
            raise ValueError("Web clients must use client_secret_basic or private_key_jwt")

        if self.include_bookmark:
            if self.protocol != "oidc":
                raise ValueError("Bookmarks are only supported for OIDC clients")
            if self.bookmark_url is None:
                raise ValueError("include_bookmark=true requires bookmark_url")
        elif self.bookmark_url is not None or self.bookmark_label is not None:
            raise ValueError("bookmark_url/label require include_bookmark=true")


class OidcApplicationRequest(OAuthApplicationBase):
    protocol: Literal["oidc"] = "oidc"
    client_type: Literal["web", "browser", "native"] = "web"
    grant_types: list[Literal["authorization_code", "refresh_token"]] = Field(
        default_factory=lambda: ["authorization_code"]
    )
    response_types: list[Literal["code"]] = Field(default_factory=lambda: ["code"])


class OAuth2ApplicationRequest(OAuthApplicationBase):
    protocol: Literal["oauth2"] = "oauth2"
    # Defaults to client-credentials service, but supports delegated OAuth2
    # web/browser/native clients when their grant and redirect fields are set.
    client_type: Literal["web", "browser", "native", "service"] = "service"
    grant_types: list[Literal["authorization_code", "refresh_token", "client_credentials"]] = Field(
        default_factory=lambda: ["client_credentials"]
    )
    response_types: list[Literal["code", "token"]] = Field(
        default_factory=lambda: ["token"]
    )


class PullRequestResult(BaseModel):
    status: Literal["submitted"] = "submitted"
    application: str
    branch: str
    pull_request_number: int
    pull_request_url: str
