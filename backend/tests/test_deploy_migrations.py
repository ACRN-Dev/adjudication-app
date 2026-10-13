from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _assert_initializer_precedes_start(script_name, initializer, start_command):
    script = (REPO_ROOT / "scripts" / script_name).read_text(encoding="utf-8")

    assert initializer in script
    assert script.index(initializer) < script.index(start_command)


def test_production_deploy_removes_demo_data_before_starting_app():
    initializer = "python backend/scripts/init_prod.py"
    _assert_initializer_precedes_start("deploy-prod.sh", initializer, "$COMPOSE up -d")
    _assert_initializer_precedes_start(
        "deploy-prod.ps1", initializer, "docker compose @composeFiles up -d"
    )
    for script_name in ("deploy-prod.sh", "deploy-prod.ps1"):
        script = (REPO_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "--schema-only" not in script


def test_production_compose_disables_demo_features():
    compose = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert 'ENABLE_DEMO_DATA: "false"' in compose
    assert 'ENABLE_DEMO_ACCOUNTS: "false"' in compose
    assert 'VITE_ENABLE_DEMO_UI: "false"' in compose
    assert "ARG VITE_ENABLE_DEMO_UI=false" in dockerfile


def test_demo_deploy_applies_schema_before_starting_app():
    initializer = "python backend/scripts/init_prod.py --schema-only"
    _assert_initializer_precedes_start("deploy-demo.sh", initializer, "$COMPOSE up -d")
    _assert_initializer_precedes_start(
        "deploy-demo.ps1", initializer, "docker compose @composeFiles up -d"
    )
    demo_compose = (REPO_ROOT / "docker-compose.demo.yml").read_text(encoding="utf-8")
    assert 'VITE_ENABLE_DEMO_UI: "true"' in demo_compose


def test_demo_shell_script_has_a_real_working_directory_and_health_loop():
    script = (REPO_ROOT / "scripts" / "deploy-demo.sh").read_text(encoding="utf-8")

    assert 'cd "$(dirname "$0")/.."' in script
    assert "for _ in $(seq 1 20); do" in script


def test_schema_only_exits_before_demo_data_purge():
    script = (REPO_ROOT / "backend" / "scripts" / "init_prod.py").read_text(encoding="utf-8")

    schema_only_exit = 'if SCHEMA_ONLY:'
    purge_step = 'step(4, "Purging synthetic demo data")'
    assert script.index(schema_only_exit) < script.index(purge_step)
