import React, { createContext, useState, ReactNode } from 'react';
import { TaskItem } from '../components/TaskCard';

export interface BoardState {
  boardId: string;
  tasks: TaskItem[];
}

export interface BoardContextValue {
  tasks: TaskItem[];
  addTask: (task: TaskItem) => void;
  updateTaskStatus: (id: string, status: TaskItem['status']) => void;
}

export const BoardContext = createContext<BoardContextValue | undefined>(undefined);

export const BoardProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [tasks, setTasks] = useState<TaskItem[]>([
    { id: 'T-1', title: 'Parse AST', description: 'Extract node hierarchy', status: 'done' },
    { id: 'T-2', title: 'Link Modules', description: 'Cross-module symbol linking', status: 'in_progress' },
  ]);

  const addTask = (task: TaskItem) => {
    setTasks((prev) => [...prev, task]);
  };

  const updateTaskStatus = (id: string, status: TaskItem['status']) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status } : t))
    );
  };

  return (
    <BoardContext.Provider value={{ tasks, addTask, updateTaskStatus }}>
      {children}
    </BoardContext.Provider>
  );
};
