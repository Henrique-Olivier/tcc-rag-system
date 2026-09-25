  # Conjunto de avaliação simulado — Spec 001

Insumo provisório para as tarefas **T11** (dimensionamento), **T26** (avaliação e calibração) e **T27** (latência), enquanto os artigos e perguntas reais da usuária não chegam. Quando chegarem, este conjunto continua útil como teste de regressão.

Tema escolhido: **doença renal crônica (DRC) em gatos**, por ter bastante literatura de acesso aberto em português e inglês e permitir perguntas que atravessam vários artigos.

## Documentos

Baixe os PDFs pelos links abaixo e salve com o nome indicado em `specs/001-mvp-rag/eval/docs/` (adicione essa pasta ao `.gitignore` se não quiser versionar os PDFs; os quatro primeiros são de acesso aberto).

| Id | Arquivo | Idioma | Tipo | Páginas | Link |
|---|---|---|---|---|---|
| D1 | `freitas2025_vetworld_pressao_proteinuria.pdf` | EN | Estudo observacional (autores brasileiros) | 7 | https://veterinaryworld.org/Vol.18/February-2025/28.pdf |
| D2 | `miranda2024_fag_estadiamento_drc.pdf` | PT | Revisão de literatura | 9 | https://themaetscientia.fag.edu.br/index.php/ABMVFAG/article/download/2032/1748/5665 |
| D3 | `vergnano2016_actascivet_suplemento.pdf` | EN | Ensaio clínico sem grupo controle | 9 | https://www.redalyc.org/pdf/2890/289043697022.pdf |
| D4 | `morita2025_frontiers_anlodipina_caes.pdf` | EN | Estudo retrospectivo **em cães** | 10 | https://www.frontiersin.org/journals/veterinary-science/articles/10.3389/fvets.2025.1570349/pdf |
| D5 | `anotacoes_aula_escaneado.pdf` | PT | Anotação escaneada (só imagem) | 2 | Gerado para o teste, está nesta pasta |
| D6 | `oliveira2020_mvez_sdma.pdf` | PT | Revisão de literatura (SDMA) | 6 | https://www.revistamvez-crmvsp.com.br/index.php/recmvz/article/download/38106/42706/ |

Por que esse conjunto:

- **Mistura de idiomas:** três artigos em inglês e dois em português, com todas as perguntas em português (CA09).
- **D4 é sobre cães.** Ele funciona como armadilha: perguntas sobre gatos não devem ser respondidas com dados dele, e perguntas sobre anlodipina em gatos precisam deixar claro que o estudo é canino (CA06).
- **D5 não tem texto extraível** e deve terminar como `failed` com a mensagem de PDF escaneado (CA03). Ele também serve para testar o reprocessamento de `failed` no reenvio.
- **Cinco documentos típicos para a T11:** D1, D2, D3, D4 e D6, somando 41 páginas com texto. O D5 fica de fora da medição de tempo, porque falha antes de gerar embeddings.
- **Tamanho:** 43 páginas no total (41 com texto). Para a T11, a extrapolação para 100 documentos de 50 páginas deve ser feita **por página**, não por documento, porque estes artigos são mais curtos que o cenário da spec.

## Atenção: página do PDF × página impressa

As páginas esperadas em `questions.yaml` são as **páginas do arquivo PDF, começando em 1**, que é o que o sistema grava em `page_number`. Em três dos quatro artigos isso **não bate** com o número impresso na página:

| Id | Página do PDF | Página impressa |
|---|---|---|
| D1 | 1 a 7 | 527 a 533 (PDF + 526) |
| D2 | 1 a 9 | 73 a 81 (PDF + 72) |
| D3 | 1 a 9 | A página 1 é uma **capa do Redalyc**; a página impressa 1 é a página 2 do PDF (impressa = PDF − 1) |
| D4 | 1 a 10 | Iguais |
| D6 | 1 a 6 | Iguais |

Isso não quebra o CA07 (a citação leva ao ponto certo do arquivo), mas vale registrar como observação para a spec: numa referência ABNT, ela vai precisar da página **impressa**, e o sistema mostra a do PDF. É um candidato natural para a Spec de referências ABNT.

## Como usar

**T11:** indexar D1, D2, D3, D4 e D6, medir o tempo total e o tempo por página, extrapolar para 5.000 páginas. Indexar D5 e confirmar o `failed`.

**T26:** para cada pergunta, rodar a busca e verificar se algum dos trechos recuperados está no documento e na página esperados (acerto no top-K). Perguntas do tipo `no_answer` devem resultar em "não encontrei" ou numa resposta que diga explicitamente que os documentos não cobrem o tema. Calibrar `MIN_SIMILARITY` começando baixo e subindo enquanto nenhuma pergunta com resposta for barrada.

**T27:** usar as perguntas Q01 a Q05 como carga do teste de latência, com e sem o worker indexando.

## Limitações deste conjunto simulado

As perguntas foram escritas a partir da leitura dos artigos, não por quem está fazendo o TCC. Perguntas reais tendem a ser mais vagas, usar termos diferentes dos artigos e misturar assuntos, então o desempenho medido aqui provavelmente é **otimista**. Substitua ou complemente com as perguntas dela assim que possível.
