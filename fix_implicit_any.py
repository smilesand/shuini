import re

files = {
    r'd:\Code\shuini_calculator\frontend\src\components\tabs\TabAggregate.vue': [
        r"@update:model-value=\"v => store\.vg = v \?\? null\"",
        r"@update:model-value=\"v => store\.rhog = v \?\? null\"",
        r"@update:model-value=\"v => store\.rhos = v \?\? null\"",
    ],
    r'd:\Code\shuini_calculator\frontend\src\components\tabs\TabBinder.vue': [
        r"@update:model-value=\"v => store\.b1p = v \?\? 0\"",
        r"@update:model-value=\"v => store\.rho1 = v \?\? 2200\"",
        r"@update:model-value=\"v => store\.b2p = v \?\? 0\"",
        r"@update:model-value=\"v => store\.rho2 = v \?\? 2900\"",
        r"@update:model-value=\"v => store\.b3p = v \?\? 0\"",
        r"@update:model-value=\"v => store\.rho3 = v \?\? 2600\"",
        r"@update:model-value=\"v => store\.b4p = v \?\? 0\"",
        r"@update:model-value=\"v => store\.rho4 = v \?\? 2200\"",
        r"@update:model-value=\"v => store\.rhoc = v \?\? null\"",
        r"@update:model-value=\"v => store\.va = v \?\? 0\.01\"",
    ],
    r'd:\Code\shuini_calculator\frontend\src\components\tabs\TabWaterBinder.vue': [
        r"@update:model-value=\"v => store\.fcuk = v \?\? null\"",
        r"@update:model-value=\"v => store\.fb = v \?\? null\"",
    ],
    r'd:\Code\shuini_calculator\frontend\src\components\tabs\TabSandRatio.vue': [
        r"@update:model-value=\"v => store\.sandRatioInput = v \?\? null\"",
    ],
    r'd:\Code\shuini_calculator\frontend\src\components\tabs\TabWaterAdmix.vue': [
        r"@update:model-value=\"v => store\.alpha = v \?\? null\"",
    ],
}

for path, patterns in files.items():
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    changed = False
    for pattern in patterns:
        replacement = pattern.replace(r"\"v =>", r"\"(v: number | undefined) =>")
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changed = True
            content = new_content
    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Fixed: {path.split(chr(92))[-1]}')
    else:
        print(f'No changes: {path.split(chr(92))[-1]}')

print('Done')
