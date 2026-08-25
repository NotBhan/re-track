export interface TokenPosition {
  line: number;
  column: number;
}

export interface ASTNode {
  type: string;
  value?: string;
  start: TokenPosition;
  end: TokenPosition;
  children: ASTNode[];
}

export interface SyntaxTree {
  sourcePath: string;
  root: ASTNode;
  nodeCount: number;
}
