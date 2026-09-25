# Spec 001 — MVP: Assistente de pesquisa para TCC (RAG)

## User story

**Como** estudante de Medicina Veterinária escrevendo meu TCC,
**quero** reunir num só lugar os artigos e documentos da minha pesquisa e fazer perguntas sobre eles em português,
**para** encontrar rapidamente o que a literatura diz sobre meu tema, com a indicação exata de onde cada informação saiu, sem precisar reler dezenas de PDFs.

## Contexto

A estudante acumula artigos científicos (muitos em inglês), capítulos de livros, diretrizes e anotações em PDF. Hoje, para responder uma dúvida do tipo "quais estudos avaliaram o protocolo X em felinos?", ela precisa abrir e procurar arquivo por arquivo. O sistema deve funcionar como um assistente de pesquisa que responde **somente com base nos documentos dela** e sempre aponta a fonte, porque num TCC toda afirmação precisa ser referenciada e verificável.

## Escopo do MVP

**Gerenciar documentos:** ela envia um ou mais PDFs, o sistema processa e mostra quais estão disponíveis para consulta. Ela pode remover um documento (soft delete): ele deixa de ser usado nas respostas, mas as referências a ele em conversas salvas são preservadas com aviso de remoção. Se reenviar um documento removido, ele é reativado.

**Perguntar aos documentos:** ela faz uma pergunta em linguagem natural, em português, e recebe uma resposta em português baseada nos trechos relevantes, mesmo que os documentos estejam em inglês. Cada resposta lista as fontes usadas (nome do arquivo e página) e mostra os trechos originais para conferência. Dentro de uma sessão, a conversa tem contexto (perguntas de acompanhamento).

**Conversas salvas:** toda conversa é salva automaticamente, mensagem a mensagem, com cópia dos trechos citados. Ao iniciar uma nova conversa ou fechar o sistema, a conversa anterior vira um arquivo somente leitura, que ela pode consultar por uma lista (data e título) ou apagar.

## Critérios de aceite

- **CA01 Upload:** dado um PDF com texto selecionável, quando o processamento termina, então o documento aparece como "disponível" e passa a ser considerado nas respostas.
- **CA02 Upload múltiplo:** é possível enviar vários PDFs de uma vez, e o sistema informa o progresso/status de cada um.
- **CA03 PDF sem texto:** dado um PDF escaneado (sem texto extraível), o sistema não trava e avisa claramente que o arquivo não pôde ser lido.
- **CA04 Duplicado:** se um arquivo idêntico a um já existente for enviado, o sistema avisa e não o indexa de novo.
- **CA05 Remoção:** quando um documento é removido, nenhuma resposta posterior o cita.
- **CA06 Resposta fundamentada:** toda resposta é baseada apenas nos documentos enviados; o sistema não completa com conhecimento externo.
- **CA07 Citação:** toda afirmação relevante indica arquivo e página de origem, e é possível ver o trecho original correspondente.
- **CA08 Sem resposta:** se os documentos não contêm informação suficiente, o sistema diz isso explicitamente em vez de inventar.
- **CA09 Idioma:** perguntas em português recuperam trechos relevantes de documentos em inglês, e a resposta vem em português.
- **CA10 Persistência:** ao fechar e reabrir o sistema, os documentos continuam disponíveis sem reprocessar.
- **CA11 Conversa:** dentro de uma sessão, perguntas de acompanhamento ("e em cães?") são entendidas no contexto da pergunta anterior. O contexto vale só para a sessão atual.
- **CA12 Salvamento automático:** cada mensagem da conversa (pergunta, resposta e trechos citados com arquivo e página) é salva assim que gerada.
- **CA13 Encerramento:** ao iniciar uma nova conversa ou fechar o sistema, a conversa anterior fica disponível somente para leitura.
- **CA14 Consulta:** ela vê a lista de conversas anteriores, com data e título, e abre qualquer uma para ler inteira.
- **CA15 Exclusão:** ela pode apagar uma conversa salva.
- **CA16 Documento removido:** numa conversa salva, citações de documentos removidos continuam exibindo o trecho, com aviso de remoção.
- **CA17 Reenvio:** se ela reenviar um documento removido, ele é reativado sem reprocessamento.

## Requisitos não funcionais

- O back-end é implementado em Python; uso por uma única pessoa.
- Suportar ao menos 100 documentos de até 50 páginas cada.
- Uma resposta deve chegar em até ~15 segundos.
- Os documentos e conversas não devem ser expostos publicamente.

## Fora do escopo (versões futuras)

Retomar conversas antigas, busca por texto nas conversas salvas, OCR de PDFs escaneados, fichamento automático, geração de referências em ABNT, comparação estruturada entre estudos, identificação de lacunas na literatura, múltiplos usuários e login, formatos além de PDF (DOCX, imagens).

## Decisões registradas

- Provedor de LLM: Groq (plano gratuito para começar), atrás de interface configurável.
- Histórico: conversas salvas automaticamente como arquivo somente leitura; sem retomada no MVP.
- Remoção de documentos: soft delete, com reativação no reenvio.
