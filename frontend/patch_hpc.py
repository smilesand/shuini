import sys

filepath = 'd:/Code/shuini_calculator/frontend/src/composables/useHpcTrial.ts'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update interface TrialInputSnapshot
marker1 = """  measuredDensity: NullableNumber
}"""
insert1 = """  measuredDensity: NullableNumber
  evalStrength28d: NullableNumber
  evalSlump: NullableNumber
  evalSpread: NullableNumber
  evalWorkabilityDesc: string
}"""
text = text.replace(marker1, insert1)

# 2. Add refs
marker2 = """  const measuredDensity = ref<NullableNumber>(null)"""
insert2 = """  const measuredDensity = ref<NullableNumber>(null)
  const evalStrength28d = ref<NullableNumber>(null)
  const evalSlump = ref<NullableNumber>(null)
  const evalSpread = ref<NullableNumber>(null)
  const evalWorkabilityDesc = ref<string>('')"""
text = text.replace(marker2, insert2)

# 3. Add to getInputs
marker3 = """      measuredDensity: measuredDensity.value,
    }
  })"""
insert3 = """      measuredDensity: measuredDensity.value,
      evalStrength28d: evalStrength28d.value,
      evalSlump: evalSlump.value,
      evalSpread: evalSpread.value,
      evalWorkabilityDesc: evalWorkabilityDesc.value,
    }
  })"""
text = text.replace(marker3, insert3)

# 4. Add to setInputs
marker4 = """    measuredDensity.value = toNullableNumber(inputs.measuredDensity)
  }"""
insert4 = """    measuredDensity.value = toNullableNumber(inputs.measuredDensity)
    evalStrength28d.value = toNullableNumber(inputs.evalStrength28d)
    evalSlump.value = toNullableNumber(inputs.evalSlump)
    evalSpread.value = toNullableNumber(inputs.evalSpread)
    if (typeof inputs.evalWorkabilityDesc === 'string') {
      evalWorkabilityDesc.value = inputs.evalWorkabilityDesc
    } else {
      evalWorkabilityDesc.value = ''
    }
  }"""
text = text.replace(marker4, insert4)

# 5. Add to resetData
marker5 = """    measuredDensity.value = null
  }"""
insert5 = """    measuredDensity.value = null
    evalStrength28d.value = null
    evalSlump.value = null
    evalSpread.value = null
    evalWorkabilityDesc.value = ''
  }"""
text = text.replace(marker5, insert5)

# 6. Add to context return
marker6 = """    trialLabMix,

    calculate,"""
insert6 = """    evalStrength28d,
    evalSlump,
    evalSpread,
    evalWorkabilityDesc,

    trialLabMix,

    calculate,"""
text = text.replace(marker6, insert6)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("HPC composable patched")