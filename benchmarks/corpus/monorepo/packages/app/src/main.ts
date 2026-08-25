import { WorkspaceView } from './WorkspaceView';

export function initializeWorkspaceApp(): string {
  const view = WorkspaceView;
  return `Workspace initialized with ${view.name}`;
}

export const appState = initializeWorkspaceApp();
