from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ItemSpec:
    sku: str
    name: str
    category: str
    unit_weight_grams: int
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class CatalogItem:
    item_id: str
    spec: ItemSpec
    in_stock: bool = True
    location_bin: Optional[str] = None
