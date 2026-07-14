// Gera public/og-padrao.png: 1200x630, fundo #0b1712, wordmark "⦿ RADAR POLÍTICOS" em #4ade80.
// Renderiza um SVG (fonte sans bold 72px) via sharp/librsvg — sem depender de navegador.
import { writeFileSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import sharp from 'sharp'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SAIDA = join(__dirname, '..', 'public', 'og-padrao.png')

const LARGURA = 1200
const ALTURA = 630

const svg = `
<svg width="${LARGURA}" height="${ALTURA}" viewBox="0 0 ${LARGURA} ${ALTURA}" xmlns="http://www.w3.org/2000/svg">
  <rect width="${LARGURA}" height="${ALTURA}" fill="#0b1712" />
  <text
    x="50%"
    y="52%"
    dominant-baseline="middle"
    text-anchor="middle"
    font-family="Arial, Helvetica, sans-serif"
    font-weight="bold"
    font-size="72"
    letter-spacing="4"
    fill="#4ade80"
  >⦿ RADAR POLÍTICOS</text>
</svg>
`

await sharp(Buffer.from(svg)).png().toFile(SAIDA)
console.log(`OG gerado em ${SAIDA}`)
