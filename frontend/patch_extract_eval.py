import sys
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/views/ReportView.vue'
text = Path(path).read_text(encoding='utf-8')

marker = """function extractEval(record: RecordItem, key: string) {
  const trialData = record.record_data?.trial_data;
  if (!trialData || !trialData.inputs) return '';
  const val = (trialData.inputs as any)[key];
  if (val === null || val === undefined) return '';
  return val;
}"""

insert = """function extractEval(record: RecordItem, key: string) {
  const trialData = record.record_data?.trial_data as any;
  if (!trialData) return '';
  const val = trialData.inputs ? trialData.inputs[key] : trialData[key];
  if (val === null || val === undefined) return '';
  return val;
}"""

text = text.replace(marker, insert)
Path(path).write_text(text, encoding='utf-8')
print("extractEval patched")