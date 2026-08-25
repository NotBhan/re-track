import React, { useState } from 'react';
import { CodeParser } from '../../core/src/index';
import { TreeView } from '../../ui/src/index';
import { SyntaxTree } from '../../shared/src/types';

export const WorkspaceView: React.FC = () => {
  const [parser] = useState(() => new CodeParser());
  const [tree, setTree] = useState<SyntaxTree>(() =>
    parser.parseSource('example.ts', 'const x = 42;')
  );

  return (
    <div className="workspace-view">
      <h3>Developer Tooling Workspace</h3>
      <TreeView tree={tree} />
    </div>
  );
};
