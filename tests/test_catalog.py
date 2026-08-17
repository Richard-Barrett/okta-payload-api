from app.catalog import add_application
from app.models import SamlApplicationRequest


def request(key="sample-app"):
    return SamlApplicationRequest(
        key=key,
        label="Sample Application",
        sso_url="https://example.com/saml/acs",
        audience="https://example.com",
        owner="identity-team",
        requested_by="developer@example.com",
    )


def test_add_application():
    catalog = {"applications": {}}
    updated = add_application(catalog, request())
    assert "sample-app" in updated["applications"]
    assert updated["applications"]["sample-app"]["label"] == "Sample Application"


def test_duplicate_application_rejected():
    catalog = {"applications": {"sample-app": {"label": "Existing"}}}
    try:
        add_application(catalog, request())
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "already exists" in str(exc)
