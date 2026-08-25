import { ASTNode, SyntaxTree } from '../../shared/src/types';

export class CodeParser {
  public parseSource(sourcePath: string, code: string): SyntaxTree {
    const rootNode: ASTNode = {
      type: 'Program',
      value: code.slice(0, 20),
      start: { line: 1, column: 0 },
      end: { line: 1, column: code.length },
      children: [],
    };

    return {
      sourcePath,
      root: rootNode,
      nodeCount: 1,
    };
  }
}
