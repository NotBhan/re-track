import React from 'react';

export interface TaskItem {
  id: string;
  title: string;
  description: string;
  status: 'todo' | 'in_progress' | 'done';
}

export interface TaskCardProps {
  task: TaskItem;
  onStatusChange?: (id: string, newStatus: TaskItem['status']) => void;
}

export function formatTaskSummary(task: TaskItem): string {
  return `[${task.status.toUpperCase()}] ${task.title} - ${task.description}`;
}

export const TaskCard: React.FC<TaskCardProps> = ({ task, onStatusChange }) => {
  return (
    <div className="task-card">
      <h4>{task.title}</h4>
      <p>{task.description}</p>
      <span className={`badge status-${task.status}`}>{task.status}</span>
      {onStatusChange && (
        <button onClick={() => onStatusChange(task.id, 'done')}>Mark Done</button>
      )}
    </div>
  );
};
