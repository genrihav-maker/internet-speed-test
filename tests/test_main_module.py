"""Тесты MainModule: логика замера скорости и сборка модулей."""

from src import __version__
from src.base import OneModule
from src.config import OneConfig
from src.logger import OneLogger
from src.main_module import MainModule


def test_measure_speed_ok(main_module, file_server):
    """Замер с рабочего адреса возвращает метрики всех успешных запросов."""
    result = main_module.measure_speed(file_server, runs=3, timeout=10)

    assert result["runs"] == 3
    assert result["runs_ok"] == 3
    assert result["total_bytes"] == 3 * 1024 * 1024
    assert result["avg_time_s"] > 0
    assert result["avg_speed_mb_s"] > 0
    assert len(result["per_request"]) == 3
    assert all(r["error"] is None for r in result["per_request"])
    assert all(r["size_bytes"] == 1024 * 1024 for r in result["per_request"])


def test_measure_speed_all_fail(main_module, closed_port_url):
    """При недоступном адресе все запросы помечаются ошибкой и метрики нулевые."""
    result = main_module.measure_speed(closed_port_url, runs=2, timeout=5)

    assert result["runs"] == 2
    assert result["runs_ok"] == 0
    assert result["total_bytes"] == 0
    assert result["avg_time_s"] == 0
    assert result["avg_speed_mb_s"] == 0
    assert all(r["error"] is not None for r in result["per_request"])


def test_measure_speed_single_run(main_module, file_server):
    """Одиночный запрос с рабочего адреса скачивает ровно один файл."""
    result = main_module.measure_speed(file_server, runs=1, timeout=10)

    assert result["runs_ok"] == 1
    assert result["total_bytes"] == 1024 * 1024


def test_measure_speed_partial_failure(main_module, flaky_server):
    """Успешные запросы учитываются, неудачные помечаются и не искажают среднее."""
    result = main_module.measure_speed(flaky_server, runs=3, timeout=10)

    assert result["runs_ok"] == 2
    assert result["total_bytes"] == 2 * 1024 * 1024
    assert result["avg_time_s"] > 0
    assert result["avg_speed_mb_s"] > 0
    assert sum(1 for r in result["per_request"] if r["error"] is not None) == 1
    assert sum(1 for r in result["per_request"] if r["error"] is None) == 2


def test_measure_speed_follows_redirects(main_module, redirect_server):
    """302-редирект обрабатывается, данные скачиваются с финального адреса."""
    result = main_module.measure_speed(redirect_server, runs=1, timeout=10)

    assert result["runs_ok"] == 1
    assert result["total_bytes"] == 1024 * 1024
    assert result["per_request"][0]["error"] is None


def test_main_module_init_order(main_module):
    """Модули собираются в порядке config -> logger."""
    assert main_module.config.logger.log_level == "info"
    assert main_module.logger.logger is not None


def test_main_module_title_and_version(main_module):
    """Имя и версия сервиса соответствуют ожидаемым."""
    assert main_module.title == "internet-speed-test"
    assert main_module.version == __version__


def test_modules_auto_discovery_order(main_module):
    """Модули обнаруживаются и собираются в том же порядке, что объявлены."""
    classes = [type(module) for _, module in main_module.modules]
    assert classes == [OneConfig, OneLogger]


def test_modules_discovered_from_typehint():
    """Fromtypehint находит все модули по аннотациям MainModule."""
    hints = OneModule.fromtypehint(MainModule)
    assert hints == {"config": OneConfig, "logger": OneLogger}


def test_module_repr():
    """Каждый модуль имеет представление <ClassName name='...'>."""
    cfg = OneConfig(path="nope.yml")
    assert repr(cfg) == "<OneConfig name='config'>"


def test_destroy_modules(tmp_path):
    """destroy_modules() освобождает хендлеры модулей в обратном порядке."""
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(
        "logger:\n  stream:\n    log_level: debug\n"
        "measure:\n  default_runs: 2\n  max_runs: 3\n"
        "  default_timeout: 10\n  max_timeout: 30\n",
        encoding="utf-8",
    )
    mm = MainModule(config_path=cfg_path)

    mm.destroy_modules()

    assert mm.logger._handlers == []
