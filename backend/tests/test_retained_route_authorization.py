"""Deny-by-default guard for every route retained by the production application."""

from main import app


PUBLIC_ROUTES = {
    ("GET", "/api/auth/config"),
    ("GET", "/api/auth/sso/login"),
    ("GET", "/api/auth/sso/callback"),
    ("POST", "/api/auth/login"),
}

LEGACY_PREFIXES = (
    "/api/import",
    "/api/mappings",
    "/api/reconcile",
    "/api/derive",
    "/api/narrative",
    "/api/adjudication",
    "/api/committee",
    "/api/audit",
    "/api/workflow",
)

PROTECTED_DEPENDENCIES = {
    "current_user",
    "dep",          # require_role()/require_chairperson_assignment() closure
    "dependency",   # Admin permission closure
    "get_identity",
    "identity",
    "monitor",
    "adjudicator",
    "actor",
}


def test_every_production_retained_api_route_is_public_or_has_an_auth_dependency():
    unclassified = []
    for route in app.routes:
        if not hasattr(route, "dependant") or not route.path.startswith("/api/"):
            continue
        if route.path.startswith(LEGACY_PREFIXES):
            continue
        dependency_names = {
            getattr(dependency.call, "__name__", "")
            for dependency in route.dependant.dependencies
        }
        for method in route.methods - {"HEAD", "OPTIONS"}:
            key = (method, route.path)
            if key in PUBLIC_ROUTES:
                continue
            if "require_legacy_unsafe_route" in dependency_names:
                continue
            if not dependency_names.intersection(PROTECTED_DEPENDENCIES):
                unclassified.append(key)

    assert not unclassified, (
        "Production-retained routes must declare authentication or be explicitly public: "
        f"{sorted(unclassified)}"
    )
