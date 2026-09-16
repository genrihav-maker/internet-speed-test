"""Тесты OneLogger: настройка хендлеров, _to_level и get_logger."""

import logging

import pytest

from src.config import OneConfig
from src.logger import _to_level, get_logger
from src.main_module import MainModule

NO_FILE_CONFIG = """
logger:
  log_level: info
  stream:
    log_level: warn
measure:
  default_runs: 2
  max_runs: 3
  default_timeout: 10
  max_timeout: 30
"""


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        ("debug", logging.DEBUG),
        ("INFO", logging.INFO),
        ("warn", logging.WARNING),
        ("WARN", logging.WARNING),
        ("error", logging.ERROR),
        ("bogus", logging.INFO),
    ],
)
def test_to_level(level, expected):
    """Строковые уровни переводятся в константы logging (невалидные — в default)."""
    assert _to_level(level) == expected


def test_to_level_warn_default_is_warning():
    """Ветка default=logging.WARNING в _to_level отрабатывает для 'WARN'."""
    assert _to_level("WARN", default=logging.WARNING) == logging.WARNING


def test_get_logger():
    """get_logger возвращает логгер по имени."""
    assert get_logger("test-module") is logging.getLogger("test-module")


def test_logger_without_file_handler(tmp_path):
    """Без секции file в конфиге добавляется только stream-хендлер."""
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(NO_FILE_CONFIG, encoding="utf-8")

    mm = MainModule(config_path=cfg_path)
    root = logging.getLogger()
    handler_types = [type(h).__name__ for h in root.handlers]

    assert mm.logger.logger is not None
    assert "StreamHandler" in handler_types
    assert "TimedRotatingFileHandler" not in handler_types


def test_logger_stream_level_from_config(tmp_path, capsys):
    """stream.log_level: warn ограничивает вывод только warning+ сообщениями."""
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(NO_FILE_CONFIG, encoding="utf-8")

    mm = MainModule(config_path=cfg_path)
    mm.logger.debug("skipped-debug")
    mm.logger.warning("seen-warning")

    out = capsys.readouterr().out
    assert "skipped-debug" not in out
    assert "seen-warning" in out


def test_logger_destroy_closes_handlers(tmp_path):
    """destroy() закрывает и очищает хендлеры модуля."""
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(NO_FILE_CONFIG, encoding="utf-8")

    mm = MainModule(config_path=cfg_path)
    mm.logger.destroy()

    assert mm.logger._handlers == []


def test_config_module_repr():
    """ОдинConfig вручную без build корректно строится и имеет представление."""
    cfg = OneConfig(path="nope.yml")
    assert cfg.name == "config"
    assert repr(cfg) == "<OneConfig name='config'>"
