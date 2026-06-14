const fs = require('fs');

const filepath = 'd:/Code/shuini_calculator/frontend/src/components/uhpc-trial/UhpcTrialCorrectionTab.vue';
let text = fs.readFileSync(filepath, 'utf-8');

const marker1 = `<div v-if="corrMix" class="mix-grid mix-grid--trial">
          <div v-for="k in matKeys" :key="k" class="mix-cell">
            <div class="mix-cell__head">{{ matLabels[k] }}</div>
            <div class="mix-cell__val">{{ fmt(corrMix[k as keyof typeof corrMix]) }}</div>
          </div>
          <div class="mix-cell mix-cell--total">
            <div class="mix-cell__head">合计</div>
            <div class="mix-cell__val">{{ fmt(corrMix.total) }}</div>
          </div>
        </div>`;

const repl1 = `<div v-if="corrMix" class="mix-grid mix-grid--trial" style="grid-template-columns: repeat(10, 1fr);">
          <div v-for="k in matKeys" :key="k" class="mix-cell">
            <div class="mix-cell__head">{{ matLabels[k] }}</div>
            <div class="mix-cell__val">{{ fmt(corrMix[k as keyof typeof corrMix]) }}</div>
          </div>
          <div class="mix-cell">
            <div class="mix-cell__head">外加剂(%)</div>
            <div class="mix-cell__val">{{ corrMix.admixture_pct !== undefined ? fmt(corrMix.admixture_pct, 2) + '%' : '—' }}</div>
          </div>
          <div class="mix-cell mix-cell--total">
            <div class="mix-cell__head">合计</div>
            <div class="mix-cell__val">{{ fmt(corrMix.total) }}</div>
          </div>
        </div>`;

const marker2 = `<div class="mix-grid" :class="needsCorr ? 'mix-grid--corrected' : 'mix-grid--trial'">
            <div v-for="k in matKeys" :key="k" class="mix-cell">
              <div class="mix-cell__head">{{ matLabels[k] }}</div>
              <div class="mix-cell__val">{{ fmt(labMix[k as keyof typeof labMix]) }}</div>
            </div>
            <div class="mix-cell mix-cell--total">
              <div class="mix-cell__head">合计</div>
              <div class="mix-cell__val">{{ fmt(labMix.total) }}</div>
            </div>
          </div>`;

const repl2 = `<div class="mix-grid" :class="needsCorr ? 'mix-grid--corrected' : 'mix-grid--trial'" style="grid-template-columns: repeat(10, 1fr);">
            <div v-for="k in matKeys" :key="k" class="mix-cell">
              <div class="mix-cell__head">{{ matLabels[k] }}</div>
              <div class="mix-cell__val">{{ fmt(labMix[k as keyof typeof labMix]) }}</div>
            </div>
            <div class="mix-cell">
              <div class="mix-cell__head">外加剂(%)</div>
              <div class="mix-cell__val">{{ labMix.admixture_pct !== undefined ? fmt(labMix.admixture_pct, 2) + '%' : '—' }}</div>
            </div>
            <div class="mix-cell mix-cell--total">
              <div class="mix-cell__head">合计</div>
              <div class="mix-cell__val">{{ fmt(labMix.total) }}</div>
            </div>
          </div>`;

text = text.replace(marker1, repl1);
text = text.replace(marker2, repl2);

fs.writeFileSync(filepath, text);
console.log('patched vue');
