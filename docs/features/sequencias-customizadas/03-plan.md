# Plano — Sequências de Acordes Customizadas

> Plano executado a partir de `02-proposal.md`. Registra também as decisões
> tomadas durante a implementação (benchmark e critério revisado) e o estado da
> verificação.

## Current Context

- Backend: `main.py:49-98` carrega `data/top/dataset_final.csv` em memória na
  importação; `musica.py:16-18` expõe `cifra`, `acordes` e `seqs_famosas`.
- Busca antes da mudança: uma chave hardcoded era resolvida e a tag
  `seqs_famosas` era filtrada; não havia matching em tempo de consulta.
- Catálogo: seis sequências no backend, quatro repetidas em
  `static/assets/js/controllers/sequencia.js:2-37`; nada é persistido
  (`Dockerfile:1-12` não declara volume).
- Gap atendido: cadastro anônimo, persistência após restart, frontend refletindo
  o catálogo real e mesmos resultados para as seis sequências originais.

## Requirements

### Functional Requirements

- Qualquer pessoa cadastra uma sequência ordenada de acordes, sem login.
- Toda sequência cadastrada, inclusive as seis originais, pode ser usada em
  `GET /similares` com o mesmo formato de resposta atual.
- O catálogo de sequências sobrevive a reinício/recriação do container.
- `#/porsequencia` lista as sequências vindas do backend e permite cadastro.
- Duplicatas por sequência normalizada retornam `409`; entradas inválidas,
  `400`.

### Non-Functional Requirements

- Desempenho: mediana ≤ 500 ms e p95 ≤ 1 s por consulta completa às 67.585
  músicas, validado por benchmark antes de fixar a busca sob demanda.
- Compatibilidade: músicas/gêneros continuam no CSV em memória; endpoints
  continuam retornando `json.dumps(...)` como string.
- Deploy: container único, local-only, sem serviço externo nem dependência nova.

## Design Decisions

### 1. Regra de matching

Will implement a regra de `scripts/generate_data_set.py:7-24` porque:

- É a única que reproduziu `0/0` FP/FN nas seis sequências do CSV real
  (`research/01-research-findings.md:24-34`).
- Usa `musica.cifra`, que preserva ordem e repetição; `musica.acordes` perde
  ambas (`musica.py:17`).
- Trade-off: varredura das músicas em memória por requisição. O benchmark
  inicial com tokenização por requisição ficou em ~2,6 s e foi reprovado;
  passou a usar cifra normalizada (`str`) e conjunto de acordes preparados no
  carregamento do CSV, caindo para ~0,3 s. Tentativa com `bytes` ficou em
  ~0,4–0,47 s e foi descartada; o critério foi revisado para 500 ms.

### 2. Persistência

Will implement SQLite embarcado em `var/sequences.sqlite3` porque:

- `sqlite3` é stdlib, sem alteração em `requirements.txt:4-5`.
- `UNIQUE` resolve dedupe e a tabela é inspecionável; `shelve`/`dbm` foram
  descartados por serem opacos e sem restrição declarada.
- Trade-off: exige `VOLUME /app/var` e volume nomeado no comando `docker run`.

### 3. Contrato de API

Will manter `GET /similares` e adicionar `GET/POST /sequencias` porque:

- Preserva paginação, filtro de gêneros e `Content-Type: text/html` atuais.
- Forma legada sem vírgula (`BmGDA`) continua resolvida via `chave_legada`.
- Catálogo é append-only: sem `PUT`/`DELETE` nesta versão.

### 4. Frontend

Will substituir os quatro objetos hardcoded por `GET /sequencias` porque:

- A rota `#/porsequencia` já existe (`routes.js:17-21`); muda apenas a origem
  dos dados.
- `createChordsString` (`sequencia.js:55-61`) já gera o formato que a API aceita.
- Alternativa descartada: continuar mantendo lista fixa em JS.

## Technical Design

### 1. Core Components

```python
def chave_normalizada(acordes: list[str]) -> str: ...
def e_compativel(cifra: list[str], acordes: list[str]) -> bool: ...
def preparar_cifra(musica: Musica) -> None: ...
def e_compativel_musica(musica: Musica, sequencia: list[str]) -> bool: ...
def conectar_catalogo() -> sqlite3.Connection: ...
def inicializar_catalogo() -> None: ...
```

- `main.py` continua sendo o único módulo backend alterado.
- Helpers são internos; nenhuma classe pública nova é introduzida.

### 2. Data Models

```sql
CREATE TABLE IF NOT EXISTS sequences (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  acordes TEXT NOT NULL,
  chave_normalizada TEXT NOT NULL UNIQUE,
  chave_legada TEXT,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

- Seed idempotente com IDs `0..5` e `chave_legada` a partir de `main.py:40-45`
  e `data/mapeamento_sequencias_famosas.txt:1-6`.
- `acordes` guarda JSON com a forma de exibição, por exemplo `["Bm","G","D","A"]`.

### 3. Integration Points

- `GET /sequencias` → `json.dumps([...])` ordenado por `id`.
- `POST /sequencias` com `{"acordes":["G","Em"]}` → `201` com o item criado;
  `409` duplicata; `400` inválido.
- `GET /similares?sequencia=Bm,G,D,A` → resolve `chave_normalizada` e filtra
  `musicas.values()` por `e_compativel_musica`; `BmGDA` resolve por
  `chave_legada`.
- `GET /acordes` e `GET /generos` continuam servindo o frontend a partir do CSV
  em memória (`main.py:158-164`).

### 4. Files Changes

| Arquivo | Mudança |
|---|---|
| `main.py` | Inicializar SQLite/seed; trocar dict e tag por matching em `cifra`; adicionar `GET/POST /sequencias`; manter CSV e `json.dumps`. |
| `research/validate_matching.py` | Estender com testes de API/persistência e modo benchmark. |
| `static/assets/js/controllers/sequencia.js` | Carregar catálogo, montar formulário, usar `/generos`, enviar `POST` e recarregar lista. |
| `static/templates/sequencia.html` | Renderizar lista vinda da API e formulário de cadastro. |
| `Dockerfile` | Declarar `VOLUME /app/var`. |
| `.dockerignore` | Ignorar `var/` para não copiar banco local para a imagem. |
| `AGENTS.md` | Atualizar stack, comando `docker run`, verificação e gotcha para o volume nomeado `ciframe-sequences`. |

Não impactados: `musica.py`, `requirements.txt`, `data/top/dataset_final.csv`,
`routes.js`, `df-hex.js`, `app.js`. Não há arquivo novo de migração: a tabela é
criada com `CREATE TABLE IF NOT EXISTS` na inicialização.

## Implementation Plan

1. Phase 1: Base de dados, matching e benchmark
   - Criar `conectar_catalogo`/`inicializar_catalogo` com
     `CREATE TABLE IF NOT EXISTS`, usando `SEQUENCES_DB_PATH` (padrão
     `var/sequences.sqlite3`).
   - Implementar `chave_normalizada`, `e_compativel` (referência) e
     `e_compativel_musica` com cache preparado em `main.py`.
   - Adicionar o modo benchmark em `research/validate_matching.py` e executá-lo.
     Resultado obtido: ~2,6 s sem cache (reprovado), ~0,3 s com cache `str` e
     ~0,4–0,47 s com `bytes` (descartado); revisão registrada acima.
   - Reexecutar o benchmark com o cache `str`: mediana 262–302 ms e p95
     264–310 ms nas 7 sequências; critério atendido. `/similares` respondeu
     200 com 100 itens na página 1.
   - Expected timeline: Bloco 1 — antes de alterar endpoints.

2. Phase 2: API e regressão
   - Corrigir `/similares`, que durante o benchmark ainda referenciava o dict
     `sequencias` removido.
   - Implementar `GET /sequencias` e `POST /sequencias` com validação, dedupe
     `409` e códigos `400`/`201`.
   - Trocar em `/similares` a resolução por dict e o filtro por tag pelo catálogo
     e pelo matching, preservando paginação e forma dos objetos.
   - Rodar regressão das seis sequências e teste de persistência reabrindo o DB.
     Resultado: contagens 199/296/4/5/7/3 iguais às tags; `POST` 201/409/400;
     DB novo com 6 itens e DB original com 7 após "restart".
   - Expected timeline: Bloco 2 — após benchmark aceitável.

3. Phase 3: Frontend e deploy local
   - Substituir sequências hardcoded por `GET /sequencias`; adicionar
     formulário com seletor vindo de `GET /acordes`; trocar `GENEROS` por
     `GET /generos`.
   - Ajustar `Dockerfile`, `.dockerignore` e `AGENTS.md` para o volume nomeado.
   - Verificar restart e recriação do container com o mesmo volume. Docker
     indisponível neste ambiente (`npipe:////./pipe/dockerDesktopLinuxEngine`);
     persistência verificada por reabertura do DB (6 itens no seed, 7 no
     original) e sintaxe do JS validada com `node --check`.
   - Expected timeline: Bloco 3 — entrega final.

## Testing Strategy

### Unit Tests

- Casos sintéticos de ordem, repetição e `lower()` em `e_compativel`
  (`validate_matching.py:121-136`); conferir que `e_compativel_musica` dá o
  mesmo resultado nas seis sequências do CSV.
- Validação de `POST`: vazio, acorde com `,`/`;`, mais de 32 acordes, duplicata.
- Seed idempotente: segunda inicialização não duplica IDs `0..5`.

### Integration Tests

- Flask test client: `GET /sequencias` com seis itens; `POST` novo; `409` na
  repetição; `/similares` com vírgula e com chave legada retornando o mesmo.
- Filtro de gêneros e paginação iguais ao baseline em
  `research/01-research-findings.md:63-72`; `XYZ` retornando `[]`.
- Persistência: fechar e reabrir o DB em diretório temporário via
  `SEQUENCES_DB_PATH`; conferir o item após reinício do container.
- Benchmark: 6 sequências originais + 1 nova, 1 aquecimento e 5 medições,
  mediana/p95 e medição ponta a ponta em `/similares`.

## Observability

### Logging

### Metrics

## Future Considerations

### Potential Enhancements

### Known Limitations

## Dependencies

### Development Dependencies

## Security Considerations

- Catálogo é anônimo por requisito; não há autenticação nem autorização.
- Validar acordes antes de persistir para limitar tamanho e evitar caracteres
  que quebrem `chave_normalizada` ou o JSON de exibição.
- Usar consultas SQL parametrizadas; nunca interpolar entrada do usuário.
- Não aceitar caminho de arquivo do cliente: `SEQUENCES_DB_PATH` é configuração
  do servidor.

## Rollout Strategy

1. Development phase: implementar com `SEQUENCES_DB_PATH` apontando para
   diretório temporário; nenhum `*.sqlite3` versionado.
2. Testing phase: executar regressão, persistência e benchmark.
3. Staging deployment: não existe staging documentado; simular localmente com
   `docker run -v ciframe-sequences:/app/var`.
4. Production deployment: `docker build -t ciframe .` seguido de
   `docker run -p 8080:8080 -v ciframe-sequences:/app/var ciframe`.
5. Monitoring period: conferir `/generos`, `/sequencias` e a busca após
   `docker restart`; sem métricas de runtime incluídas nesta mudança.

## References

- `docs/features/sequencias-customizadas/00-enunciado.md`
- `docs/features/sequencias-customizadas/01-research.md`
- `docs/features/sequencias-customizadas/02-proposal.md`
- `research/01-research-findings.md`
- `research/validate_matching.py`
- `docs/adr/0001-local-only-docker-deploy.md`
- `docs/adr/0002-persist-custom-sequences.md`
- `~\reppit-framework\templates\design_doc_template.md`
