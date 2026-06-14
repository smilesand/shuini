import sys
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/views/ReportView.vue'
text = Path(path).read_text(encoding='utf-8')

text = text.replace('配合比配合比记录', '配合比记录')
Path(path).write_text(text, encoding='utf-8')
print("Fixed typo.")