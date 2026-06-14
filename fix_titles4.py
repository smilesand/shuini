files_and_fixes = [
    (
        r'd:\Code\shuini_calculator\frontend\src\components\hpc-trial\HpcTrialCorrectionTab.vue',
        '      title="请先在配比计算 \u2192 高性能混凝土中完成配合比计算，之后再回到本页进行试配调整。"',
    ),
    (
        r'd:\Code\shuini_calculator\frontend\src\components\hpc-trial\HpcTrialStrengthTab.vue',
        '      title="请先在配比计算 \u2192 高性能混凝土中完成配合比计算。"',
    ),
    (
        r'd:\Code\shuini_calculator\frontend\src\components\hpc-trial\HpcTrialWorkabilityTab.vue',
        '      title="请先在配比计算 \u2192 高性能混凝土中完成配合比计算，之后再回到本页进行工作性实验。"',
    ),
]

for path, new_title_line in files_and_fixes:
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    changed = False
    for i, line in enumerate(lines):
        if 'title=' in line and '\u914d\u6bd4\u8ba1\u7b97' in line:
            lines[i] = new_title_line + '\n'
            print(f'Fixed {path.split(chr(92))[-1]} L{i+1}')
            changed = True
            break
    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

print('Done')
