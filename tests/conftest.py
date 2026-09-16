"""Общие фикстуры тестов: локальный файл-сервер и собранный MainModule."""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from src.main_module import MainModule

PAYLOAD = b"x" * (1024 * 1024)

TEST_CONFIG = """
logger:
  log_level: info
  log_format: "%(levelname)s | %(name)s | %(message)s"
  stream:
    log_level: debug
  file:
    log_level: info
    path: logs/test.log
measure:
  default_runs: 2
  max_runs: 3
  default_timeout: 10
  max_timeout: 30
"""


class _FileHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Отдаёт PAYLOAD с заголовком Content-Length."""
        self.send_response(200)
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def log_message(self, *args):
        """Подавляет логирование запросов тестового HTTP-сервера."""
        pass


class _FlakyHandler(BaseHTTPRequestHandler):
    """На втором запросе отдаёт 503, остальные — успешные ответы."""

    def do_GET(self):
        self.server.requests += 1
        if self.server.requests == 2:
            self.send_response(503)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def log_message(self, *args):
        """Подавляет логирование запросов тестового HTTP-сервера."""
        pass


class _FileServer(HTTPServer):
    daemon_threads = True


class _FlakyServer(HTTPServer):
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.requests = 0


class _RedirectHandler(BaseHTTPRequestHandler):
    """На /start отдаёт 302 на /file.bin, остальные пути — PAYLOAD."""

    def do_GET(self):
        if self.path == "/start":
            self.send_response(302)
            self.send_header("Location", "/file.bin")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def log_message(self, *args):
        """Подавляет логирование запросов тестового HTTP-сервера."""
        pass


@pytest.fixture(scope="module")
def file_server():
    """Возвращает URL локального HTTP-сервера, отдающего файл (1 МБ)."""
    server = _FileServer(("127.0.0.1", 0), _FileHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/file.bin"
    server.shutdown()


@pytest.fixture(scope="module")
def closed_port_url():
    """Возвращает адрес, на котором гарантированно нет сервера (порт 1)."""
    return "http://127.0.0.1:1/unreachable.bin"


@pytest.fixture(scope="module")
def flaky_server():
    """URL сервера, у которого проваливается только второй запрос (503)."""
    server = _FlakyServer(("127.0.0.1", 0), _FlakyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/flaky.bin"
    server.shutdown()


@pytest.fixture(scope="module")
def redirect_server():
    """URL, где /start отдаёт 302 на /file.bin с PAYLOAD."""
    server = _FileServer(("127.0.0.1", 0), _RedirectHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/start"
    server.shutdown()


@pytest.fixture(scope="module")
def main_module(tmp_path_factory):
    """Собирает MainModule из тестового конфига (config -> logger)."""
    cfg_dir = tmp_path_factory.mktemp("config")
    config_path = cfg_dir / "config.yml"
    config_path.write_text(TEST_CONFIG, encoding="utf-8")

    return MainModule(config_path=config_path)
