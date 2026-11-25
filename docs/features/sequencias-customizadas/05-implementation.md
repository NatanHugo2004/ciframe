# Implementação — Sequências de Acordes Customizadas

## Visão geral

A busca por sequência deixa de depender das tags `SEQ_FAMOSA` do CSV e passa a
calcular o matching em tempo de consulta sobre a cifra das músicas. O catálogo de
sequências é persistido em SQLite e pode ser consultado e ampliado por qualquer
pessoa, sem login. Músicas e gêneros continuam vindo do CSV carregado em memória.

## Backend

- `main.py` inicializa o banco SQLite na importação e semeia as 6 sequências
  originais com os IDs `0..5` e suas chaves legadas (`BmGDA`, `CGAmF`, `EmG`,
  `CA7DmG7`, `GmF`, `CC7FFm`).
- A tabela `sequences` guarda `id`, acordes em JSON, `chave_normalizada`
  (`bm;g;d;a`, com `UNIQUE`), `chave_legada` e `criado_em`.
- A regra de compatibilidade usa a cifra ordenada: minúsculas nos dois lados,
  trecho contíguo presente na cifra e nenhum acorde da música fora do conjunto
  de acordes da sequência.
- Para evitar recomputar a normalização de cada cifra, `main.py` prepara no
  carregamento do CSV uma string normalizada e um conjunto de acordes por música.

## API

- `GET /sequencias` retorna o catálogo ordenado por `id`, com itens no formato
  `{"id": 0, "acordes": ["Bm","G","D","A"], "chave": "BmGDA"}`.
- `POST /sequencias` recebe `{"acordes": ["G","Em"]}`, valida de 1 a 32 acordes
  sem `;` nem `,`, rejeita duplicatas e retorna a sequência criada.
- `GET /similares?sequencia=...` aceita tanto a lista com vírgulas
  (`Bm,G,D,A`) quanto a chave legada (`BmGDA`). Sequência desconhecida retorna
  `[]`. Paginação, filtro de gêneros e o formato dos objetos de música seguem
  inalterados.
- Todas as respostas continuam usando `json.dumps(...)`, com
  `Content-Type: text/html`.

## Frontend

- `#/porsequencia` carrega o catálogo via `GET /sequencias` em vez de usar as
  quatro sequências hardcoded em JavaScript.
- O formulário permite escolher acordes a partir de `GET /acordes`, montar a
  sequência ordenada, cadastrar via `POST /sequencias` e recarregar a lista.
- O dropdown de gêneros passou a usar `GET /generos`, que continua lendo os
  gêneros derivados do CSV.
- A busca ao clicar em uma sequência continua montando
  `similares?sequencia=...` com os acordes separados por vírgula.

## Execução e persistência

- O arquivo do catálogo fica em `var/sequences.sqlite3`; o caminho pode ser
  sobrescrito pela variável `SEQUENCES_DB_PATH`.
- `Dockerfile` declara `VOLUME /app/var` e o comando documentado usa
  `docker run -p 8080:8080 -v ciframe-sequences:/app/var ciframe` para manter o
  catálogo após reiniciar ou recriar o contêiner.
- `.dockerignore` exclui `var/`, evitando que um banco local seja copiado para a
  imagem durante o build.
