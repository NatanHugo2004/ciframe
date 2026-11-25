# Pesquisa — Sequências de Acordes Customizadas

> Documento completo também disponível em `research/01-research-findings.md`.
> Este arquivo responde diretamente às quatro perguntas da fase de pesquisa com
> evidência de código e testes executados. Não há proposta de mudança aqui.

## Resumo

Hoje a busca por sequência não calcula matching em tempo real: `GET /similares?sequencia=...` resolve uma chave `0..5` e filtra a tag `musica.seqs_famosas` vinda do CSV (`main.py:40-45`, `main.py:170-223`). A regra que gerou essas tags está em `scripts/generate_data_set.py:7-24`: minúsculas nos dois lados, substring exata e contígua na cifra inteira e exigência de que todos os acordes da música pertençam ao conjunto de acordes da sequência. Essa regra reproduziu exatamente os seis conjuntos de tags no CSV real (514 músicas marcadas), enquanto definições mais simples geraram de 91 a 14.156 falsos positivos por sequência. `musica.acordes` perde ordem e repetição (`musica.py:17`); a cifra ordenada em `musica.cifra` preserva a informação usada. A página `#/porsequencia` mostra quatro sequências hardcoded em JavaScript e chama essa mesma API, enquanto o backend conhece seis (`static/assets/js/controllers/sequencia.js:2-37`, `main.py:40-45`).

## 1. Algoritmo de matching

**O que existe hoje.** `main.py:190-197` lê `sequencia`, remove vírgulas com `replace(',','')`, procura a chave no dicionário `sequencias` e chama `get_similares_por_sequencia(id_seq, generos_key)`. Essa função apenas testa `str(id_seq) in musica.seqs_famosas` (`main.py:203-223`). A coluna 7 do CSV é dividida por `;` em `main.py:63` e passada para `Musica` em `main.py:69-72` / `musica.py:18`. Não há comparação entre a sequência recebida e `musica.cifra` ou `musica.acordes`.

**Origem das tags.** `scripts/generate_data_set.py:69-89` extrai `str_notas` dos `<b>` sob `#cifra_tom` e chama `get_famosas`. Dentro dela (`scripts/generate_data_set.py:7-24`): as sequências são `bm;g;d;a`, `c;g;am;f`, `em;g`, `c;a7;dm;g7`, `gm;f`, `c;c7;f;fm` (linha 8); a cifra é convertida para minúsculas (linha 12); a sequência precisa aparecer como substring exata da cifra (linha 13); cada acorde da música precisa estar no conjunto de acordes da sequência (linhas 16-23). O mapeamento ID ↔ acordes está em `data/mapeamento_sequencias_famosas.txt:1-6`.

**Respostas diretas.**

- Ordem importa: `em;g` e `g;em` são strings distintas. Teste em `research/validate_matching.py:123-124`: `['Em','G']` → `True`; `['G','Em']` → `False`.
- Repetições na música não impedem o match, desde que o trecho contíguo exista e todos os tokens sejam do conjunto da sequência: `['Em','G','Em']` → `True` (`research/validate_matching.py:126`). Se a sequência tiver acorde repetido, a substring exige a repetição no trecho (`scripts/generate_data_set.py:13`).
- Normalização: o gerador aplica `lower()` nas duas pontas (`scripts/generate_data_set.py:12`); `main.py:53` e `main.py:11-23` não aplicam. Variações são tokens distintos: `C/E` não casa com `C` (`research/validate_matching.py:128`). No CSV atual, as versões com e sem `lower()` deram as mesmas contagens; a fonte histórica, porém, normaliza.
- `musica.acordes` não serve para reproduzir as tags: `musica.py:17` faz `list(set(cifra))`, removendo ordem e duplicatas. A definição por conjunto gerou 5.569 a 14.156 falsos positivos por sequência.
- Definição observada: com minúsculas, a cifra ordenada em `musica.cifra` deve conter a sequência como substring delimitada por `;`, e a música não pode conter acorde fora do conjunto da sequência. O delimitador vem de `scripts/generate_data_set.py:8,13`.

**Definições comparadas no CSV real** (FP = calculado sem tag; FN = com tag e não calculado; `research/validate_matching.py:152-164`):

| Definição | FP/FN em BmGDA, CGAmF, EmG, CA7DmG7, GmF, CC7FFm |
|---|---|
| Regra do gerador | `0/0` em todas; conjuntos idênticos |
| Substring contígua sem regra de acordes | `773/0`, `950/0`, `3700/0`, `91/0`, `1515/0`, `141/0` |
| Lista contígua | `667/0`, `920/0`, `3106/0`, `91/0`, `1032/0`, `129/0` |
| Subsequência não contígua | `4564/0`, `5591/0`, `13639/0`, `422/0`, `3634/0`, `277/0` |
| Conjunto de acordes | `5569/0`, `6598/0`, `14156/0`, `577/0`, `3840/0`, `362/0` |

Exemplos: `data/top/dataset_final.csv:210` contém `D,A,Bm,G` e também `Em`, ficando sem tag; `data/top/dataset_final.csv:13` contém `Em,G` entre vários acordes e fica sem tag; `data/top/dataset_final.csv:20380` tem tag `2` e o trecho `Em,G` a partir da segunda posição.

## 2. Validação da hipótese

**Teste executado.** Script `research/validate_matching.py:1-218`, com Flask `3.1.3` (`requirements.txt:4`). Comando em PowerShell, na raiz de `ciframe`, com venv temporário contendo somente Flask:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONUTF8='1'
C:\Users\natan\AppData\Local\Temp\opencode\ciframe-venv\Scripts\python.exe research\validate_matching.py
```

`PYTHONUTF8=1` foi necessário neste Windows porque `main.py:49` abre o CSV sem `encoding`; sem isso houve `UnicodeDecodeError: 'charmap' codec can't decode byte 0x81`. Com UTF-8, o script terminou com `TODOS OS TESTES PASSARAM`.

**Resultados.** `data/top/dataset_final.csv:1` contém dado, não cabeçalho; `main.py:50` a descarta, restando 67.585 músicas de 67.586 linhas. Tags: `''` = 67.071; IDs 0 a 5 = 199, 296, 4, 5, 7 e 3.

| ID | Sequência | Com tag | Calculado | Iguais |
|---:|---|---:|---:|:---:|
| 0 | BmGDA | 199 | 199 | sim |
| 1 | CGAmF | 296 | 296 | sim |
| 2 | EmG | 4 | 4 | sim |
| 3 | CA7DmG7 | 5 | 5 | sim |
| 4 | GmF | 7 | 7 | sim |
| 5 | CC7FFm | 3 | 3 | sim |

Teste de endpoint com Flask test client (`research/validate_matching.py:167-209`), comparando a resposta com `get_pagina(get_similares_por_sequencia(...), pagina)`:

| Query | Página 1 | Página 2 | Igual à tag | `Bm,G,D,A` = `BmGDA` |
|---|---:|---:|:---:|:---:|
| BmGDA | 100 | 99 | sim | sim |
| CGAmF | 100 | 100 | sim | sim |
| EmG | 4 | 0 | sim | sim |
| CA7DmG7 | 5 | 0 | sim | sim |
| GmF | 7 | 0 | sim | sim |
| CC7FFm | 3 | 0 | sim | sim |

`sequencia=XYZ` retorna `[]`; `generos=MPB` com `BmGDA` retorna 1 música, idêntica ao recorte tag ∩ MPB; `Content-Type` é `text/html; charset=utf-8` (`AGENTS.md:45-46`). A equivalência com vírgulas vem de `main.py:191`. A paginação de 100 itens está em `main.py:35,196,226-228`.

## 3. Banco de dados

**Estado atual.** `AGENTS.md:9-11` diz explicitamente que não há banco; `main.py:49-98` carrega o CSV na importação; `AGENTS.md:45` exige reinício após editar CSV. `requirements.txt:4-5` tem só Flask e gunicorn. `Dockerfile:1-12` usa `python:3.9-slim`, instala esse requirements, faz `COPY . .` e roda gunicorn na 8080, sem `VOLUME`; `AGENTS.md:22-25` mostra `docker run -p 8080:8080 ciframe`, sem `-v`. `docs/adr/0001-local-only-docker-deploy.md:9-16` registra container único local-only e nenhum alvo de cloud definido. `docs/adr/0002-persist-custom-sequences.md:1-8` ainda é template. Não há `*.db`/`*.sqlite*` no repositório.

**Implicações observadas por opção.** No interpretador local Python 3.11, `sqlite3` (3.38.4), `dbm` e `shelve` importaram sem instalação adicional; não estão em `requirements.txt`. DuckDB e TinyDB não aparecem em nenhum arquivo e exigiriam linha nova em `requirements.txt:4-5`, instalada por `Dockerfile:5-6`, sem serviço externo se usados como arquivo local. Para qualquer opção baseada em arquivo, `COPY . .` (`Dockerfile:8`) copia o estado do repositório no build (`.dockerignore:1-4` exclui só `.git`, `.venv`, `__pycache__`, `*.pyc`), mas escritas feitas durante `docker run` ficam na camada gravável do contêiner; sem `-v` ou `VOLUME`, um novo contêiner criado da imagem não as contém.

**Limitação da verificação.** `docker run --rm python:3.9-slim ...` falhou porque o daemon Docker não está ativo neste ambiente (`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`). A disponibilidade de `sqlite3` dentro da imagem base não foi confirmada por execução; as afirmações acima sobre o container vêm dos arquivos do repositório.

## 4. Frontend existente

`static/assets/js/routes.js:17-21` liga `#/porsequencia` a `templates/sequencia.html` e `SequenciaController`. `static/index.html:123,125-147` carrega `ng-view`, AngularJS 1.4.9, jQuery e o controller. `static/templates/sequencia.html:6-8` desenha as sequências com `df-hex` (`static/assets/js/directives/df-hex.js:1-12`).

As quatro sequências hardcoded em `static/assets/js/controllers/sequencia.js:2-37` são `Bm,G,D,A` (ID 0), `C,G,Am,F` (ID 1), `Gm,F` (ID 4) e `C,C7,F,Fm` (ID 5). Faltam `EmG` (ID 2) e `CA7DmG7` (ID 3), presentes em `main.py:42-43`. O campo `index: 1` aparece nos quatro objetos (`sequencia.js:3,11,19,25`) e não é lido em `sequencia.js` ou `sequencia.html`. Não há formulário de cadastro nem chamada a endpoint de catálogo.

`vm.pesquisarPorSequencia` (`sequencia.js:63-90`) guarda a sequência clicada, inicia progresso, monta `similares?sequencia=` com acordes separados por vírgula (`createChordsString`, linhas 55-61), acrescenta `&generos=` quando há gênero selecionado e faz `$http.get` relativo à mesma origem (`apiUrl = ""`, linhas 72,77). No sucesso preenche `vm.musics`; no erro troca a mensagem para `"Ops! Algo errado."`. O dropdown usa `GENEROS` hardcoded em `static/assets/js/app.js:6-58` (`sequencia.js:43`) e seu `ng-change` repete a busca com `vm.minhaSequencia` (`sequencia.html:24-29`). Cards são ordenados por popularidade e escondidos quando `music.diferenca.length` é truthy (`sequencia.html:42-43`); como `get_similares_por_sequencia` não devolve `diferenca` (`main.py:210-220`), nada é escondido. Clicar no acorde selecionado chama `limparPesquisa` (`sequencia.html:34`, `sequencia.js:92-95`); clicar no card abre `music.url` (`sequencia.js:97-99`).

## Registro das descobertas (fluxo entre componentes)

HTMLs → `scripts/generate_data_set.py:7-24,69-89` → coluna `SEQ_FAMOSA` no CSV → `main.py:49-98` → `Musica.cifra`, `Musica.acordes`, `Musica.seqs_famosas` (`musica.py:16-18`) → `main.py:190-223` → JSON paginado → `sequencia.js:63-90` → cards em `sequencia.html:40-58`. O filtro de gêneros da página vem de `app.js:6-58`, enquanto o backend deriva `generos` do CSV em `main.py:65-66,92` e os aplica em `main.py:265-272`. O caminho de "similares por acordes" (`main.py:230-263`) é diferente e usa interseção/diferença de conjuntos; ele não é acionado quando o request contém `sequencia`.

## Trade-offs identificados

Não há decisão tomada nesta fase. As únicas implicações verificáveis são:

- **Algoritmo**: a regra do gerador é a única, entre as cinco testadas, que produziu zero FP/FN nas seis sequências; todas as demais produziram apenas falsos positivos (`research/validate_matching.py:152-164`).
- **Banco**: `sqlite3`, `dbm` e `shelve` não exigem entrada nova em `requirements.txt`; bancos não presentes nesse arquivo exigiriam inclusão explícita. Para qualquer arquivo local, a ausência de `-v`/`VOLUME` em `AGENTS.md:22-25` / `Dockerfile:1-12` significa que escritas em runtime não voltam para a imagem.
- **Frontend**: a lista atual do controller cobre 4 dos 6 IDs do backend e o dropdown de gêneros é uma constante local, enquanto `/generos` existe no backend (`main.py:158-160`).
