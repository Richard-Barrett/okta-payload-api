from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


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


class PullRequestResult(BaseModel):
    status: Literal["submitted"] = "submitted"
    application: str
    branch: str
    pull_request_number: int
    pull_request_url: str
