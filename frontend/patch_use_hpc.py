import sys
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/composables/useHpcTrial.ts'
text = Path(path).read_text(encoding='utf-8')

marker1 = """        wbAdj: wbAdj.value,
        mbAdj: mbAdj.value,
        sandRatioAdj: sandRatioAdj.value,
        alphaAdj: alphaAdj.value,
        measuredDensity: measuredDensity.value,
      },
      calculated: calculated.value,"""

insert1 = """        wbAdj: wbAdj.value,
        mbAdj: mbAdj.value,
        sandRatioAdj: sandRatioAdj.value,
        alphaAdj: alphaAdj.value,
        measuredDensity: measuredDensity.value,
        evalStrength28d: evalStrength28d.value,
        evalSlump: evalSlump.value,
        evalSpread: evalSpread.value,
        evalWorkabilityDesc: evalWorkabilityDesc.value,
      },
      calculated: calculated.value,"""

text = text.replace(marker1, insert1)


marker2 = """  return {
    loading,
    error,
    hasData,
    wbVal,"""

insert2 = """  return {
    loading,
    error,
    hasData,
    wbVal,
    evalStrength28d,
    evalSlump,
    evalSpread,
    evalWorkabilityDesc,"""

text = text.replace(marker2, insert2)

Path(path).write_text(text, encoding='utf-8')
print("useHpcTrial.ts patched")