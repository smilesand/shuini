import re

fixes = {
    r'd:\Code\shuini_calculator\frontend\src\components\hpc-trial\HpcTrialCorrectionTab.vue': (
        "title=\'\u8bf7\u5148\u5728\'\u914d\u6bd4\u8ba1\u7b97 \u2192 \u9ad8\u6027\u80fd\u6df7\u51dd\u571f\"\u4e2d\u5b8c\u6210\u914d\u6bd4\u8ba1\u7b97\uff0c\u4e4b\u540e\u518d\u56de\u5230\u672c\u9875\u8fdb\u884c\u8bd5\u914d\u8c03\u6574\u3002\"",
        "title=\"\u8bf7\u5148\u5728\u300c\u914d\u6bd4\u8ba1\u7b97 \u2192 \u9ad8\u6027\u80fd\u6df7\u51dd\u571f\u300d\u4e2d\u5b8c\u6210\u914d\u6bd4\u8ba1\u7b97\uff0c\u4e4b\u540e\u518d\u56de\u5230\u672c\u9875\u8fdb\u884c\u8bd5\u914d\u8c03\u6574\u3002\""
    ),
    r'd:\Code\shuini_calculator\frontend\src\components\hpc-trial\HpcTrialWorkabilityTab.vue': (
        "title=\'\u8bf7\u5148\u5728\'\u914d\u6bd4\u8ba1\u7b97 \u2192 \u9ad8\u6027\u80fd\u6df7\u51dd\u571f\"\u4e2d\u5b8c\u6210\u914d\u6bd4\u8ba1\u7b97\uff0c\u4e4b\u540e\u518d\u56de\u5230\u672c\u9875\u8fdb\u884c\u5de5\u4f5c\u6027\u5b9e\u9a8c\u3002\"",
        "title=\"\u8bf7\u5148\u5728\u300c\u914d\u6bd4\u8ba1\u7b97 \u2192 \u9ad8\u6027\u80fd\u6df7\u51dd\u571f\u300d\u4e2d\u5b8c\u6210\u914d\u6bd4\u8ba1\u7b97\uff0c\u4e4b\u540e\u518d\u56de\u5230\u672c\u9875\u8fdb\u884c\u5de5\u4f5c\u6027\u5b9e\u9a8c\u3002\""
    ),
}

for path, (old_frag, new_frag) in fixes.items():
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    if old_frag in c:
        c2 = c.replace(old_frag, new_frag, 1)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c2)
        print(f'Fixed: {path.split(chr(92))[-1]}')
    else:
        # Try to find and fix any remaining broken title patterns
        lines = c.split('\n')
        changed = False
        for i, line in enumerate(lines):
            if 'title=' in line and '\u914d\u6bd4\u8ba1\u7b97' in line:
                # Build a clean version
                # Remove all quote chars around the title value
                clean = re.sub(r"title=['\"]?(.*?)['\"]?\s*$", '', line).rstrip()
                # Extract the text content - find what's between title= and line end
                m = re.search(r"title=['\"]?(.+)", line)
                if m:
                    content = m.group(1).rstrip("'\"").strip()
                    # Clean the content: remove inner quotes
                    content = content.replace(chr(0x22), '').replace(chr(0x27), '')
                    # Add corner brackets around 配比计算 → 高性能混凝土
                    content = re.sub(r'(\u914d\u6bd4\u8ba1\u7b97[^\u3001\uff0c\u3002]*)', r'\u300c\1\u300d', content)
                    new_line = '      title="' + content + '"'
                    lines[i] = new_line
                    print(f'Fixed L{i+1}: {new_line.strip()[:80]}')
                    changed = True
        if changed:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
        else:
            print(f'No match for: {path.split(chr(92))[-1]}')

# Fix StrengthTab separately since it has different text
path = r'd:\Code\shuini_calculator\frontend\src\components\hpc-trial\HpcTrialStrengthTab.vue'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
lines = c.split('\n')
changed = False
for i, line in enumerate(lines):
    if 'title=' in line and '\u914d\u6bd4\u8ba1\u7b97' in line:
        # Extract content stripping all outer/inner quotes
        m = re.search(r'title=.(.+)', line)
        if m:
            raw = m.group(1)
            # Remove trailing quote-like chars
            raw = raw.rstrip('"\'')
            # Remove inner quotes
            raw = re.sub(r'["\'\u201c\u201d]', '', raw)
            new_line = '      title="' + raw + '"'
            lines[i] = new_line
            print(f'Fixed StrengthTab L{i+1}: {new_line.strip()[:80]}')
            changed = True
if changed:
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

print('All done')
