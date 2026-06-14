export function formatNullableNumber(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined) {
    return '—'
  }

  return Number(value).toFixed(digits)
}

export function formatKg(value: number | null | undefined, digits = 2) {
  return `${formatNullableNumber(value, digits)} kg`
}