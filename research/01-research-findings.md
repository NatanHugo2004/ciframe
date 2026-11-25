# Pesquisa — Sequências de Acordes Customizadas (estado atual)

## Resumo

A busca por sequência não calcula matching em tempo real: `GET /similares?sequencia=...` resolve uma chave `0..5` e filtra a tag `musica.seqs_famosas` do CSV (`main.py:40-45`, `main.py:170-223`). A regra que gerou essas tags está em `scripts/generate_data_set.py:7-24`: minúsculas nos dois lados, substring contígua na cifra e exigência de que todos os acordes da música pertençam ao conjunto da sequência; ela reproduziu exatamente as seis tags do CSV real (514 músicas), enquanto as alternativas testadas só geraram falsos positivos. `musica.acordes` perde ordem e repetição (`musica.py:17`); `musica.cifra` preserva o que a regra usa. Não há banco: o CSV é lido na importação e o `Dockerfile` não declara volume (`AGENTS.md:9-11`, `main.py:49-98`, `Dockerfile:1-12`). O frontend `#/porsequencia` mostra 4 sequências hardcoded e chama a mesma API, contra 6 no backend (`routes.js:17-21`, `sequencia.js:2-37`, `main.py:40-45`). Somente código, dados e testes executados são registrados aqui.

## 1. Algoritmo de matching

- **Código atual:** `main.py:190-197` remove vírgulas, resolve a chave e chama `get_similares_por_sequencia`, que apenas testa `str(id_seq) in musica.seqs_famosas` (`main.py:203-223`). A tag vem da coluna 7 (`main.py:33,63,69-72`, `musica.py:18`). Não há comparação com `cifra`/`acordes` em `main.py`.
- **Origem da tag:** `scripts/generate_data_set.py:69-89` extrai `str_notas` e chama `get_famosas`; a regra está em `scripts/generate_data_set.py:7-24` — `lower()` (linha 12), substring exata `bm;g;d;a` etc. (linha 13) e todos os acordes da música dentro do conjunto da sequência (linhas 16-23).
- **IDs:** 0 `BmGDA`, 1 `CGAmF`, 2 `EmG`, 3 `CA7DmG7`, 4 `GmF`, 5 `CC7FFm` (`main.py:40-45`, `data/mapeamento_sequencias_famosas.txt:1-6`).

Respostas diretas, com testes em `research/validate_matching.py:121-129`:

| Pergunta | Evidência |
|---|---|
| Ordem importa? | Sim: `['Em','G']` → `True`; `['G','Em']` → `False` (`validate_matching.py:123-124`). |
| Repetições importam? | Não impedem: `['Em','G','Em']` → `True` (`:126`). Se a sequência tiver repetição, a substring a exige (`generate_data_set.py:13`). |
| Normalizar? | `lower()` está no gerador (`generate_data_set.py:12`), não em `main.py:53,11-23`; `C/E` não casa com `C` (`validate_matching.py:128`). Com e sem `lower()` as contagens no CSV foram iguais. |
| Usar `musica.acordes`? | Não reproduz as tags: `musica.py:17` faz `list(set(cifra))`; definição por conjunto gerou 5.569–14.156 FP. |

Definição observada: com minúsculas, `musica.cifra` deve conter a sequência delimitada por `;` em qualquer posição, e a música não pode ter acorde fora do conjunto da sequência (`generate_data_set.py:8,13`).

Alternativas medidas no CSV (`FP/FN` em ID 0→5; `validate_matching.py:152-164`):

| Definição | FP/FN |
|---|---|
| Regra do gerador | `0/0` em todas; conjuntos idênticos |
| Substring sem regra de acordes | `773/0`, `950/0`, `3700/0`, `91/0`, `1515/0`, `141/0` |
| Lista contígua | `667/0`, `920/0`, `3106/0`, `91/0`, `1032/0`, `129/0` |
| Subsequência não contígua | `4564/0`, `5591/0`, `13639/0`, `422/0`, `3634/0`, `277/0` |
| Conjunto de acordes | `5569/0`, `6598/0`, `14156/0`, `577/0`, `3840/0`, `362/0` |

Exemplos: `data/top/dataset_final.csv:210` tem `D,A,Bm,G` e `Em`, fica sem tag; `:13` tem `Em,G` entre outros acordes, fica sem tag; `:20380` tem tag `2` e `Em,G` a partir da segunda posição.

## 2. Validação executada

Script: `research/validate_matching.py:1-218`; Flask `3.1.3` (`requirements.txt:4`). Comando em PowerShell, na raiz de `ciframe`:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONUTF8='1'
C:\Users\natan\AppData\Local\Temp\opencode\ciframe-venv\Scripts\python.exe research\validate_matching.py
```

`PYTHONUTF8=1` foi necessário no Windows porque `main.py:49` abre o CSV sem `encoding`; sem isso houve `UnicodeDecodeError` cp1252. Com UTF-8: `TODOS OS TESTES PASSARAM`.

- Teste 1 (`validate_matching.py:121-136`): 6 casos sintéticos, todos conformes.
- Teste 2 (`:139-149`): `data/top/dataset_final.csv:1` é dado, não cabeçalho; `main.py:50` a descarta → 67.585 músicas de 67.586 linhas. Tags: `''`=67.071; IDs 0–5 = 199, 296, 4, 5, 7, 3.

| ID | Sequência | Tag | Calculado | Igual |
|---:|---|---:|---:|:---:|
| 0 | BmGDA | 199 | 199 | sim |
| 1 | CGAmF | 296 | 296 | sim |
| 2 | EmG | 4 | 4 | sim |
| 3 | CA7DmG7 | 5 | 5 | sim |
| 4 | GmF | 7 | 7 | sim |
| 5 | CC7FFm | 3 | 3 | sim |

- Teste 3 (`:152-164`): tabela acima; nenhuma alternativa reproduziu as tags.
- Teste 4 (`:167-209`): endpoint comparado a `get_pagina(get_similares_por_sequencia(...), pagina)`.

| Query | Pág. 1 | Pág. 2 | Igual à tag | Com vírgulas = concatenada |
|---|---:|---:|:---:|:---:|
| BmGDA | 100 | 99 | sim | sim |
| CGAmF | 100 | 100 | sim | sim |
| EmG | 4 | 0 | sim | sim |
| CA7DmG7 | 5 | 0 | sim | sim |
| GmF | 7 | 0 | sim | sim |
| CC7FFm | 3 | 0 | sim | sim |

Extras: `XYZ` → `[]`; `BmGDA&generos=MPB` → 1, igual a tag ∩ MPB; `Content-Type: text/html; charset=utf-8` (`AGENTS.md:45-46`); vírgulas equivalem porque `main.py:191` usa `replace(',','')`. Paginação: `main.py:35,196,226-228`.

## 3. Banco de dados

- Sem banco: `AGENTS.md:9-11`, `main.py:49-98`, `AGENTS.md:45`.
- `requirements.txt:4-5`: só Flask e gunicorn. `Dockerfile:1-12`: `python:3.9-slim`, `pip install -r requirements.txt`, `COPY . .`, gunicorn `:8080`, sem `VOLUME`; comando `docker run -p 8080:8080 ciframe` sem `-v` (`AGENTS.md:22-25`).
- ADR local-only: `docs/adr/0001-local-only-docker-deploy.md:9-16`; ADR de persistência ainda é template: `docs/adr/0002-persist-custom-sequences.md:1-8`. Nenhum `*.db`/`*.sqlite*` no repositório.

| Opção | Evidência / dependência | Persistência observada |
|---|---|---|
| `sqlite3`, `dbm`, `shelve` | Importaram no Python 3.11 local (sqlite 3.38.4); ausentes de `requirements.txt` | Arquivo em `/app` fica na camada gravável; novo `docker run` recria a imagem (`AGENTS.md:24`, `Dockerfile:1-12`) |
| DuckDB, TinyDB etc. | Não aparecem no repositório; exigiriam linha em `requirements.txt:4-5`, instalada por `Dockerfile:5-6` | Mesma limitação de filesystem; não exigem serviço externo se usados como arquivo local |

`COPY . .` (`Dockerfile:8`) leva ao build o que está no repo; `.dockerignore:1-4` exclui só `.git`, `.venv`, `__pycache__`, `*.pyc`. Escritas em runtime não voltam para a imagem. `docker run --rm python:3.9-slim ...` falhou porque o daemon Docker não está ativo; disponibilidade na imagem base não foi executada.

## 4. Frontend `#/porsequencia`

- Rota/template: `routes.js:17-21`, `index.html:123,125-147`, `sequencia.html:6-8`, `df-hex.js:1-12`.
- Quatro hardcoded em `sequencia.js:2-37`: `Bm,G,D,A`→ID 0; `C,G,Am,F`→1; `Gm,F`→4; `C,C7,F,Fm`→5. Faltam IDs 2 e 3 (`main.py:42-43`). `index:1` (`sequencia.js:3,11,19,25`) não é lido; não há cadastro nem endpoint de catálogo.
- Busca: `sequencia.js:55-90` junta com vírgulas, monta `similares?sequencia=`, acrescenta `&generos=`, faz `$http.get` relativo (`apiUrl=""`), preenche `vm.musics` ou mostra erro. Gêneros vêm de `app.js:6-58`; `ng-change` repete a busca (`sequencia.html:24-29`).
- Cards: ordenados por popularidade, com `ng-hide="music.diferenca.length"` (`sequencia.html:42-43`); a API de sequência não devolve `diferenca` (`main.py:210-220`). Clique no acorde limpa (`sequencia.js:92-95`); clique no card abre URL (`:97-99`).

Fluxo: HTMLs → `generate_data_set.py:7-24,69-89` → `SEQ_FAMOSA` no CSV → `main.py:49-98` → `Musica.cifra/acordes/seqs_famosas` (`musica.py:16-18`) → `main.py:190-223` → JSON paginado → `sequencia.js:63-90` → `sequencia.html:40-58`. O backend deriva gêneros do CSV (`main.py:65-66,92,158-160`) e a página usa `app.js:6-58`; o caminho de similares por acordes (`main.py:230-263`) é distinto e não é acionado por `sequencia`.

Não executado: container Docker (daemon indisponível) e frontend em navegador; comportamento do frontend verificado por leitura dos arquivos citados e pelo teste do endpoint.
