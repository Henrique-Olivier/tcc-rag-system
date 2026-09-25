/** Marcadores [n] da resposta, com listas e intervalos (plano, seção 6.4). Não pega links markdown "[1](url)". */
const MARKER = /\[\s*(\d+(?:\s*[-–]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*)\s*\](?!\()/g

export const CITE_PREFIX = '#cite-'

function expand(group: string, upper: number): number[] {
  return group.split(',').flatMap((item) => {
    const [first, last = first] = item.split(/[-–]/).map((n) => Number(n.trim()))
    const numbers: number[] = []
    for (let n = first; n <= Math.min(last, upper); n++) numbers.push(n)
    return numbers
  })
}

/**
 * Troca cada marcador por links markdown "[n](#cite-n)", um por trecho existente, para o renderizador
 * mostrar como botões clicáveis. Números sem trecho correspondente ficam como texto.
 */
export function linkMarkers(text: string, markers: Set<number>): string {
  const upper = Math.max(0, ...markers)
  // Durante o streaming o texto ainda pode trazer [2†L20-L23]; o back-end limpa ao salvar (plano v10).
  return text.replace(/†[^[\]]*(?=\])/g, '').replace(MARKER, (whole, group: string) => {
    const valid = expand(group, upper).filter((n) => markers.has(n))
    return valid.length ? valid.map((n) => `[${n}](${CITE_PREFIX}${n})`).join('') : whole
  })
}
