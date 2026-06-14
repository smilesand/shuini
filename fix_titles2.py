# Fix the broken title attributes by replacing inner ASCII " with Chinese corner brackets
import re

files = [
    r'd:\Code\shuini_calculator\frontend\src\components\hpc-trial\HpcTrialCorrectionTab.vue',
    r'd:\Code\shuini_calculator\frontend\src\components\hpc-trial\HpcTrialStrengthTab.vue',
    r'd:\Code\shuini_calculator\frontend\src\components\hpc-trial\HpcTrialWorkabilityTab.vue',
]

for path in files:
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    lines = c.split('\n')
    changed = False
    for i, line in enumerate(lines):
        # Find title="..." lines that have the broken inner quotes around 配比计算
        if 'title=' in line and '\u914d\u6bd4\u8ba1\u7b97' in line:
            # The title attribute pattern: outer " at positions 0 and last of title value
            # Example: title="请先在"配比计算 → 高性能混凝土"中完成..."
            # We need to find the full attribute value across the whole title attr
            # Strategy: extract everything after title=" and before the final "
            # The line pattern is: <spaces>title="AAA"BBB"CCC"
            # where " are at positions: outer-open, inner-open, inner-close, outer-close
            # Find full title attribute using the fact it ends at the last " on the line
            m = re.search(r'title="(.*)"', line)
            if m:
                val = m.group(1)
                # val contains the full content with inner quotes
                # Replace the inner " pair around 配比计算 → 高性能混凝土 with corner brackets
                val_fixed = re.sub(r'"(\u914d\u6bd4\u8ba1\u7b97[^"]*)"', r'「\1」', val)
                new_line = line[:m.start()] + 'title="' + val_fixed + '"' + line[m.end():]
                lines[i] = new_line
                print(f'Fixed L{i+1} in {path.split(chr(92))[-1]}')
                print(f'  Before: {line.strip()[:80]}')
                print(f'  After:  {new_line.strip()[:80]}')
                changed = True
    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

print('\nDone')
