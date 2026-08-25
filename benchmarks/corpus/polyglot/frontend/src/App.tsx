import React from 'react';
import { ItemList } from './views/ItemList';

export const App: React.FC = () => {
  return (
    <div className="polyglot-app">
      <header>
        <h2>Catalog Console</h2>
      </header>
      <main>
        <ItemList />
      </main>
    </div>
  );
};

export default App;
