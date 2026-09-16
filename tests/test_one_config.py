"""Тесты OneConfig: чтение и валидация config.yml через Pydantic."""

import pytest
from pydantic import ValidationError

from src.config import OneConfig
from src.main_module import MainModule


def test_config_defaults_when_missing(tmp_path):
    """При отсутствующем файле используются значения по умолчанию."""
    cfg = OneConfig.build(path=tmp_path / "not_exist.yml")

    assert cfg.logger.log_level == "info"
    assert cfg.measure.default_runs == 10
    assert cfg.measure.max_runs == 100
    assert cfg.measure.default_timeout == 60


def test_config_reads_yaml(tmp_path):
    """Значения из YAML-файла попадают в конфиг."""
    path = tmp_path / "config.yml"
    path.write_text(
        "logger:\n  log_level: debug\nmeasure:\n  default_runs: 5\n",
        encoding="utf-8",
    )
    cfg = OneConfig.build(path=path)

    assert cfg.logger.log_level == "debug"
    assert cfg.measure.default_runs == 5


def test_config_invalid_structure_raises(tmp_path):
    """Неверная структура конфига вызывает pydantic.ValidationError."""
    path = tmp_path / "config.yml"
    path.write_text("measure:\n  default_runs: 'not-a-number'\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        OneConfig.build(path=path)


def test_config_access_before_build_raises(tmp_path):
    """Доступ к конфигу до build() поднимает RuntimeError."""
    cfg = OneConfig(path=tmp_path / "nope.yml")

    with pytest.raises(RuntimeError):
        _ = cfg.measure  # noqa: B018


def test_main_module_config_via_kwargs(tmp_path):
    """MainModule передаёт config_path модулю OneConfig через kwargs."""
    path = tmp_path / "config.yml"
    path.write_text("measure:\n  default_runs: 7\n", encoding="utf-8")

    mm = MainModule(config_path=path)

    assert mm.config.measure.default_runs == 7
