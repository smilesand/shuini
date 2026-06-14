import request from '../utils/request'

export interface LoginRes {
  access_token: string
  token_type: string
  username: string
  is_admin: boolean
  must_reset: boolean
}

export const login = (username: string, password: string): Promise<LoginRes> =>
  request.post('/auth/login', { username, password }) as Promise<LoginRes>

export const logout = (): Promise<{ ok: boolean }> =>
  request.post('/auth/logout') as Promise<{ ok: boolean }>

export const resetPassword = (newPassword: string): Promise<{ ok: boolean }> =>
  request.post('/auth/reset-password', { new_password: newPassword }) as Promise<{ ok: boolean }>

export interface CreateUserReq {
  username: string
  email?: string
  phone?: string
  is_admin?: boolean
}

export const createUser = (data: CreateUserReq): Promise<Record<string, unknown>> =>
  request.post('/auth/users', data)

export interface UserInfo {
  id: number
  username: string
  email: string
  phone: string
  is_admin: number | boolean
  must_reset: number | boolean
  created_at: string
}

export const listUsers = (): Promise<UserInfo[]> =>
  request.get('/auth/users') as Promise<UserInfo[]>

export const deleteUser = (username: string): Promise<{ ok: boolean }> =>
  request.delete(`/auth/users/${encodeURIComponent(username)}`) as Promise<{ ok: boolean }>

export const adminResetPassword = (username: string, newPassword: string): Promise<{ ok: boolean }> =>
  request.post(`/auth/users/${encodeURIComponent(username)}/reset-password`, {
    new_password: newPassword,
  }) as Promise<{ ok: boolean }>

export interface ProfileInfo {
  username: string
  email: string
  phone: string
  is_admin: boolean
  must_reset: boolean
  created_at: string
}

export const getProfile = (): Promise<ProfileInfo> =>
  request.get('/auth/profile') as Promise<ProfileInfo>

export const updateProfile = (data: { email?: string; phone?: string }): Promise<ProfileInfo> =>
  request.put('/auth/profile', data) as Promise<ProfileInfo>

export const changePassword = (oldPassword: string, newPassword: string): Promise<{ ok: boolean }> =>
  request.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword }) as Promise<{ ok: boolean }>
