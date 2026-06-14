import request from '../utils/request'

export interface RecordData {
  [key: string]: unknown
}

export interface RecordItem {
  id: number
  name: string
  category: string
  created_by: string
  created_at: string
  project_id?: number | null
  record_data: RecordData
  [key: string]: unknown
}

export interface RecordListRes {
  items: RecordItem[]
  total: number
  page: number
  page_size: number
}

export interface SaveRecordPayload {
  id?: number
  name: string
  category: string
  project_id?: number | null
  record_data?: RecordData | null
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

export function getRecordData(record: { record_data?: unknown } | Record<string, unknown>): RecordData {
  return isPlainObject(record.record_data) ? record.record_data : {}
}

export function getRecordNumber(record: { record_data?: unknown } | Record<string, unknown>, key: string): number | null {
  const value = getRecordData(record)[key]
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

export function getRecordObject<T extends Record<string, unknown>>(
  record: { record_data?: unknown } | Record<string, unknown>,
  key: string,
): T | null {
  const value = getRecordData(record)[key]
  return isPlainObject(value) ? value as T : null
}

export function formatRecordNumber(
  record: { record_data?: unknown } | Record<string, unknown>,
  key: string,
  digits = 2,
): string {
  const value = getRecordNumber(record, key)
  return value !== null ? value.toFixed(digits) : '—'
}

export const saveRecord = (data: SaveRecordPayload): Promise<{ ok: boolean; id: number }> =>
  request.post('/records', data)

export const listRecords = (params?: {
  category?: string
  search?: string
  page?: number
  page_size?: number
  project_id?: number
}): Promise<RecordListRes> =>
  request.get('/records', { params }) as Promise<RecordListRes>

export const deleteRecord = (id: number): Promise<{ ok: boolean }> =>
  request.delete(`/records/${id}`)
