import request from '../utils/request'

export type RecycleBinFilterType = 'all' | 'project' | 'record'
export type RecycleBinItemType = 'project' | 'record'

export interface RecycleBinItem {
  item_type: RecycleBinItemType
  id: number
  name: string
  category?: string | null
  project_code: string
  project_name: string
  project_id?: number | null
  created_by: string
  created_at: string
  deleted_at?: string | null
  deleted_by: string
  deleted_with_project: boolean
}

export interface RecycleBinListRes {
  items: RecycleBinItem[]
  total: number
  page: number
  page_size: number
}

export const listRecycleBin = (params?: {
  item_type?: RecycleBinFilterType
  search?: string
  page?: number
  page_size?: number
}): Promise<RecycleBinListRes> =>
  request.get('/recycle-bin', { params }) as Promise<RecycleBinListRes>

export const restoreProjectFromRecycleBin = (id: number): Promise<{ restored: number; item_type: 'project' }> =>
  request.post(`/recycle-bin/projects/${id}/restore`)

export const restoreRecordFromRecycleBin = (id: number): Promise<{ restored: number; item_type: 'record' }> =>
  request.post(`/recycle-bin/records/${id}/restore`)

export const purgeProjectFromRecycleBin = (id: number): Promise<{ deleted: number; item_type: 'project' }> =>
  request.delete(`/recycle-bin/projects/${id}`)

export const purgeRecordFromRecycleBin = (id: number): Promise<{ deleted: number; item_type: 'record' }> =>
  request.delete(`/recycle-bin/records/${id}`)