const fs = require('fs');
let file = 'd:/Code/shuini_calculator/frontend/src/api/calc.ts';
let text = fs.readFileSync(file, 'utf-8');
text = text.replace(
`  binder: number
  total: number
}`,
`  binder: number
  total: number
  admixture_pct?: number
}`);
fs.writeFileSync(file, text);
console.log('done calc.ts')