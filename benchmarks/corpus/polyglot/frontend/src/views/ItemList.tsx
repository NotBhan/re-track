import React, { useEffect, useState } from 'react';
import { CatalogItemDTO, fetchCatalogItems } from '../api/itemClient';

export interface ItemListProps {
  initialCategory?: string;
}

export const ItemList: React.FC<ItemListProps> = ({ initialCategory }) => {
  const [items, setItems] = useState<CatalogItemDTO[]>([]);

  useEffect(() => {
    fetchCatalogItems({ category: initialCategory }).then(setItems);
  }, [initialCategory]);

  return (
    <div className="item-list-view">
      <h3>Inventory Catalog</h3>
      <ul>
        {items.map((item) => (
          <li key={item.item_id} className="catalog-row">
            <span>{item.name}</span> - <span>{item.sku}</span> (
            {item.in_stock ? 'In Stock' : 'Out of Stock'})
          </li>
        ))}
      </ul>
    </div>
  );
};
