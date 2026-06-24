/**
 * Excel 导入 API 层
 */
import request from '../utils/request'

// ── 类型定义 ──────────────────────────────────────────────────────────────────

export interface ValidationItem {
  param: string
  expected: number | null
  actual: number | null
  diff: number | null
  passed: boolean
  tolerance: number
  tolerance_unit?: string
}

export interface ValidationResult {
  valid: boolean
  items: ValidationItem[]
  warnings: string[]
}

export interface ImportValidateResult {
  category: 'hpc' | 'uhpc'
  data: Record<string, unknown>
  validation: ValidationResult
}

export interface ImportSaveResult {
  saved: boolean
  record_id?: number
  category: string
  data: Record<string, unknown>
  validation: ValidationResult
  message?: string
}

export interface ImportProjectRecordDetail {
  name: string
  record_id: number | null
  category: string
  validation: ValidationResult
  saved: boolean
  error?: string
}

export interface ImportProjectResult {
  saved: boolean
  project_id?: number
  project_code?: string
  project_name?: string
  records_created?: number
  records_total?: number
  all_valid: boolean
  project?: Record<string, unknown>
  records?: ImportProjectRecordDetail[]
  record_details?: ImportProjectRecordDetail[]
  message?: string
}

// ── API ───────────────────────────────────────────────────────────────────────

/** 导入 Excel 并校验 */
export const importValidate = (file: File): Promise<ImportValidateResult> => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/exchange/import/validate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 导入并保存单条记录 */
export const importRecord = (
  file: File,
  projectId?: number | null,
  dryRun = false,
): Promise<ImportSaveResult> => {
  const formData = new FormData()
  formData.append('file', file)
  const params: Record<string, unknown> = { dry_run: dryRun }
  if (projectId != null) {
    params.project_id = projectId
  }
  return request.post('/exchange/import/record', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params,
  })
}

/** 导入项目 Excel（含项目信息与所有记录） */
export const importProject = (
  file: File,
  dryRun = false,
): Promise<ImportProjectResult> => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/exchange/import/project', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params: { dry_run: dryRun },
  })
}

