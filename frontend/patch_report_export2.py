import sys
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/views/ReportView.vue'
text = Path(path).read_text(encoding='utf-8')

marker = """  <div class="report-header">
    <div class="report-title">混凝土配合比配合比记录</div>
    <div class="report-meta">
      <span><b>项目：</b>${project?.project_name ?? '—'}</span>
      <span><b>项目编号：</b>${project?.project_code ?? '—'}</span>
      <span><b>记录名称：</b>${record.name}</span>
      <span><b>类别：</b>${categoryLabel(record.category)}</span>
      <span><b>创建时间：</b>${fmtDate(record.created_at)}</span>
      <span><b>创建人：</b>${record.created_by}</span>
    </div>
  </div>

  <div class="section-title">计算参数与结果</div>
  <table>
    <thead><tr><th>参数名称</th><th>数值</th></tr></thead>
    <tbody>${rows.join('\\n')}</tbody>
  </table>

  <div class="footer">本配合比记录由水泥配合比计算系统自动生成 · ${new Date().toLocaleString('zh-CN')}</div>"""

insert = """  <div class="report-header">
    <div class="report-title">混凝土配合比记录</div>
  </div>

  <div class="section-title">第一部分：项目情况信息</div>
  <table>
    <tbody>
      <tr><td class="kv-key">项目名称</td><td class="kv-val">${project?.project_name ?? '—'}</td></tr>
      <tr><td class="kv-key">项目编号</td><td class="kv-val">${project?.project_code ?? '—'}</td></tr>
      <tr><td class="kv-key">记录名称</td><td class="kv-val">${record.name}</td></tr>
      <tr><td class="kv-key">配合比类别</td><td class="kv-val">${categoryLabel(record.category)}</td></tr>
      <tr><td class="kv-key">创建时间</td><td class="kv-val">${fmtDate(record.created_at)}</td></tr>
      <tr><td class="kv-key">创建人</td><td class="kv-val">${record.created_by}</td></tr>
    </tbody>
  </table>

  <div class="section-title">第二部分：配合比及关键参数</div>
  <table>
    <thead><tr><th>参数名称</th><th>数值</th></tr></thead>
    <tbody>${rows.join('\\n')}</tbody>
  </table>

  <div class="section-title">第三部分：混凝土的强度和工作性能（实验室配合比基准）</div>
  <table>
    <tbody>
      <tr><td class="kv-key">28d抗压强度 (MPa)</td><td class="kv-val">${evalStrength || '—'}</td></tr>
      <tr><td class="kv-key">实测坍落度 (mm)</td><td class="kv-val">${evalSlump || '—'}</td></tr>
      <tr><td class="kv-key">实测扩展度 (mm)</td><td class="kv-val">${evalSpread || '—'}</td></tr>
      <tr><td class="kv-key">工作性综合描述</td><td class="kv-val">${workDesc || '—'}</td></tr>
    </tbody>
  </table>

  <div class="footer">本配合比记录由水泥配合比计算系统自动生成 · ${new Date().toLocaleString('zh-CN')}</div>"""

text = text.replace(marker, insert)
Path(path).write_text(text, encoding='utf-8')
print("exportReport modified part 2")