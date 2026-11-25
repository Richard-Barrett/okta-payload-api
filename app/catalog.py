from copy import deepcopy

from .models import OAuthApplicationBase, SamlApplicationRequest


def application_to_catalog_entry(request: SamlApplicationRequest | OAuthApplicationBase) -> dict:
    data = request.model_dump(mode="json", exclude_none=isinstance(request, OAuthApplicationBase))
    key = data.pop("key")
    # Metadata stays in the catalog for governance/auditability. Terraform's module
    # consumes only the fields it needs.
    return {key: data}


def add_application(catalog: dict, request: SamlApplicationRequest | OAuthApplicationBase) -> dict:
    updated = deepcopy(catalog)
    applications = updated.setdefault("applications", {})

    if request.key in applications:
        raise ValueError(f"Application key already exists: {request.key}")

    applications.update(application_to_catalog_entry(request))
    updated["applications"] = dict(sorted(applications.items()))
    return updated
