import os
import glob

src_dir = 'd:/Code/shuini_calculator/frontend/src'
for filepath in glob.glob(os.path.join(src_dir, '**', '*.*'), recursive=True):
    if not os.path.isfile(filepath):
        continue
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if '计算书' in content:
            print(f"Found in {filepath}")
    except:
        pass
