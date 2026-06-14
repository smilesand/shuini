import { inject, type InjectionKey } from 'vue'
import type { HpcTrialState } from './useHpcTrial'

export const hpcTrialKey: InjectionKey<HpcTrialState> = Symbol('hpc-trial')

export function useHpcTrialContext() {
  const context = inject(hpcTrialKey)

  if (!context) {
    throw new Error('HPC trial context is not available.')
  }

  return context
}