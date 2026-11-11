import ts from 'typescript';
export function noBrowserGlobals(file, source) {
  const host = ts.createCompilerHost({ noLib: true });
  host.getSourceFile = (name) => (name === file ? source : undefined);
  const program = ts.createProgram([file], { noLib: true }, host);
  const checker = program.getTypeChecker();
  const globals = new Set(['window', 'document', 'localStorage', 'fetch']);
  function visit(node) {
    if (ts.isIdentifier(node) && globals.has(node.text)) {
      const namedProperty =
        node.parent.name === node && !ts.isShorthandPropertyAssignment(node.parent);
      if (!namedProperty && !checker.getSymbolAtLocation(node))
        throw new Error(`${file}: browser dependency in core`);
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
}
