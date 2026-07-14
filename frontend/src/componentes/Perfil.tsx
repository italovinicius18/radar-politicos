'use client'
import {
  Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { Resumo } from '@/lib/tipos'
import { formatarBRL, formatarBRLCompacto } from '@/lib/formato'
import { TabelaDespesas } from './TabelaDespesas'

function mediana(valores: number[]): number {
  if (valores.length === 0) return 0
  const ordenados = [...valores].sort((a, b) => a - b)
  const meio = Math.floor(ordenados.length / 2)
  return ordenados.length % 2 ? ordenados[meio] : (ordenados[meio - 1] + ordenados[meio]) / 2
}

// Paleta dark validada (dataviz, superfície #11221a). Cores por RANK da fatia:
// a adjacência circular 1→…→6→1 é fixa; o pior par adjacente (10,3, faixa-piso)
// é coberto pelos vãos de 2px entre fatias + legenda.
const CORES_ROSCA = ['#3987e5', '#199e70', '#c98500', '#008300', '#9085e9', '#e66767']
const MAX_FATIAS = 5 // além disso, agrega em "Outras" (regra: >7 classes nunca)

export function Perfil({ resumo }: { resumo: Resumo }) {
  const { politico } = resumo
  const totaisAnuais = resumo.por_ano.map((a) => a.total)
  const mediaAnual = totaisAnuais.length ? resumo.total / totaisAnuais.length : 0
  const medianaAnual = mediana(totaisAnuais)
  const categoriasComGasto = resumo.por_categoria.filter((c) => c.total > 0)
  const fatias =
    categoriasComGasto.length <= MAX_FATIAS + 1
      ? categoriasComGasto
      : [
          ...categoriasComGasto.slice(0, MAX_FATIAS),
          {
            categoria: 'Outras (agregadas)',
            total: categoriasComGasto.slice(MAX_FATIAS).reduce((s, c) => s + c.total, 0),
          },
        ]

  return (
    <div>
      <div className="cartao resultado">
        {politico.foto_url && <img src={politico.foto_url} alt="" style={{ width: 72, height: 90 }} />}
        <div>
          <h1 style={{ margin: 0 }}>{politico.nome}</h1>
          <div>
            {politico.cargo}
            {politico.partido ? ` · ${politico.partido}` : ''}
            {politico.uf ? ` · ${politico.uf}` : ''}
          </div>
          <div className="total-destaque">{formatarBRL(resumo.total)}</div>
          <small>total no período disponível (estornos já descontados)</small>
          {totaisAnuais.length > 0 && (
            <small>
              média {formatarBRLCompacto(mediaAnual)}/ano · mediana{' '}
              {formatarBRLCompacto(medianaAnual)}/ano · {totaisAnuais.length}{' '}
              {totaisAnuais.length === 1 ? 'ano' : 'anos'} com dados
            </small>
          )}
        </div>
      </div>

      <div className="graficos">
        <div className="cartao">
          <h3>Gasto por ano</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={resumo.por_ano}>
              <XAxis dataKey="ano" />
              <YAxis tickFormatter={(v) => `${Math.round(v / 1000)}k`} width={50} />
              <Tooltip formatter={(v) => formatarBRL(Number(v))} />
              <Bar dataKey="total" fill="#199e70" radius={[4, 4, 0, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="cartao">
          <h3>Por categoria (o porquê)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={fatias}
                dataKey="total"
                nameKey="categoria"
                innerRadius={50}
                outerRadius={90}
                paddingAngle={2}
                stroke="#11221a"
              >
                {fatias.map((c, i) => (
                  <Cell key={c.categoria} fill={CORES_ROSCA[i % CORES_ROSCA.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => formatarBRL(Number(v))} />
              <Legend formatter={(valor) => <span style={{ color: '#d7e4da' }}>{valor}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="cartao">
        <h3>Top fornecedores (para quem foi o dinheiro)</h3>
        <table>
          <thead>
            <tr><th>Fornecedor</th><th>CNPJ/CPF</th><th>Notas</th><th className="valor">Total</th></tr>
          </thead>
          <tbody>
            {resumo.top_fornecedores.map((f) => (
              <tr key={f.fornecedor + f.cnpj}>
                <td>{f.fornecedor}</td>
                <td>{f.cnpj || '—'}</td>
                <td>{f.quantidade}</td>
                <td className="valor">{formatarBRL(f.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <TabelaDespesas
        politicoId={resumo.politico.id}
        anos={resumo.por_ano.map((a) => a.ano)}
        categorias={resumo.por_categoria.map((c) => c.categoria)}
      />
    </div>
  )
}
