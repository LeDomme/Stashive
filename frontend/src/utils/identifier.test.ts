import { describe, expect, it } from 'vitest'
import { detectIdentifierType } from './identifier'

describe('detectIdentifierType', () => {
  it.each([['12345678', 'EAN-8'], ['123456789012', 'UPC-A'], ['5053083188269', 'EAN-13']])('suggests %s as %s', (value, expected) => {
    expect(detectIdentifierType(value)).toBe(expected)
  })
  it('does not misclassify alphanumeric or non-standard custom IDs', () => {
    expect(detectIdentifierType('ABC-12345')).toBeNull()
    expect(detectIdentifierType('123456789')).toBeNull()
  })
})
