import request from '../utils/request'

export interface LicenseStatus {
  edition: string
  fingerprint: string
  activated: boolean
  can_use: boolean
  expiry: string | null
  trial: boolean
  trial_days_left: number | null
  message: string
}

export interface ActivateResult {
  activated: boolean
  can_use: boolean
  fingerprint: string
  expiry: string | null
  message: string
}

export const getLicenseStatus = (): Promise<LicenseStatus> =>
  request.get('/license/status') as Promise<LicenseStatus>

export const activateLicense = (licenseCode: string): Promise<ActivateResult> =>
  request.post('/license/activate', { license_code: licenseCode }) as Promise<ActivateResult>
