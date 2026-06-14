import sys
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/views/ReportView.vue'
text = Path(path).read_text(encoding='utf-8')

marker = """  function exportReport(record: RecordItem) {
    const project = selectedProject.value
    const data = record.record_data ?? {}
    const rows: string[] = []

    function renderKV(obj: Record<string, unknown>, indent = 0): void {
      for (const [key, val] of Object.entries(obj)) {
        const pad = '&nbsp;'.repeat(indent * 4)
        if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
          rows.push(`<tr><td class="kv-key" style="padding-left:${indent * 12 + 12}px">${pad}<b>${key}</b></td><td></td></tr>`)
          renderKV(val as Record<string, unknown>, indent + 1)
        } else if (Array.isArray(val)) {
          rows.push(`<tr><td class="kv-key" style="padding-left:${indent * 12 + 12}px">${pad}<b>${key}</b></td><td class="kv-val">${val.join(', ')}</td></tr>`)
        } else {
          rows.push(`<tr><td class="kv-key" style="padding-left:${indent * 12 + 12}px">${pad}${key}</td><td class="kv-val">${val ?? '—'}</td></tr>`)
        }
      }
    }

    renderKV(data as Record<string, unknown>)"""

insert = """  function exportReport(record: RecordItem) {
    const project = selectedProject.value
    const data = record.record_data ?? {}
    const trialData = data.trial_data as any
    const inputs = trialData?.inputs || {}

    const evalStrength = extractEval(record, 'evalStrength28d')
    const evalSlump = extractEval(record, 'evalSlump') || extractEval(record, 'slumpMeasured')
    const evalSpread = extractEval(record, 'evalSpread') || extractEval(record, 'spreadMeasured')
    const workDesc = extractEval(record, 'evalWorkabilityDesc') || extractEval(record, 'workabilityNote')

    const rows: string[] = []

    function renderKV(obj: Record<string, unknown>, indent = 0, isRoot = true): void {
      for (const [key, val] of Object.entries(obj)) {
        // Skip trial_data inputs inside the KV, we will print what we need manually or just print other data
        if (isRoot && key === 'trial_data') {
          rows.push(`<tr><td class="kv-key" style="padding-left:${indent * 12 + 12}px"><b>配合比试验参数</b></td><td></td></tr>`)
          renderKV(val as Record<string, unknown>, indent + 1, false)
          continue
        }
        if (key === 'inputs' && typeof val === 'object') {
            continue // skip inputs since we pull out strength explicitly later, or let it render? We will let it render but hide the eval fields.
        }
        // skip the eval fields if they appear in any dict
        if (['evalStrength28d', 'evalSlump', 'evalSpread', 'evalWorkabilityDesc', 'slumpMeasured', 'spreadMeasured', 'workabilityNote'].includes(key)) {
            continue
        }

        const pad = '&nbsp;'.repeat(indent * 4)
        if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
          rows.push(`<tr><td class="kv-key" style="padding-left:${indent * 12 + 12}px">${pad}<b>${key}</b></td><td></td></tr>`)
          renderKV(val as Record<string, unknown>, indent + 1, false)
        } else if (Array.isArray(val)) {
          rows.push(`<tr><td class="kv-key" style="padding-left:${indent * 12 + 12}px">${pad}<b>${key}</b></td><td class="kv-val">${val.join(', ')}</td></tr>`)
        } else {
          rows.push(`<tr><td class="kv-key" style="padding-left:${indent * 12 + 12}px">${pad}${key}</td><td class="kv-val">${val ?? '—'}</td></tr>`)
        }
      }
    }

    renderKV(data as Record<string, unknown>)"""

text = text.replace(marker, insert)
Path(path).write_text(text, encoding='utf-8')
print("exportReport modified part 1")