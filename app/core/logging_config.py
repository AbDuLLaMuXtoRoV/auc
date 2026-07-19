"""Strukturaviy (JSON) logging sozlamasi — stdlib `logging` ustida, tashqi paketsiz.

Nega JSON: prod'da log'lar yig'uvchiga (Loki/ELK) tushadi; matnli log'ni parse qilish
mo'rt. Har yozuv bitta JSON qatori bo'lsa, filtr/qidiruv `request_id` bo'yicha ishonchli.
`json` moduli bilan qo'lda yozamiz — ortiqcha bog'liqlik kiritmaymiz.
"""

import json
import logging
from datetime import UTC, datetime

from app.core.request_context import request_id_var

# Handler'ni belgilash uchun nishon — configure_logging ikki marta chaqirilsa,
# handler'lar takrorlanmasin (idempotentlik).
_HANDLER_MARK = "_bazart_json_handler"


class JsonLogFormatter(logging.Formatter):
    """Har log record'ni bitta JSON qatorga aylantiradi.

    Maydonlar: ts (ISO8601, UTC), level, logger, msg, request_id. request_id
    contextvar'dan olinadi — joriy so'rov bo'lmasa None bo'ladi.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    """Root logger'ni JSON formatterli stream handler'ga sozlaydi.

    Idempotent: bir marta o'rnatilgan JSON handler'ni belgilaymiz (`_HANDLER_MARK`)
    va qayta chaqirilsa yangi handler qo'shmaymiz — aks holda har chaqiruvda log
    ikki, uch marta takrorlanardi.
    """
    root = logging.getLogger()
    root.setLevel(level)

    for handler in root.handlers:
        if getattr(handler, _HANDLER_MARK, False):
            handler.setLevel(level)
            handler.setFormatter(JsonLogFormatter())
            return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    handler.setLevel(level)
    setattr(handler, _HANDLER_MARK, True)
    root.addHandler(handler)
