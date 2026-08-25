import React from 'react';
import { BoardProvider } from './context/BoardContext';
import { TaskBoard } from './components/TaskBoard';

export const App: React.FC = () => {
  return (
    <main className="app-container">
      <header>
        <h1>Engineering Task Board</h1>
      </header>
      <BoardProvider>
        <TaskBoard boardName="Sprint Tasks" />
      </BoardProvider>
    </main>
  );
};

export default App;
