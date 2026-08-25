import React from 'react';
import { ASTNode, SyntaxTree } from '../../shared/src/types';

export interface TreeViewProps {
  tree: SyntaxTree;
  onSelectNode?: (node: ASTNode) => void;
}

export const TreeView: React.FC<TreeViewProps> = ({ tree, onSelectNode }) => {
  return (
    <div className="ast-tree-view">
      <h4>Syntax Tree: {tree.sourcePath}</h4>
      <div className="node-item" onClick={() => onSelectNode?.(tree.root)}>
        <span>{tree.root.type}</span>
      </div>
    </div>
  );
};
