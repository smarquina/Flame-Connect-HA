import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import ts from 'typescript';
import { noBrowserGlobals } from './core-globals.mjs';

const CORE_ROOTS = ['src/domain', 'src/application'];
function files(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory() ? files(join(directory, entry.name)) : [join(directory, entry.name)],
  );
}
function checkDependency(file, directory, dependency) {
  const target = relative(resolve('src'), resolve(dirname(file), dependency)).replaceAll('\\', '/');
  const allowed =
    target.startsWith('domain/') ||
    (directory.endsWith('application') && target.startsWith('application/'));
  if (!dependency.startsWith('.') || !allowed)
    throw new Error(`${file}: forbidden inward dependency ${dependency}`);
}
function moduleArgument(node) {
  if (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) return node.moduleSpecifier;
  if (ts.isImportTypeNode(node)) return node.argument.literal;
  if (
    ts.isCallExpression(node) &&
    (node.expression.kind === ts.SyntaxKind.ImportKeyword ||
      (ts.isIdentifier(node.expression) && node.expression.text === 'require'))
  )
    return node.arguments[0];
  return undefined;
}
for (const directory of CORE_ROOTS) {
  for (const file of files(directory)) {
    const source = ts.createSourceFile(
      file,
      readFileSync(file, 'utf8'),
      ts.ScriptTarget.Latest,
      true,
    );
    noBrowserGlobals(file, source);
    function visit(node) {
      const argument = moduleArgument(node);
      if (argument) {
        if (!ts.isStringLiteralLike(argument))
          throw new Error(`${file}: forbidden inward dependency: nonliteral module`);
        checkDependency(file, directory, argument.text);
      }

      ts.forEachChild(node, visit);
    }
    visit(source);
  }
}
console.log('Architecture boundaries verified.');
