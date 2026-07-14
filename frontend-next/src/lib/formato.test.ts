import { describe, expect, it } from 'vitest'
import { formatarBRL, formatarBRLCompacto, formatarData, MESES_ABREV } from './formato'

describe('formatarBRL', () => {
  it('formata em pt-BR', () => {
    expect(formatarBRL(1234.5).replace(/\s/g, ' ')).toBe('R$ 1.234,50')
    expect(formatarBRL(-200).replace(/\s/g, ' ')).toBe('-R$ 200,00')
  })
})

describe('formatarData', () => {
  it('converte ISO para DD/MM/YYYY', () => {
    expect(formatarData('2025-02-07')).toBe('07/02/2025')
    expect(formatarData(null)).toBe('—')
  })
})

describe('formatarBRLCompacto', () => {
  it('abrevia milhões e milhares em pt-BR', () => {
    expect(formatarBRLCompacto(89_200_000)).toBe('R$ 89,2 mi')
    expect(formatarBRLCompacto(151_700)).toBe('R$ 151,7 mil')
    expect(formatarBRLCompacto(2_000_000)).toBe('R$ 2 mi')
  })
  it('mantém valores pequenos e negativos legíveis', () => {
    expect(formatarBRLCompacto(42.5).replace(/\s/g, ' ')).toBe('R$ 42,50')
    expect(formatarBRLCompacto(-1_500_000)).toBe('R$ -1,5 mi')
  })
})

describe('MESES_ABREV', () => {
  it('tem 12 meses pt-BR', () => {
    expect(MESES_ABREV).toHaveLength(12)
    expect(MESES_ABREV[0]).toBe('jan')
    expect(MESES_ABREV[11]).toBe('dez')
  })
})
