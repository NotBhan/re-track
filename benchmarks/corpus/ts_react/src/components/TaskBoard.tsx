import React from 'react';
import { TaskCard, TaskItem } from './TaskCard';
import { useBoard } from '../hooks/useBoard';

export interface TaskBoardProps {
  boardName: string;
}

export const TaskBoard: React.FC<TaskBoardProps> = ({ boardName }) => {
  const { tasks, updateTaskStatus } = useBoard();

  return (
    <section className="task-board">
      <h2>{boardName}</h2>
      <div className="task-columns">
        {tasks.map((task: TaskItem) => (
          <TaskCard
            key={task.id}
            task={task}
            onStatusChange={updateTaskStatus}
          />
        ))}
      </div>
    </section>
  );
};
