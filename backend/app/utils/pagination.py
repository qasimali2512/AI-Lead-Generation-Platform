from __future__ import annotations

import math


def calculate_pagination(
    *,
    page: int,
    page_size: int,
    total: int,
) -> dict:
    total_pages = (
        math.ceil(total / page_size)
        if total > 0
        else 0
    )

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": (
            page < total_pages
        ),
        "has_previous": (
            page > 1 and total_pages > 0
        ),
    }