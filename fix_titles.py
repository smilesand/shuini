import re
files = [
  r'frontend/src/components/hpc-trial/HpcTrialCorrectionTab.vue',
  r'frontend/src/components/hpc-trial/HpcTrialStrengthTab.vue',
  r'frontend/src/components/hpc-trial/HpcTrialWorkabilityTab.vue',
]
for path in files:
  with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
  lines = c.split('\n')
  changed = False
  for i, line in enumerate(lines):
    if 'title=' in line and '\u914d\u6bd4\u8ba1\u7b97' in line:
      new_line = re.sub(r'title="(.*?)"', lambda m: "title='" + m.group(1) + "'", line)
      lines[i] = new_line
      print(f'Fixed L{i+1} in {path.split("/")[-1]}: {new_line.strip()[:80]}')
      changed = True
  if changed:
    with open(path, 'w', encoding='utf-8') as f:
      f.write('\n'.join(lines))
print('Done')
