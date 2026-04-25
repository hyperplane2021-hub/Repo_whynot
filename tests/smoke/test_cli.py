from typer.testing import CliRunner

from app.cli.main import app


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Repo_whynot" in result.output
