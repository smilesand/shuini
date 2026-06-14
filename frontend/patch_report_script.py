import sys
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/views/ReportView.vue'
text = Path(path).read_text(encoding='utf-8')

marker = """function fmtDate(value: string) {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}"""

insert = """function fmtDate(value: string) {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function extractEval(record: RecordItem, key: string) {
  const trialData = record.record_data?.trial_data;
  if (!trialData || !trialData.inputs) return '';
  const val = (trialData.inputs as any)[key];
  if (val === null || val === undefined) return '';
  return val;
}"""

text = text.replace(marker, insert)
Path(path).write_text(text, encoding='utf-8')
print("ReportView script patched")
