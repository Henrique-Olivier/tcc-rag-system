# Avaliação da busca — 25/09/2026

Gerado por `eval_retrieval.py`. TOP_K avaliado: 8. Posição = onde a página esperada aparece entre os 30 trechos mais similares.

| Pergunta | Tipo | Posição da página esperada | Recuperação no TOP_K | Similaridade dos trechos enviados |
|---|---|---|---|---|
| Q01 | single_doc | 17 | NÃO | D6:4 0.63, D1:2 0.63, D3:3 0.60, D6:1 0.58, D6:2 0.58, D2:4 0.58, D2:1 0.58, D3:4 0.57 |
| Q02 | cross_lingual | 1 | sim | D1:5 0.74, D1:1 0.73, D1:1 0.73, D1:1 0.71, D1:5 0.69, D2:3 0.69, D1:2 0.68, D1:6 0.68 |
| Q03 | cross_lingual | 7 | sim | D2:4 0.60, outro:2 0.60, outro:4 0.59, outro:5 0.59, D1:2 0.58, outro:4 0.58, D1:3 0.58, D6:4 0.57 |
| Q04 | cross_lingual | 1 | sim | D1:6 0.59, D1:2 0.52, D1:5 0.52, D4:7 0.52, D4:8 0.52, D4:1 0.51, D1:2 0.51, D4:7 0.51 |
| Q05 | cross_lingual | 1 | sim | D3:2 0.59, D3:3 0.58, D3:3 0.58, D3:8 0.57, D3:3 0.56, D3:7 0.56, D3:5 0.55, D3:2 0.54 |
| Q06 | cross_lingual | 1 | sim | D3:2 0.58, D3:4 0.54, D3:2 0.54, D3:8 0.51, D3:5 0.51, D3:7 0.50, D3:7 0.50, D1:4 0.48 |
| Q07 | cross_lingual | 1 | sim | D3:7 0.62, D2:3 0.60, D2:1 0.58, D2:4 0.58, D2:6 0.58, D3:3 0.57, D4:2 0.57, D3:3 0.57 |
| Q08 | single_doc | 1 | sim | D2:5 0.64, D2:1 0.62, D2:3 0.61, D3:3 0.61, D2:5 0.59, outro:7 0.59, outro:2 0.59, outro:8 0.58 |
| Q09 | multi_doc | 22 | NÃO | outro:4 0.60, outro:2 0.57, D1:3 0.56, D2:6 0.55, outro:1 0.55, D1:3 0.55, D1:3 0.55, D3:3 0.54 |
| Q10 | trap_species | 1 | sim | D4:1 0.72, D4:2 0.71, D4:9 0.71, D4:2 0.71, D4:1 0.69, D6:4 0.68, D6:4 0.67, D6:1 0.67 |
| Q11 | cross_lingual | 1 | sim | D4:8 0.60, D4:7 0.58, D4:5 0.57, D4:5 0.57, D4:9 0.55, D4:6 0.54, D4:9 0.54, D4:8 0.54 |
| Q12 | no_answer | sem resposta esperada | - | D3:5 0.55, D3:3 0.54, D3:8 0.53, D4:4 0.53, D3:3 0.53, D2:1 0.52, D3:2 0.52, outro:7 0.52 |
| Q13 | no_answer | sem resposta esperada | - | D6:2 0.66, D6:1 0.64, D3:3 0.64, D1:2 0.62, D6:3 0.62, D6:4 0.61, D6:1 0.61, D6:2 0.60 |
| Q14 | single_doc | 4 | sim | D3:8 0.58, D3:3 0.58, D3:7 0.58, D2:7 0.57, D3:2 0.57, D6:1 0.56, D6:2 0.56, D3:3 0.55 |
| Q15 | single_doc | 1 | sim | D6:4 0.66, D6:1 0.60, D6:2 0.57, D1:2 0.56, outro:2 0.56, D6:4 0.55, D6:2 0.55, D4:7 0.54 |
| Q16 | multi_doc | 2 | sim | D6:4 0.70, D4:2 0.65, D6:2 0.63, D4:2 0.63, D6:1 0.62, D6:2 0.61, D6:5 0.61, D6:4 0.61 |

## Resumo

| TOP_K | Recuperação |
|---|---|
| 4 | 11/14 |
| 6 | 11/14 |
| 8 | 12/14 |
| 10 | 12/14 |
| 12 | 12/14 |

Falhas com o TOP_K avaliado: Q01 (posição 17), Q09 (posição 22)
Maior similaridade nas perguntas sem resposta: Q12=0.553, Q13=0.660
