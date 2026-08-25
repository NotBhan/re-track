import React, { ReactNode } from 'react';

export interface PanelProps {
  title: string;
  children: ReactNode;
}

export const PanelHeader: React.FC<{ title: string }> = ({ title }) => {
  return (
    <div className="panel-header">
      <h3>{title}</h3>
    </div>
  );
};

export const Panel: React.FC<PanelProps> = ({ title, children }) => {
  return (
    <div className="ui-panel">
      <PanelHeader title={title} />
      <div className="panel-body">{children}</div>
    </div>
  );
};
