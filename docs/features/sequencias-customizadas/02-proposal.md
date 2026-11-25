# Proposta — Sequências de Acordes Customizadas

> Decisão tomada com base em `research/01-research-findings.md` e em
> `docs/features/sequencias-customizadas/01-research.md`. Esta fase decide a
> abordagem; a implementação fica para a próxima fase.

## Abordagem escolhida

### Algoritmo de matching

Adotar a regra do gerador (`scripts/generate_data_set.py:7-24`), que foi a única,
entre cinco definições testadas, a reproduzir zero falsos positivos e zero falsos
negativos nas seis sequências do CSV real (`research/01-research-findings.md:24-34`).
Definição implementável: uma música `m` é compatível com a sequência ordenada
`s = [c1, ..., cn]` quando, comparando tudo em minúsculas, (1) os tokens de `s`
aparecem como um bloco contíguo em `m.cifra` (`musica.py:16`, preservando ordem e
repetição) e (2) todo acorde de `m.cifra` pertence ao conjunto de acordes de `s`.
A condição (2) é o que impede que um trecho contíguo dentro de uma cifra com
outros acordes gere match, como mostram os exemplos em
`research/01-research-findings.md:34` e os testes em
`research/validate_matching.py:121-136`. `musica.acordes` não é usado:
`musica.py:17` aplica `list(set(...))`, descartando ordem e duplicatas, e a
definição por conjunto gerou de 5.569 a 14.156 falsos positivos
(`docs/features/sequencias-customizadas/01-research.md:22,33`).

A busca continua lendo `data/top/dataset_final.csv` em memória na importação
(`main.py:49-98`). Nenhuma música ou gênero vai para o banco. Para manter o
contrato atual, `GET /similares?sequencia=Bm,G,D,A` é dividido por vírgula e
normalizado; a forma legada sem vírgula (`BmGDA`) continua resolvida pelo campo
`chave_legada` das seis sequências-semente. Sequência desconhecida retorna `[]`,
como em `main.py:194-197`. A paginação e o formato dos objetos de música
permanecem os atuais (`main.py:210-220,226-228`).

### Banco de dados

SQLite embarcado, via módulo `sqlite3` da biblioteca padrão, em
`var/sequences.sqlite3` por padrão (caminho sobrescrevível por
`SEQUENCES_DB_PATH` nos testes). Ele foi escolhido porque já importa no ambiente
avaliado, não adiciona linha em `requirements.txt:4-5`, cabe no container único
de `docs/adr/0001-local-only-docker-deploy.md:9-16` e oferece `UNIQUE`,
ordenação e inspeção simples para um catálogo público que precisa de dedupe.
`dbm`/`shelve` também são stdlib, mas são dicionários opacos, sem restrição de
unicidade declarada, e foram descartados na alternativa abaixo.

Para que o catálogo não seja perdido ao reiniciar o container, `Dockerfile`
passa a declarar `VOLUME /app/var` e o comando documentado de execução passa a
usar um volume nomeado, por exemplo `docker run -p 8080:8080 -v ciframe-sequences:/app/var ciframe`.
`.dockerignore:1-4` ignora `var/` para que um banco de teste local não seja
copiado para a imagem por `COPY . .` (`Dockerfile:8`). O CSV permanece em
`data/top/dataset_final.csv`, carregado em memória como hoje (`main.py:49-98`).

### Esquema de dados (alto nível)

Uma única tabela `sequences`:

- `id INTEGER PRIMARY KEY` — IDs `0..5` preservados para as seis sequências
  originais; novas sequências usam `AUTOINCREMENT`.
- `acordes TEXT NOT NULL` — array JSON com a forma de exibição, por exemplo
  `["Bm","G","D","A"]`.
- `chave_normalizada TEXT NOT NULL UNIQUE` — `bm;g;d;a`, usada para dedupe e
  como chave de matching.
- `chave_legada TEXT` — `BmGDA` etc., somente nas seis originais.
- `criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`.

Seed idempotente na inicialização quando a tabela estiver vazia, a partir das
chaves já presentes em `main.py:40-45` e dos acordes registrados em
`data/mapeamento_sequencias_famosas.txt:1-6`. Não há tabelas para músicas,
gêneros ou resultados derivados.

### API

- `GET /sequencias` — `json.dumps` da lista ordenada por `id`, com itens
  `{"id":0,"acordes":["Bm","G","D","A"],"chave":"BmGDA"}`. Catálogo aberto, sem
  login.
- `POST /sequencias` — corpo JSON `{"acordes":["G","Em"]}`. Validação: lista
  não vazia, de 1 a 32 acordes, cada string não vazia após `strip()` e sem `;`
  nem `,`; normalização com `lower()`. Duplicata por `chave_normalizada`
  retorna `409` com o item existente; entrada inválida retorna `400`; sucesso
  retorna `201` com o item criado. Todas as respostas continuam usando
  `json.dumps(...)`, não `jsonify`, preservando o `Content-Type: text/html`
  registrado em `AGENTS.md:45`.
- `GET /similares` mantém a assinatura (`sequencia`, `generos`, `pagina`); muda
  apenas a resolução da chave pelo catálogo e o filtro pela tag
  `musica.seqs_famosas` pelo matching em `cifra`. Não há `PUT`/`DELETE` nesta
  versão: o catálogo é append-only para proteger as seis sequências originais.

### Frontend

A rota `#/porsequencia` (`static/assets/js/routes.js:17-21`) deixa de usar os
quatro objetos hardcoded em `static/assets/js/controllers/sequencia.js:2-37` e
passa a carregar `GET /sequencias` na inicialização, mapeando cada item para
`{acorde, cor}` com a mesma cor `#2E1C74` já usada pelo `df-hex`
(`static/assets/js/directives/df-hex.js:1-12`). Um formulário simples permite
montar a sequência ordenada a partir de um seletor alimentado por
`GET /acordes` (`main.py:162-164`), enviar `POST /sequencias`, recarregar a lista
e selecionar a nova sequência. A busca continua com `createChordsString`
(`sequencia.js:55-61`) e `$http.get('similares?...')` (`sequencia.js:63-90`), mas
agora vale para qualquer item do catálogo. O dropdown de gêneros passa a vir de
`GET /generos` (`main.py:158-160`) em vez da constante local `GENEROS`
(`static/assets/js/app.js:6-58`); a origem continua sendo o CSV em memória.

## Validação de desempenho (benchmark)

Incluir um benchmark simples, a ser executado na próxima fase, para medir o custo
do matching em tempo de consulta sobre o catálogo real. Ele não é entrega
funcional: serve para confirmar com dados que "recalcular sob demanda" continua
aceitável antes de fixar a implementação da busca.

Procedimento: carregar o CSV exatamente como `main.py:49-98` (67.585 músicas
após descartar a primeira linha, conforme
`research/01-research-findings.md:49`) uma única vez no processo de teste. Para
cada uma das seis sequências-semente e para uma sequência nova representativa
de 4 acordes, aplicar a regra de `scripts/generate_data_set.py:7-24` sobre
`musicas.values()`, usando `musica.cifra` (`musica.py:16`) e
`time.perf_counter()`. Fazer 1 execução de aquecimento e 5 medições por
sequência; registrar mediana, p95 e quantidade de músicas varridas. Depois,
fazer uma medição ponta a ponta com o Flask test client em
`GET /similares?...&pagina=1`, incluindo `get_pagina` (`main.py:226-228`) e o
`json.dumps`, para separar o custo do matching do custo de serialização. O
harness existente `research/validate_matching.py:1-218` é o ponto de partida; o
benchmark pode ser um modo extra dele, sem alterar os testes de corretude.

Critério preliminar de aceite: mediana ≤ 300 ms e p95 ≤ 1 s por consulta
completa ao catálogo, no ambiente local de desenvolvimento com um único worker
(`Dockerfile:12`). A pesquisa não registrou SLA, então esse limite é critério de
decisão, não garantia de produção. Se as medições ficarem acima dele, os números
devem ser registrados e a decisão de manter o matching sob demanda ou rever a
abordagem deve ser tomada separadamente — isso não faz parte desta proposta.

## Alternativas consideradas e descartadas

- **`shelve`/`dbm` com a mesma regra de matching:** também não exigem dependência
  nova, mas são dicionários persistidos de forma opaca, sem `UNIQUE`, sem
  ordenação declarativa e com portabilidade/locking menos previsíveis. Para um
  catálogo que precisa de dedupe e listagem, SQLite dá as mesmas garantias com o
  mesmo custo de dependência (`research/01-research-findings.md:80-85`).
- **Pré-computar e persistir as músicas compatíveis no cadastro:** acelera a
  leitura, mas transforma um índice derivado do CSV em estado persistido e
  exigiria reindexação sempre que o CSV mudasse. Fica de fora porque só o
  catálogo de sequências deve ir para o banco.
- **Manter `seqs_famosas` do CSV como fonte exclusiva e apenas estender o
  dicionário em memória (`main.py:40-45`):** não atende ao requisito de
  persistência após reiniciar o container
  (`docs/features/sequencias-customizadas/00-enunciado.md:52-53`,
  `research/01-research-findings.md:74-85`).

## Escopo explícito

**Dentro do escopo:**

- SQLite apenas para o catálogo de sequências, com seed das seis originais.
- Matching em tempo real sobre `musica.cifra` do CSV em memória, com a paginação
  e o formato de resposta atuais.
- Persistência via `VOLUME /app/var` e volume nomeado documentado.
- `#/porsequencia` lendo o catálogo do backend e permitindo cadastro anônimo.
- Testes de regressão das seis sequências e teste de persistência após
  reinício/recriação do container.
- Benchmark de matching em tempo de consulta sobre as 67.585 músicas, com
  mediana/p95 e medição ponta a ponta, antes de fixar a busca sob demanda.

**Fora do escopo (e por quê):**

- Migrar músicas/gêneros para o banco: requisito fixo mantém o CSV carregado em
  memória (`docs/features/sequencias-customizadas/00-enunciado.md:60-62`,
  `main.py:49-98`).
- Login, edição/exclusão e moderação de sequências: o catálogo é aberto e
  anônimo; esta versão é append-only para preservar as originais.
- Modernizar AngularJS, trocar `json.dumps` por `jsonify` ou alterar o caminho
  de similares por acordes (`main.py:230-263`): mudanças de stack/API sem
  relação com este feature.
- Índice persistido de músicas por sequência: evita duplicar no banco um estado
  derivado do CSV.
