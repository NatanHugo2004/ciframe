# Relatório de testes — Sequências de Acordes Customizadas

## Cobertura

Automação em `research/validate_matching.py:1-363`, executada com o test client do
Flask (sem servidor e sem navegador):

- Teste 1 (`research/validate_matching.py:121-136`): 6 casos sintéticos da regra
  de matching — ordem, contiguidade, repetição, normalização para minúsculas e
  `C/E ≠ C`.
- Teste 2 (`research/validate_matching.py:139-149`): no CSV real, compara por
  `id_unico_musica` os conjuntos calculados pela regra com as tags `SEQ_FAMOSA`
  das 6 sequências (67.585 músicas após o descarte da primeira linha).
- Teste 3 (`research/validate_matching.py:152-164`): 4 definições alternativas
  continuam gerando falsos positivos; impede a troca ingênua da regra.
- Teste 4 (`research/validate_matching.py:167-235`): `GET /similares` — páginas
  1 e 2, forma com vírgula igual à concatenada, `XYZ → []`, filtro
  `generos=MPB` e `Content-Type: text/html`.
- Teste 5 (`research/validate_matching.py:238-310`): `GET /sequencias` com os
  IDs `0..5`, `POST /sequencias` com `201`/`409`/`400`, busca pela sequência
  cadastrada, equivalência entre `e_compativel` e `e_compativel_musica` nas 6
  sequências e persistência simulada por troca de `SEQUENCES_DB_PATH`.
- Benchmark (`--benchmark`, `research/validate_matching.py:313-350`): 7
  sequências, 1 aquecimento e 5 medições com `perf_counter`, mediana/p95 e um
  smoke test de `/similares`.

## Teste de regressão obrigatório

As 6 sequências originais (`main.py:37-44`, `SEQUENCIAS_SEED`) precisam
continuar retornando os mesmos resultados de antes da introdução do banco.

Verificação: `teste_csv` comparou os conjuntos de músicas calculados pela regra
com as tags do CSV, e `teste_endpoint` comparou as respostas paginadas da API com
uma referência independente montada sobre `musica.cifra`.

| ID | Sequência | Com tag | Calculado/API pág. 1 | API pág. 2 | Resultado |
|---:|---|---:|---:|---:|:---:|
| 0 | `BmGDA` | 199 | 199 | 99 | igual |
| 1 | `CGAmF` | 296 | 296 | 100 | igual |
| 2 | `EmG` | 4 | 4 | 0 | igual |
| 3 | `CA7DmG7` | 5 | 5 | 0 | igual |
| 4 | `GmF` | 7 | 7 | 0 | igual |
| 5 | `CC7FFm` | 3 | 3 | 0 | igual |

Resultado: **passou**. `TODOS OS TESTES PASSARAM`. As formas `Bm,G,D,A` e
`BmGDA` retornaram a mesma lista, `generos=MPB` retornou 1 música (igual ao
corte tag ∩ MPB) e o `Content-Type` permaneceu `text/html; charset=utf-8`.

Benchmark: mediana de 262–302 ms e p95 de 264–310 ms nas 7 sequências, dentro
do critério registrado em `03-plan.md` (mediana ≤ 500 ms, p95 ≤ 1 s);
`/similares` respondeu `200` com 100 itens na página 1.

## Como rodar

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONUTF8='1'
C:\Users\natan\AppData\Local\Temp\opencode\ciframe-venv\Scripts\python.exe research\validate_matching.py
```

Para o benchmark:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONUTF8='1'
C:\Users\natan\AppData\Local\Temp\opencode\ciframe-venv\Scripts\python.exe research\validate_matching.py --benchmark
```

## O que ficou de fora

- Execução em navegador de `#/porsequencia`: cadastro, renderização do catálogo
  e busca foram verificados por leitura do código e pelos testes de API, não por
  teste E2E.
- Container Docker: o daemon não estava disponível
  (`npipe:////./pipe/dockerDesktopLinuxEngine`). A persistência foi simulada
  abrindo um segundo `SEQUENCES_DB_PATH` (6 itens no seed) e voltando ao
  original (7 itens).
- Concorrência de `POST /sequencias`: a checagem de duplicata e o `INSERT` não
  são atômicos (`main.py:325-341`); não há teste com requisições paralelas.
- **Regressão detectada na revisão e ainda não coberta pela suíte:** `GET
  /musicas` (`main.py:294-296`) e `GET /musica/<m_id>/` (`main.py:346-348`)
  retornam `500` porque `preparar_cifra` (`main.py:107-111`) adiciona
  `acordes_normalizados` como `frozenset` ao `__dict__` da música, que não é
  serializável por `json.dumps`. Confirmado com o test client; precisa de fix e
  teste de regressão.
