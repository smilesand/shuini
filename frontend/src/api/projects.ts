import request from '../utils/request'
import type { RecordItem } from './records'

export interface Project {
  id: number
  project_code: string
  project_name: string
  requirements: string
  created_by: string
  created_at: string
  updated_at: string
  record_count: number
}

export interface ProjectCreateReq {
  project_code: string
  project_name: string
  requirements?: string
}

export interface ProjectUpdateReq {
  project_code?: string
  project_name?: string
  requirements?: string
}

export const createProject = (data: ProjectCreateReq): Promise<Project> =>
  request.post('/projects', data)

export const listProjects = (search?: string, page?: number, pageSize?: number): Promise<{ items: Project[]; total: number; page: number; page_size: number }> =>
  request.get('/projects', { params: { search, page, page_size: pageSize } })

export const getProject = (id: number): Promise<Project> =>
  request.get(`/projects/${id}`)

export const updateProject = (id: number, data: ProjectUpdateReq): Promise<Project> =>
  request.put(`/projects/${id}`, data)

export const deleteProject = (id: number): Promise<any> =>
  request.delete(`/projects/${id}`)

export const listProjectRecords = (id: number): Promise<RecordItem[]> =>
  request.get(`/projects/${id}/records`)
