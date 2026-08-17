from copy import deepcopy

from .models import SamlApplicationRequest


def application_to_catalog_entry(request: SamlApplicationRequest) -> dict:
    data = request.model_dump(mode="json")
    key = data.pop("key")
    # Metadata stays in the catalog for governance/auditability. Terraform's module
    # consumes only the fields it needs.
    return {key: data}


def add_application(catalog: dict, request: SamlApplicationRequest) -> dict:
    updated = deepcopy(catalog)
    applications = updated.setdefault("applications", {})

    if request.key in applications:
        raise ValueError(f"Application key already exists: {request.key}")

    applications.update(application_to_catalog_entry(request))
    updated["applications"] = dict(sorted(applications.items()))
    return updated
