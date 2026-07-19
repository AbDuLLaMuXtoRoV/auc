"""So'rov konteksti: joriy HTTP so'rovning request_id'sini contextvar orqali tashuvchi.

Nega contextvar: log formatter (logging_config) so'rov obyektiga to'g'ridan-to'g'ri
kira olmaydi. Middleware har so'rovda request_id'ni bu yerga o'rnatadi, formatter esa
undan o'qiydi — shu tariqa har log yozuvi qaysi so'rovga tegishli ekani bilinadi.
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Joriy so'rovning request_id'si. So'rov tashqarisida (masalan startup) None.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Sarlavha nomi — kiruvchi propagatsiya ham, chiquvchi javob ham shuni ishlatadi.
REQUEST_ID_HEADER = "X-Request-Id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Har HTTP so'rovga request_id biriktiradi.

    - Kiruvchi `X-Request-Id` bo'lsa — o'shani ishlatadi (tarqatilgan tracing uchun
      propagatsiya). Bo'lmasa `uuid4` generatsiya qiladi.
    - contextvar'ga o'rnatadi (log formatter o'qiydi), javobga o'sha sarlavhani qaytaradi.
    - So'rov tugagach contextvar'ni token orqali reset qiladi — oqim (thread/task)
      qayta ishlatilganda eski qiymat sizib chiqmasligi uchun.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming if incoming else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
