"""backfill items.search_text

202607260019 `search_text` ustunini qo'shgan, lekin mavjud qatorlarni
to'ldirmagan — u faqat create/update'da yoziladi. Natijada eski lotlar
qidiruvda umuman chiqmasdi. Bu migratsiya ularni ilova ishlatadigan AYNAN
o'sha normallashtirish (`normalize_search`) bilan to'ldiradi.

Revision ID: 202610130021
Revises: 202610130020
Create Date: 2026-10-13 00:00:01.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.services.translit import normalize_search

# revision identifiers, used by Alembic.
revision: str = "202610130021"
down_revision: str | None = "202610130020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, title, description FROM items WHERE search_text IS NULL")
    ).all()
    for row in rows:
        parts = [part for part in (row.title, row.description) if part]
        if not parts:
            continue
        bind.execute(
            sa.text("UPDATE items SET search_text = :text WHERE id = :id"),
            {"text": normalize_search(" ".join(parts)), "id": row.id},
        )


def downgrade() -> None:
    # Ma'lumot backfill'i — qaytarish shart emas (ustun 202607260019 da o'chiriladi).
    pass
