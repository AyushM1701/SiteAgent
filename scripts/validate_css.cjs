const fs = require('node:fs');
const postcss = require('postcss');
try {
  const root = postcss.parse(fs.readFileSync(0, 'utf8'));
  const sharedSelectors = [];
  root.walkRules(rule => {
    let parent = rule.parent;
    while (parent) {
      if (parent.type === 'atrule' && /^(scope|.*keyframes)$/i.test(parent.name)) return;
      parent = parent.parent;
    }
    for (const selector of rule.selectors) {
      if (/^\.(section__(?:inner|header|title)|btn)(?![\w-])/.test(selector.trim())) sharedSelectors.push(selector);
    }
  });
  process.stdout.write(JSON.stringify({errors: [], sharedSelectors}));
} catch (error) {
  process.stdout.write(JSON.stringify({errors: [`${error.reason || error.message} at ${error.line || '?'}:${error.column || '?'}`]}));
}
