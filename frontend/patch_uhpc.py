import sys
from pathlib import Path

filepath = 'd:/Code/shuini_calculator/frontend/src/views/TrialUhpcView.vue'
text = Path(filepath).read_text(encoding='utf-8')

# 1. Add refs to UHPC
marker1 = """const corrBase = ref<CorrBase>('trial')
const measuredDensity = ref<number | null>(null)"""
insert1 = """const corrBase = ref<CorrBase>('trial')
const measuredDensity = ref<number | null>(null)

// ─── Workability Eval ──────────────────────────────────────────────
const evalStrength28d = ref<number | null>(null)
const evalSlump = ref<number | null>(null)
const evalSpread = ref<number | null>(null)
const evalWorkabilityDesc = ref<string>('')"""
text = text.replace(marker1, insert1)

# 2. Add to buildTrialSnapshot
marker2 = """    measuredDensity: measuredDensity.value,
    corrBase: corrBase.value,
  }
}"""
insert2 = """    measuredDensity: measuredDensity.value,
    corrBase: corrBase.value,
    evalStrength28d: evalStrength28d.value,
    evalSlump: evalSlump.value,
    evalSpread: evalSpread.value,
    evalWorkabilityDesc: evalWorkabilityDesc.value,
  }
}"""
text = text.replace(marker2, insert2)

# 3. Add to applyTrialSnapshot
marker3 = """  if (typeof s.corrBase === 'string' && ['trial', 'wbRec', 'sfRec'].includes(s.corrBase)) {
    corrBase.value = s.corrBase as CorrBase
  }
}"""
insert3 = """  if (typeof s.corrBase === 'string' && ['trial', 'wbRec', 'sfRec'].includes(s.corrBase)) {
    corrBase.value = s.corrBase as CorrBase
  }
  if (typeof s.evalStrength28d === 'number') evalStrength28d.value = s.evalStrength28d
  if (typeof s.evalSlump === 'number') evalSlump.value = s.evalSlump
  if (typeof s.evalSpread === 'number') evalSpread.value = s.evalSpread
  if (typeof s.evalWorkabilityDesc === 'string') evalWorkabilityDesc.value = s.evalWorkabilityDesc
}"""
text = text.replace(marker3, insert3)

# 4. Pass down to UhpcTrialCorrectionTab props
marker4 = """                  :needs-corr="needsCorr"
                  :lab-mix="labMix"
                  :design-str="designStr"
                  @update:corr-base="v => corrBase = v"
                  @update:measured-density="v => measuredDensity = v"
                />"""
insert4 = """                  :needs-corr="needsCorr"
                  :lab-mix="labMix"
                  :design-str="designStr"
                  :eval-strength28d="evalStrength28d"
                  :eval-slump="evalSlump"
                  :eval-spread="evalSpread"
                  :eval-workability-desc="evalWorkabilityDesc"
                  @update:corr-base="v => corrBase = v"
                  @update:measured-density="v => measuredDensity = v"
                  @update:eval-strength28d="v => evalStrength28d = v"
                  @update:eval-slump="v => evalSlump = v"
                  @update:eval-spread="v => evalSpread = v"
                  @update:eval-workability-desc="v => evalWorkabilityDesc = v"
                />"""
text = text.replace(marker4, insert4)

Path(filepath).write_text(text, encoding='utf-8')
print("UHPC View patched")
