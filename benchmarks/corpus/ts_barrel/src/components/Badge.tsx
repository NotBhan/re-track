import React from 'react';

export interface BadgeProps {
  label: string;
  variant?: 'info' | 'success' | 'warning';
}

export function formatBadgeLabel(label: string): string {
  return label.trim().toUpperCase();
}

export const Badge: React.FC<BadgeProps> = ({ label, variant = 'info' }) => {
  return (
    <span className={`ui-badge ui-badge-${variant}`}>
      {formatBadgeLabel(label)}
    </span>
  );
};

export default Badge;
