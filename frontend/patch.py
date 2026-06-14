import sys

filepath = 'src/components/uhpc-trial/UhpcTrialCorrectionTab.vue'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update mix-grid
text = text.replace(
    '<div v-if="corrMix" class="mix-grid mix-grid--trial">',
    '<div v-if="corrMix" class="mix-grid mix-grid--trial" style="grid-template-columns: repeat(10, 1fr);">'
)

text = text.replace(
    '<div class="mix-grid" :class="needsCorr ? \'mix-grid--corrected\' : \'mix-grid--trial\'">',
    '<div class="mix-grid" :class="needsCorr ? \'mix-grid--corrected\' : \'mix-grid--trial\'" style="grid-template-columns: repeat(10, 1fr);">'
)

# 2. Add admixture cell
marker1 = """          <div v-for="k in matKeys" :key="k" class="mix-cell">
            <div class="mix-cell__head">{{ matLabels[k] }}</div>
            <div class="mix-cell__val">{{ fmt(corrMix[k as keyof typeof corrMix]) }}</div>
          </div>
          <div class="mix-cell mix-cell--total">"""
insert1 = """          <div v-for="k in matKeys" :key="k" class="mix-cell">
            <div class="mix-cell__head">{{ matLabels[k] }}</div>
            <div class="mix-cell__val">{{ fmt(corrMix[k as keyof typeof corrMix]) }}</div>
          </div>
          <div class="mix-cell">
            <div class="mix-cell__head">外加剂掺量(%)</div>
            <div class="mix-cell__val">{{ corrMix.admixture_pct !== undefined && corrMix.admixture_pct !== 0 ? fmt(corrMix.admixture_pct, 2) + '%' : '—' }}</div>
          </div>
          <div class="mix-cell mix-cell--total">"""
text = text.replace(marker1, insert1)


marker2 = """            <div v-for="k in matKeys" :key="k" class="mix-cell">
              <div class="mix-cell__head">{{ matLabels[k] }}</div>
              <div class="mix-cell__val">{{ fmt(labMix[k as keyof typeof labMix]) }}</div>
            </div>
            <div class="mix-cell mix-cell--total">"""
insert2 = """            <div v-for="k in matKeys" :key="k" class="mix-cell">
              <div class="mix-cell__head">{{ matLabels[k] }}</div>
              <div class="mix-cell__val">{{ fmt(labMix[k as keyof typeof labMix]) }}</div>
            </div>
            <div class="mix-cell">
              <div class="mix-cell__head">外加剂掺量(%)</div>
              <div class="mix-cell__val">{{ labMix.admixture_pct !== undefined && labMix.admixture_pct !== 0 ? fmt(labMix.admixture_pct, 2) + '%' : '—' }}</div>
            </div>
            <div class="mix-cell mix-cell--total">"""
text = text.replace(marker2, insert2)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)
print("python patched")
