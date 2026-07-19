"""Strukturaviy logging + request_id middleware testlari.

Tekshiriladi: X-Request-Id javobda bor, kiruvchi qiymat propagatsiya bo'ladi,
configure_logging idempotent, JSON formatter to'g'ri JSON + request_id chiqaradi.
"""

import json
import logging

from fastapi.testclient import TestClient

from app.core.logging_config import JsonLogFormatter, configure_logging
from app.core.request_context import request_id_var


def test_response_has_request_id_header(client: TestClient) -> None:
    """Har javobda X-Request-Id sarlavhasi bo'lishi va bo'sh bo'lmasligi kerak."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-Id")


def test_request_id_is_propagated(client: TestClient) -> None:
    """Kiruvchi X-Request-Id aynan o'sha qiymat bilan qaytarilishi kerak."""
    response = client.get("/api/v1/health", headers={"X-Request-Id": "my-trace-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "my-trace-123"


def test_generated_ids_are_unique(client: TestClient) -> None:
    """Sarlavhasiz ikki so'rov har xil (avto-generatsiya qilingan) id olishi kerak."""
    first = client.get("/api/v1/health").headers["X-Request-Id"]
    second = client.get("/api/v1/health").headers["X-Request-Id"]
    assert first != second


def test_configure_logging_is_idempotent() -> None:
    """configure_logging ikki marta chaqirilsa handler soni ortmasligi kerak."""
    configure_logging()
    root = logging.getLogger()
    before = len(root.handlers)
    configure_logging()
    after = len(root.handlers)
    assert after == before


def test_formatter_outputs_valid_json_with_request_id() -> None:
    """Formatter chiqishi to'g'ri JSON bo'lishi va request_id maydonini o'z ichiga olishi kerak."""
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="salom %s",
        args=("dunyo",),
        exc_info=None,
    )
    token = request_id_var.set("trace-abc")
    try:
        line = formatter.format(record)
    finally:
        request_id_var.reset(token)

    parsed = json.loads(line)
    assert parsed["msg"] == "salom dunyo"
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test.logger"
    assert parsed["request_id"] == "trace-abc"
    assert "ts" in parsed


def test_formatter_request_id_none_outside_request() -> None:
    """So'rov tashqarisida request_id None bo'lishi, ammo JSON haqiqiy bo'lishi kerak."""
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="ogohlantirish",
        args=(),
        exc_info=None,
    )
    parsed = json.loads(formatter.format(record))
    assert parsed["request_id"] is None
    assert parsed["level"] == "WARNING"
