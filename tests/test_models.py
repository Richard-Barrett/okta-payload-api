import pytest
from pydantic import ValidationError

from app.models import SamlApplicationRequest


def test_invalid_key_rejected():
    with pytest.raises(ValidationError):
        SamlApplicationRequest(
            key="Bad App Name",
            label="Bad App",
            sso_url="https://example.com/acs",
            audience="https://example.com",
            owner="identity-team",
            requested_by="developer@example.com",
        )
