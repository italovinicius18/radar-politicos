// Cores de gráfico validadas pelo verificador do dataviz para a superfície
// escura #11221a (modo "Painel de Brasília"): todos os checks PASS.
export const FONTES: Record<string, { rotulo: string; cor: string }> = {
  camara: { rotulo: 'Câmara', cor: '#199e70' },
  senado: { rotulo: 'Senado', cor: '#3987e5' },
  cldf: { rotulo: 'CLDF', cor: '#c98500' },
}

export function infoFonte(fonte: string): { rotulo: string; cor: string } {
  return FONTES[fonte] ?? { rotulo: fonte, cor: '#8aa694' }
}
