from typing import Optional

from backend.app.models.item import CatalogItem, ItemSpec


class InMemoryCatalogStore:
    def __init__(self) -> None:
        self._items: dict[str, CatalogItem] = {}

    def insert(self, item: CatalogItem) -> None:
        self._items[item.item_id] = item

    def get(self, item_id: str) -> Optional[CatalogItem]:
        return self._items.get(item_id)

    def all(self) -> list[CatalogItem]:
        return list(self._items.values())


class CatalogService:
    def __init__(self, store: InMemoryCatalogStore) -> None:
        self.store = store

    def list_items(self) -> list[CatalogItem]:
        return self.store.all()

    def get_item(self, item_id: str) -> Optional[CatalogItem]:
        return self.store.get(item_id)

    def register_item(self, item_id: str, spec: ItemSpec) -> CatalogItem:
        item = CatalogItem(item_id=item_id, spec=spec)
        self.store.insert(item)
        return item
