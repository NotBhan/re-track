from typing import Any, Optional

from backend.app.models.item import CatalogItem, ItemSpec
from backend.app.services.catalog import CatalogService, InMemoryCatalogStore


_default_store = InMemoryCatalogStore()
_default_service = CatalogService(_default_store)


def get_catalog_items() -> list[dict[str, Any]]:
    items = _default_service.list_items()
    return [
        {
            "item_id": it.item_id,
            "sku": it.spec.sku,
            "name": it.spec.name,
            "category": it.spec.category,
            "in_stock": it.in_stock,
        }
        for it in items
    ]


def get_item_by_id(item_id: str) -> Optional[dict[str, Any]]:
    it = _default_service.get_item(item_id)
    if not it:
        return None
    return {
        "item_id": it.item_id,
        "sku": it.spec.sku,
        "name": it.spec.name,
        "category": it.spec.category,
        "in_stock": it.in_stock,
        "location_bin": it.location_bin,
    }


def create_catalog_item(item_id: str, sku: str, name: str, category: str, weight: int) -> dict[str, Any]:
    spec = ItemSpec(sku=sku, name=name, category=category, unit_weight_grams=weight)
    created = _default_service.register_item(item_id=item_id, spec=spec)
    return {"status": "created", "item_id": created.item_id}
