// Syntax-only preflight for model-authored source. Read JSON from stdin so the
// same parser is usable from the Python agent and server without temporary files.
const fs = require('node:fs');
const ts = require('typescript');
const postcss = require('postcss');

const files = JSON.parse(fs.readFileSync(0, 'utf8'));
const errors = [];
for (const [path, source] of files) {
  if (/\.(tsx|jsx|ts|js)$/i.test(path)) {
    const kind = /\.tsx$/i.test(path) ? ts.ScriptKind.TSX
      : /\.jsx$/i.test(path) ? ts.ScriptKind.JSX
      : /\.ts$/i.test(path) ? ts.ScriptKind.TS : ts.ScriptKind.JS;
    const tree = ts.createSourceFile(path, source, ts.ScriptTarget.Latest, true, kind);
    for (const diagnostic of tree.parseDiagnostics) {
      const pos = tree.getLineAndCharacterOfPosition(diagnostic.start || 0);
      errors.push(`[${path}] ${ts.flattenDiagnosticMessageText(diagnostic.messageText, ' ')} at ${pos.line + 1}:${pos.character + 1}`);
    }
  } else if (/\.css$/i.test(path)) {
    if (!source.trim()) errors.push(`[${path}] CSS is empty`);
    if (/^\s*\/\*\s*(?:empty\s+)?(?:styles?|css|placeholder|todo)(?:\s+(?:go(?:es)?\s+)?here)?\s*\*\/\s*$/i.test(source)) {
      errors.push(`[${path}] CSS contains only a placeholder comment`);
    }
    // PostCSS deliberately treats unknown selectors as legal; HTML envelopes
    // and model continuation markers need explicit rejection as well. Ignore
    // quoted strings (e.g. a legitimate SVG data URL or `content: "<"`).
    const outsideStrings = source.replace(/"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'/g, '""');
    if (/<\/?(?:!doctype|[a-z][\w-]*)\b/i.test(outsideStrings)) {
      errors.push(`[${path}] HTML tag/delimiter is not CSS`);
    }
    if (/(?:^|\n)\s*(?:\.\.\.|```(?:css)?|\/\*\s*(?:todo|placeholder|insert (?:your )?css|(?:css|styles?) (?:go(?:es)? )?(?:here|omitted))\b[^*]*\*\/)\s*(?:\n|$)/im.test(source)) {
      errors.push(`[${path}] CSS contains a placeholder instead of styles`);
    }
    try {
      postcss.parse(source, { from: path });
    } catch (error) {
      errors.push(`[${path}] ${error.reason || error.message} at ${error.line || '?'}:${error.column || '?'}`);
    }
  }
}
process.stdout.write(JSON.stringify(errors));
