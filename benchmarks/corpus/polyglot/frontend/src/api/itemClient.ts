export interface CatalogItemDTO {
  item_id: string;
  sku: string;
  name: string;
  category: string;
  in_stock: boolean;
  location_bin?: string;
}

export interface ItemFilterOptions {
  category?: string;
  inStockOnly?: boolean;
}

export async function fetchCatalogItems(filter?: ItemFilterOptions): Promise<CatalogItemDTO[]> {
  const dummyItems: CatalogItemDTO[] = [
    { item_id: 'ITM-01', sku: 'SKU-BOLT-10', name: 'M8 Steel Bolt', category: 'Fasteners', in_stock: true },
    { item_id: 'ITM-02', sku: 'SKU-NUT-10', name: 'M8 Steel Nut', category: 'Fasteners', in_stock: true },
  ];
  if (filter?.category) {
    return dummyItems.filter((i) => i.category === filter.category);
  }
  return dummyItems;
}

export async function fetchItemDetails(id: string): Promise<CatalogItemDTO | null> {
  const items = await fetchCatalogItems();
  return items.find((i) => i.item_id === id) || null;
}
