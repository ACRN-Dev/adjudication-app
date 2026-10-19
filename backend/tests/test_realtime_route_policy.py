"""CI guard for authorization policy coverage on every retained RealTime route."""

from api.realtime import router
from services.route_policy import ADJUDICATOR, MONITOR, REALTIME_ROUTE_POLICIES, WORKFLOW


EXPECTED_DEPENDENCY = {
    MONITOR: "monitor",
    ADJUDICATOR: "adjudicator",
    WORKFLOW: "actor",
}


def test_every_realtime_route_has_an_explicit_authorization_policy():
    actual = {
        (method, route.path): route
        for route in router.routes
        for method in route.methods
        if method not in {"HEAD", "OPTIONS"}
    }
    assert set(actual) == set(REALTIME_ROUTE_POLICIES), (
        "RealTime route inventory changed. Classify every added route before release. "
        f"Unclassified={sorted(set(actual) - set(REALTIME_ROUTE_POLICIES))}; "
        f"stale={sorted(set(REALTIME_ROUTE_POLICIES) - set(actual))}"
    )

    for key, route in actual.items():
        dependency_names = {
            getattr(dependency.call, "__name__", "")
            for dependency in route.dependant.dependencies
        }
        required_dependency = EXPECTED_DEPENDENCY[REALTIME_ROUTE_POLICIES[key]]
        assert required_dependency in dependency_names, (
            f"{key[0]} {key[1]} is classified as {REALTIME_ROUTE_POLICIES[key]} "
            f"but does not directly enforce {required_dependency}()."
        )
