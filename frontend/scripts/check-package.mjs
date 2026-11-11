import assert from 'node:assert/strict';
import ts from 'typescript';
import { readFileSync, readdirSync, statSync } from 'node:fs';
const pkg = JSON.parse(readFileSync('package.json', 'utf8'));
const filename = `${pkg.name}.js`;
assert.equal(filename, 'flame-connect-card.js');
assert.deepEqual(readdirSync('dist'), ['flame-connect-card.js']);
const source = readFileSync(`dist/${filename}`, 'utf8');
assert(
  source.includes('data:image/png;base64,'),
  'The four supplied fireplace states must be bundled.',
);
const syntax = ts.createSourceFile(
  'bundle.js',
  source,
  ts.ScriptTarget.Latest,
  true,
  ts.ScriptKind.JS,
);
function visit(node) {
  assert(
    !(
      ts.isImportDeclaration(node) ||
      (ts.isExportDeclaration(node) && node.moduleSpecifier) ||
      (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword)
    ),
    'No external or missing module dependencies.',
  );
  ts.forEachChild(node, visit);
}
visit(syntax);
assert(statSync(`dist/${filename}`).size < 2_500_000, 'Distribution must stay below 2.5 MB.');
console.log(`Verified self-contained ${filename} (${pkg.version}).`);
