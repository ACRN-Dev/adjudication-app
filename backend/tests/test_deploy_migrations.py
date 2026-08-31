from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _assert_migration_precedes_start(script_name, start_command):
    script = (REPO_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
    migration = "python backend/scripts/init_prod.py --schema-only"

    assert migration in script
    assert script.index(migration) < script.index(start_command)


def test_routine_deploy_applies_schema_before_starting_app():
    _assert_migration_precedes_start("deploy-prod.sh", "$COMPOSE up -d")
    _assert_migration_precedes_start("deploy-prod.ps1", "docker compose @composeFiles up -d")


def test_demo_deploy_applies_schema_before_starting_app():
    _assert_migration_precedes_start("deploy-demo.sh", "$COMPOSE up -d")
    _assert_migration_precedes_start("deploy-demo.ps1", "docker compose @composeFiles up -d")


def test_demo_shell_script_has_a_real_working_directory_and_health_loop():
    script = (REPO_ROOT / "scripts" / "deploy-demo.sh").read_text(encoding="utf-8")

    assert 'cd "$(dirname "$0")/.."' in script
    assert "for _ in $(seq 1 20); do" in script


def test_schema_only_exits_before_demo_data_purge():
    script = (REPO_ROOT / "backend" / "scripts" / "init_prod.py").read_text(encoding="utf-8")

    schema_only_exit = 'if SCHEMA_ONLY:'
    purge_step = 'step(4, "Purging synthetic demo data")'
    assert script.index(schema_only_exit) < script.index(purge_step)
