"""Real-time qatlam — auksion kanallariga WebSocket orqali narx/holat yangilanishlari.

Yagona in-memory `ConnectionManager` (`manager`) shu paketda yashaydi.
"""

from app.realtime.manager import ConnectionManager, manager

__all__ = ["ConnectionManager", "manager"]
