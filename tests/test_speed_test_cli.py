"""Тесты CLI-точки входа: флаги, валидация лимитов и вывод результата."""

import sys

import pytest

from src import __version__, speed_test
from src.main_module import MainModule


def _set_argv(monkeypatch, *args: str) -> None:
    """Подставляет argv в 'speed_test ...' для вызова main()."""
    monkeypatch.setattr(sys, "argv", ["speed_test", *args])


@pytest.fixture
def use_test_main_module(monkeypatch, main_module):
    """Подменяет MainModule в CLI на экземпляр из тестового конфига."""
    monkeypatch.setattr(speed_test, "MainModule", lambda: main_module)
    return main_module


def test_cli_version_exits_0(monkeypatch, capsys):
    """--version печатает версию сервиса и завершается с кодом 0."""
    _set_argv(monkeypatch, "--version")

    with pytest.raises(SystemExit) as exc:
        speed_test.main()

    assert exc.value.code == 0
    assert capsys.readouterr().out == __version__


def test_cli_name_exits_0(monkeypatch, capsys):
    """--name печатает имя сервиса и завершается с кодом 0."""
    _set_argv(monkeypatch, "--name")

    with pytest.raises(SystemExit) as exc:
        speed_test.main()

    assert exc.value.code == 0
    assert capsys.readouterr().out == speed_test.MainModule.title


def test_cli_missing_url_exits_2(monkeypatch, capsys):
    """Без url argparse завершает программу с кодом 2."""
    _set_argv(monkeypatch)

    with pytest.raises(SystemExit) as exc:
        speed_test.main()

    assert exc.value.code == 2
    assert "не указан url" in capsys.readouterr().err


def test_cli_ok(monkeypatch, use_test_main_module, file_server, caplog):
    """Успешный замер выводит итог со скоростью в МБ/с."""
    _set_argv(monkeypatch, file_server, "-n", "1", "-t", "10")

    speed_test.main()

    assert "скорость" in caplog.text
    assert "МБ/с" in caplog.text


def test_cli_all_requests_failed_exits_1(monkeypatch, tmp_path, closed_port_url, capsys):
    """Если ни один запрос не удался, CLI завершается с ошибкой и кодом 1."""
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(
        "logger:\n  stream:\n    log_level: debug\n"
        "measure:\n  default_runs: 2\n  max_runs: 3\n"
        "  default_timeout: 5\n  max_timeout: 30\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(speed_test, "MainModule", lambda: MainModule(config_path=cfg_path))
    _set_argv(monkeypatch, closed_port_url, "-n", "1", "-t", "5")

    with pytest.raises(SystemExit) as exc:
        speed_test.main()

    assert exc.value.code == 1
    assert "ни один запрос не выполнился успешно" in capsys.readouterr().out


def test_cli_defaults_from_config(monkeypatch, use_test_main_module, file_server, caplog):
    """Без -n/-t используются значения по умолчанию из тестового конфига."""
    _set_argv(monkeypatch, file_server)

    speed_test.main()

    assert "скачано: 2.00 МБ" in caplog.text


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (("-n", "0"), "runs и timeout должны быть больше нуля"),
        (("-t", "0"), "runs и timeout должны быть больше нуля"),
        (("-n", "4"), "max_runs (3)"),
        (("-t", "31"), "max_timeout (30)"),
    ],
)
def test_cli_invalid_limits_exit_1(monkeypatch, use_test_main_module, argv, message, caplog):
    """Невалидные -n/-t или превышение лимитов дают ошибку и код выхода 1."""
    _set_argv(monkeypatch, "http://example.com/x", *argv)

    with pytest.raises(SystemExit) as exc:
        speed_test.main()

    assert exc.value.code == 1
    assert message in caplog.text
