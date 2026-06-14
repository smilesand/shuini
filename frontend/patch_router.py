import sys
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/router/index.ts'
text = Path(path).read_text(encoding='utf-8')
text = text.replace("'计算书'", "'配合比记录'")
Path(path).write_text(text, encoding='utf-8')

path = 'd:/Code/shuini_calculator/frontend/src/views/ReportView.vue'
text = Path(path).read_text(encoding='utf-8')
text = text.replace('导出计算书', '导出配合比记录')
text = text.replace('下载计算书', '下载配合比记录')
text = text.replace('计算书', '配合比记录')
Path(path).write_text(text, encoding='utf-8')

print("Renamed.")