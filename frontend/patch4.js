const fs = require('fs');

const filepath = 'src/components/uhpc-trial/UhpcTrialCorrectionTab.vue';
let text = fs.readFileSync(filepath, 'utf-8');

text = text.replace(
  '        <div v-if="corrMix" class="mix-grid mix-grid--trial">',
  '        <div v-if="corrMix" class="mix-grid mix-grid--trial" style="grid-template-columns: repeat(10, 1fr);">'
);

let insert = `
          <div class="mix-cell">
            <div class="mix-cell__head">外加剂(%)</div>
            <div class="mix-cell__val">{{ corrMix.admixture_pct !== undefined ? fmt(corrMix.admixture_pct, 2) + '%' : '—' }}</div>
          </div>
          <div class="mix-cell mix-cell--total">`;
text = text.replace('          <div class="mix-cell mix-cell--total">', insert);


text = text.replace(
  '          <div class="mix-grid" :class="needsCorr ? \\\'mix-grid--corrected\\' : \\\'mix-grid--trial\\\'">',
  '          <div class="mix-grid" :class="needsCorr ? \\\'mix-grid--corrected\\' : \\\'mix-grid--trial\\\'" style="grid-template-columns: repeat(10, 1fr);">'
);

let insert2 = `
              <div class="mix-cell">
                <div class="mix-cell__head">外加剂(%)</div>
                <div class="mix-cell__val">{{ labMix.admixture_pct !== undefined ? fmt(labMix.admixture_pct, 2) + '%' : '—' }}</div>
              </div>
              <div class="mix-cell mix-cell--total">`;
text = text.split('              <div class="mix-cell mix-cell--total">').join(insert2);

// Only insert2 was split/joined, wait, I need to make sure I don't duplicate. Wait, the first one I used replace which only replaces first instance.
// But the second one is deeply nested. Let's just write a python script. It's safer.
fs.writeFileSync(filepath, text);
console.log('regex patched');