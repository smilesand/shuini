import sys
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/views/ReportView.vue'
text = Path(path).read_text(encoding='utf-8')

marker = """              <el-table-column label="创建时间" width="140" align="center">
                <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
              </el-table-column>"""

insert = """              <el-table-column label="强度(28d)" width="90" align="center">
                <template #default="{ row }">
                  {{ extractEval(row, 'evalStrength28d') }}
                </template>
              </el-table-column>
              <el-table-column label="实测坍落度" width="100" align="center">
                <template #default="{ row }">
                  {{ extractEval(row, 'evalSlump') || extractEval(row, 'slumpMeasured') }}
                </template>
              </el-table-column>
              <el-table-column label="实测扩展度" width="100" align="center">
                <template #default="{ row }">
                  {{ extractEval(row, 'evalSpread') || extractEval(row, 'spreadMeasured') }}
                </template>
              </el-table-column>
              <el-table-column label="工作性描述" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">
                  {{ extractEval(row, 'evalWorkabilityDesc') || extractEval(row, 'workabilityNote') }}
                </template>
              </el-table-column>
              <el-table-column label="创建时间" width="140" align="center">
                <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
              </el-table-column>"""

text = text.replace(marker, insert)
Path(path).write_text(text, encoding='utf-8')
print("ReportView table patched")
