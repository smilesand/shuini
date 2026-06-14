import sys
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/composables/useHpcTrial.ts'
text = Path(path).read_text(encoding='utf-8')

marker = """      sandRatioAdj.value = toNullableNumber(inputs.sandRatioAdj)
      alphaAdj.value = toNullableNumber(inputs.alphaAdj)
      measuredDensity.value = toNullableNumber(inputs.measuredDensity)"""

insert = """      sandRatioAdj.value = toNullableNumber(inputs.sandRatioAdj)
      alphaAdj.value = toNullableNumber(inputs.alphaAdj)
      measuredDensity.value = toNullableNumber(inputs.measuredDensity)
      evalStrength28d.value = toNullableNumber(inputs.evalStrength28d)
      evalSlump.value = toNullableNumber(inputs.evalSlump)
      evalSpread.value = toNullableNumber(inputs.evalSpread)
      evalWorkabilityDesc.value = toStringValue(inputs.evalWorkabilityDesc, '')"""

text = text.replace(marker, insert)
Path(path).write_text(text, encoding='utf-8')
print("useHpcTrial snapshot updated")