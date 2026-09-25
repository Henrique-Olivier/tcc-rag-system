// Verificação rápida do linkMarkers: node scripts/check-citations.ts
import assert from 'node:assert/strict'
import { linkMarkers } from '../src/lib/citations.ts'

const valid = new Set([1, 2, 3])
assert.equal(linkMarkers('Dose segura [1].', valid), 'Dose segura [1](#cite-1).')
assert.equal(linkMarkers('Estudos [1, 3] e [2–3].', valid), 'Estudos [1](#cite-1)[3](#cite-3) e [2](#cite-2)[3](#cite-3).')
assert.equal(linkMarkers('Fora [9] fica texto.', valid), 'Fora [9] fica texto.')
assert.equal(linkMarkers('Link [1](https://x.org) intacto.', valid), 'Link [1](https://x.org) intacto.')
assert.equal(linkMarkers('Enorme [1-999999999].', valid), 'Enorme [1](#cite-1)[2](#cite-2)[3](#cite-3).')
console.log('citations ok')
