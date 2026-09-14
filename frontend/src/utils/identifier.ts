/** Suggest a barcode type for common numeric codes without rejecting custom IDs. */
export function detectIdentifierType(value: string): string | null {
  if (!/^\d+$/.test(value)) return null
  if (value.length === 8) return 'EAN-8'
  if (value.length === 12) return 'UPC-A'
  if (value.length === 13) return 'EAN-13'
  return null
}
