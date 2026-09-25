# Avaliação da busca — 25/09/2026

Gerado por `eval_retrieval.py`. TOP_K avaliado: 12. Posição = onde a página esperada aparece entre os 30 trechos mais similares.

| Pergunta | Tipo | Posição da página esperada | Recuperação no TOP_K | Similaridade dos trechos enviados |
|---|---|---|---|---|
| Q01 | single_doc | 9 | sim | D6:4 0.69, D1:2 0.63, D6:4 0.61, D6:2 0.61, D2:1 0.60, D3:3 0.59, D2:4 0.58, D1:1 0.58, D2:3 0.58, D2:1 0.57, D1:5 0.57, D1:4 0.57 |
| Q02 | cross_lingual | 1 | sim | D1:1 0.74, D1:5 0.72, D1:2 0.70, D1:6 0.69, D1:5 0.68, D1:6 0.68, D1:2 0.68, D1:1 0.67, D1:5 0.67, D1:1 0.67, D1:1 0.66, D1:3 0.66 |
| Q03 | cross_lingual | 12 | sim | D6:4 0.63, outro:4 0.62, D6:2 0.61, outro:5 0.61, D2:4 0.60, outro:8 0.59, outro:4 0.59, D1:2 0.58, outro:2 0.58, outro:2 0.58, D2:1 0.58, D1:3 0.57 |
| Q04 | cross_lingual | 1 | sim | D1:6 0.59, D1:2 0.54, D4:7 0.54, D1:2 0.54, D4:6 0.54, D4:8 0.54, D4:1 0.53, D4:1 0.53, D3:6 0.53, D1:2 0.52, D4:2 0.52, D4:2 0.52 |
| Q05 | cross_lingual | 1 | sim | D3:2 0.61, D3:3 0.60, D3:3 0.58, D6:4 0.57, D3:2 0.57, D3:7 0.57, D3:8 0.56, D3:2 0.56, D3:3 0.56, D1:2 0.55, D3:5 0.55, D3:8 0.55 |
| Q06 | cross_lingual | 1 | sim | D3:2 0.58, D3:2 0.58, D3:7 0.53, D3:2 0.53, D3:7 0.52, D3:8 0.51, D3:3 0.51, D3:4 0.50, D3:5 0.50, D1:4 0.49, D3:7 0.49, D3:6 0.48 |
| Q07 | cross_lingual | 1 | sim | D3:7 0.63, D2:3 0.60, D3:3 0.59, D2:3 0.59, D6:4 0.58, D2:1 0.58, D6:4 0.58, D3:3 0.57, D4:2 0.57, D2:4 0.57, outro:4 0.57, D1:5 0.57 |
| Q08 | single_doc | 1 | sim | D2:5 0.64, D6:4 0.64, D6:2 0.62, D2:5 0.61, D2:3 0.61, D3:7 0.61, D4:2 0.60, outro:7 0.60, D3:3 0.60, D1:2 0.60, D4:1 0.60, D1:2 0.59 |
| Q09 | multi_doc | 10 | sim | outro:4 0.60, D6:4 0.59, D6:2 0.58, D1:2 0.56, outro:2 0.56, D3:3 0.55, outro:1 0.55, outro:4 0.55, outro:8 0.55, D1:3 0.54, outro:5 0.54, D1:3 0.54 |
| Q10 | trap_species | 2 | sim | D4:2 0.73, D4:1 0.71, D4:9 0.69, D4:1 0.69, D4:1 0.68, D6:4 0.68, D6:4 0.67, D4:2 0.65, D4:2 0.64, D6:2 0.64, D4:7 0.64, D6:1 0.64 |
| Q11 | cross_lingual | 1 | sim | D4:8 0.59, D4:5 0.58, D4:5 0.58, D4:8 0.57, D4:5 0.54, D4:6 0.54, D4:2 0.53, D4:6 0.53, D4:5 0.53, D4:2 0.53, D4:9 0.53, D4:7 0.52 |
| Q12 | no_answer | sem resposta esperada | - | D6:4 0.57, D3:5 0.56, D3:3 0.55, D3:3 0.54, D3:3 0.54, D4:4 0.53, D3:8 0.53, D3:2 0.53, D1:2 0.52, D3:2 0.52, outro:7 0.51, outro:7 0.51 |
| Q13 | no_answer | sem resposta esperada | - | D6:3 0.65, D3:3 0.64, D1:2 0.62, D6:2 0.62, D6:4 0.62, D6:1 0.61, D6:2 0.61, D6:1 0.60, D6:2 0.59, D3:3 0.59, D2:7 0.59, D6:1 0.58 |
| Q14 | single_doc | 1 | sim | D2:7 0.60, D3:7 0.59, D3:8 0.58, D3:3 0.58, D3:3 0.57, D1:2 0.57, D3:2 0.57, D6:4 0.55, D3:3 0.55, D1:5 0.54, D3:5 0.54, D2:6 0.54 |
| Q15 | single_doc | 1 | sim | D6:4 0.68, D6:4 0.59, D6:2 0.57, D4:7 0.56, D6:4 0.56, D6:1 0.55, D1:2 0.54, D6:2 0.54, D1:2 0.53, D4:2 0.53, D4:2 0.53, outro:2 0.52 |
| Q16 | multi_doc | 5 | sim | D6:4 0.73, D6:2 0.68, D6:4 0.66, D6:1 0.65, D4:2 0.64, D4:7 0.64, D6:2 0.64, D6:5 0.61, D6:4 0.61, D6:2 0.60, D4:2 0.59, D4:2 0.58 |

## Resumo

| TOP_K | Recuperação |
|---|---|
| 4 | 10/14 |
| 6 | 11/14 |
| 8 | 11/14 |
| 10 | 13/14 |
| 12 | 14/14 |

Falhas com o TOP_K avaliado: nenhuma
Maior similaridade nas perguntas sem resposta: Q12=0.575, Q13=0.654
