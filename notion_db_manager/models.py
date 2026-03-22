from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DatabaseContext:
    database_id: str
    database_name: str
    properties: dict[str, dict[str, Any]]
    title_property: str
    order_property: str