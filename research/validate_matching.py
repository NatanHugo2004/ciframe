# coding: utf-8
"""Validação reprodutível das perguntas 1 e 2 de docs/features/sequencias-customizadas/01-research.md.

Execução (a partir da raiz do repositório, com Flask 3.1.3 instalado):

    python research/validate_matching.py

O script usa apenas a biblioteca padrão para a parte de CSV/matching. A parte de
endpoint importa main.py e usa o test client do Flask, sem iniciar servidor.
"""
import json
import os
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

# main.py inicializa o catálogo na importação; usar um DB temporário evita
# criar var/sequences.sqlite3 no repositório durante os testes.
DB_DIR = tempfile.mkdtemp(prefix="ciframe-sequences-")
os.environ["SEQUENCES_DB_PATH"] = os.path.join(DB_DIR, "sequences.sqlite3")

CSV = ROOT / "data" / "top" / "dataset_final.csv"

# main.py:40-45 + data/mapeamento_sequencias_famosas.txt:1-6
SEQ_CHORDS = {
    "BmGDA": ["Bm", "G", "D", "A"],
    "CGAmF": ["C", "G", "Am", "F"],
    "EmG": ["Em", "G"],
    "CA7DmG7": ["C", "A7", "Dm", "G7"],
    "GmF": ["Gm", "F"],
    "CC7FFm": ["C", "C7", "F", "Fm"],
}

QUERY_TO_KEY = {
    "BmGDA": "BmGDA",
    "CGAmF": "CGAmF",
    "EmG": "EmG",
    "CA7DmG7": "CA7DmG7",
    "GmF": "GmF",
    "CC7FFm": "CC7FFm",
}


def limpa_cifra(raw_cifra):
    """Cópia de main.py:11-23."""
    cifra = []
    for m in raw_cifra:
        if m.strip() != "":
            if "|" in m:
                cifra.append(m.split("|")[0].split()[0])
            else:
                cifra += [token for token in m.split()]
    return cifra


def load_rows():
    """Cópia do parser de main.py:49-63, mantendo o número da linha do CSV."""
    rows = []
    with open(CSV, encoding="utf-8", errors="replace") as f:
        f.readline()  # main.py:50 descarta a primeira linha
        for lineno, line in enumerate(f, start=2):
            line = line.replace('"', "").replace("NA", "")[:-1]
            parts = line.split(",")
            rows.append({
                "lineno": lineno,
                "id_unico_musica": "%s_%s" % (parts[0], parts[1]),
                "nome_musica": parts[3],
                "genero": parts[4],
                "seqs_famosas": parts[7].split(";"),
                "cifra": limpa_cifra(parts[8].split(";")) if parts[8] != "" else [],
            })
    return rows


def generator_match(cifra, sequencia):
    """Regra implementada em scripts/generate_data_set.py:7-24.

    1. minúsculas nos dois lados (linha 12);
    2. substring exata e contígua da sequência na cifra inteira (linha 13);
    3. todo acorde da música pertence ao conjunto de acordes da sequência
       (linhas 16-23).
    """
    cifra_normalizada = ";".join(cifra).lower()
    sequencia_normalizada = ";".join(sequencia).lower()
    if sequencia_normalizada not in cifra_normalizada:
        return False
    permitidos = {acorde.lower() for acorde in sequencia}
    return all(acorde.lower() in permitidos for acorde in cifra)


def ids_calculados(rows, sequencia):
    return {r["id_unico_musica"] for r in rows if generator_match(r["cifra"], sequencia)}


def ids_tag(rows, id_seq):
    return {r["id_unico_musica"] for r in rows if str(id_seq) in r["seqs_famosas"]}


def definicoes_alternativas():
    def contiguo(tokens, seq):
        a = [t.lower() for t in tokens]
        b = [t.lower() for t in seq]
        return any(a[i:i + len(b)] == b for i in range(len(a) - len(b) + 1))

    def substring(tokens, seq):
        return ";".join(seq).lower() in ";".join(tokens).lower()

    def subseq(tokens, seq):
        it = iter([t.lower() for t in tokens])
        return all(any(x == t.lower() for x in it) for t in seq)

    def conjunto(tokens, seq):
        return {t.lower() for t in seq} <= {t.lower() for t in tokens}

    return {
        "substring_contigua_sem_regra_de_acordes": substring,
        "lista_contigua": contiguo,
        "subsequencia_nao_contigua": subseq,
        "conjunto_de_acordes (musica.acordes)": conjunto,
    }


def teste_sintetico():
    casos = [
        (["Em", "G"], ["Em", "G"], True),      # ordem exata
        (["G", "Em"], ["Em", "G"], False),     # ordem importa
        (["Em", "X", "G"], ["Em", "G"], False),  # precisa ser contíguo e só usar acordes da sequência
        (["Em", "G", "Em"], ["Em", "G"], True),  # repetição fora do trecho é permitida
        (["em", "g"], ["Em", "G"], True),      # normalização para minúsculas
        (["C/E", "G"], ["C", "G"], False),     # C/E não é C
    ]
    print("TESTE 1 — casos sintéticos da regra")
    for cifra, sequencia, esperado in casos:
        obtido = generator_match(cifra, sequencia)
        print("  cifra=%-24s seq=%-12s esperado=%-5s obtido=%s" % (
            cifra, sequencia, esperado, obtido))
        assert obtido is esperado
    print()


def teste_csv(rows):
    print("TESTE 2 — regra calculada x tag SEQ_FAMOSA no CSV real")
    print("  linhas após descarte da 1ª:", len(rows))
    for id_seq, key in enumerate(QUERY_TO_KEY):
        sequencia = SEQ_CHORDS[key]
        calculados = ids_calculados(rows, sequencia)
        tags = ids_tag(rows, id_seq)
        print("  id=%d seq=%-8s tag=%4d calculado=%4d iguais=%s" % (
            id_seq, key, len(tags), len(calculados), calculados == tags))
        assert calculados == tags
    print()


def teste_alternativas(rows):
    print("TESTE 3 — definições alternativas NÃO reproduzem as tags")
    for nome, funcao in definicoes_alternativas().items():
        partes = []
        for id_seq, key in enumerate(QUERY_TO_KEY):
            calculados = {r["id_unico_musica"] for r in rows
                          if funcao(r["cifra"], SEQ_CHORDS[key])}
            tags = ids_tag(rows, id_seq)
            partes.append("%s=%d(FP%d/FN%d)" % (
                key, len(calculados), len(calculados - tags), len(tags - calculados)))
            assert calculados != tags
        print("  %-38s %s" % (nome, " ".join(partes)))
    print()


def esperado_da_tag(id_seq, pagina, generos_key=None):
    import main as app_module

    generos_key = app_module.generos if generos_key is None else generos_key
    sequencia = SEQ_CHORDS[list(SEQ_CHORDS)[id_seq]]
    collection = app_module.apply_filtro(app_module.musicas.values(), generos_key)
    esperados = []
    for musica in collection:
        if generator_match(musica.cifra, sequencia):
            esperados.append({
                'id_unico_musica': musica.id_unico_musica,
                'id_artista': musica.id_artista,
                'id_musica': musica.id_musica,
                'nome_artista': musica.nome_artista,
                'nome_musica': musica.nome_musica,
                'popularidade': musica.popularidade,
                'acordes': musica.acordes,
                'genero': musica.genero,
                'url': musica.url,
            })
    return app_module.get_pagina(esperados, str(pagina))


def teste_endpoint():
    import main as app_module

    client = app_module.app.test_client()

    print("TESTE 4 — GET /similares?sequencia=... via Flask test client")
    for id_seq, key in enumerate(QUERY_TO_KEY):
        for pagina in (1, 2):
            resposta = client.get("/similares?sequencia=%s&pagina=%d" % (key, pagina))
            assert resposta.status_code == 200
            assert resposta.headers["Content-Type"].startswith("text/html")
            dados = json.loads(resposta.data.decode("utf-8"))
            esperado = esperado_da_tag(id_seq, pagina)
            print("  query=%-8s pagina=%d api=%3d tag=%3d igual=%s content-type=%s" % (
                key, pagina, len(dados), len(esperado), dados == esperado,
                resposta.headers["Content-Type"]))
            assert dados == esperado

        com_virgula = ",".join(SEQ_CHORDS[key])
        dados_virgula = json.loads(client.get(
            "/similares?sequencia=" + com_virgula).data.decode("utf-8"))
        dados_sem_virgula = json.loads(client.get(
            "/similares?sequencia=" + key).data.decode("utf-8"))
        print("  query=%-8s forma com vírgulas igual à forma concatenada=%s" % (
            key, dados_virgula == dados_sem_virgula))
        assert dados_virgula == dados_sem_virgula

    desconhecida = json.loads(client.get("/similares?sequencia=XYZ").data.decode("utf-8"))
    print("  sequência desconhecida 'XYZ' ->", desconhecida)
    assert desconhecida == []

    filtrado = json.loads(client.get(
        "/similares?sequencia=BmGDA&generos=MPB").data.decode("utf-8"))
    esperado_mpb = esperado_da_tag(0, 1, ["MPB"])
    print("  filtro generos=MPB -> api=%d tag∩MPB=%d igual=%s" % (
        len(filtrado), len(esperado_mpb), filtrado == esperado_mpb))
    assert filtrado == esperado_mpb
    print()


def teste_catalogo():
    import main as app_module

    cliente = app_module.app.test_client()
    print("TESTE 5 — catálogo SQLite, validação e persistência")

    catalogo = json.loads(cliente.get("/sequencias").data.decode("utf-8"))
    print("  GET /sequencias -> %d itens, ids=%s" % (
        len(catalogo), [item["id"] for item in catalogo]))
    assert len(catalogo) == 6
    assert [item["id"] for item in catalogo] == [0, 1, 2, 3, 4, 5]
    assert catalogo[0] == {
        "id": 0, "acordes": ["Bm", "G", "D", "A"], "chave": "BmGDA"}

    duplicata = cliente.post(
        "/sequencias",
        data=json.dumps({"acordes": ["Bm", "G", "D", "A"]}),
        content_type="application/json")
    print("  POST duplicata ->", duplicata.status_code)
    assert duplicata.status_code == 409

    invalida = cliente.post(
        "/sequencias",
        data=json.dumps({"acordes": ["G;", "Em"]}),
        content_type="application/json")
    print("  POST inválida ->", invalida.status_code)
    assert invalida.status_code == 400

    criada = cliente.post(
        "/sequencias",
        data=json.dumps({"acordes": ["G", "Em"]}),
        content_type="application/json")
    novo = json.loads(criada.data.decode("utf-8"))
    print("  POST nova -> status=%d item=%s" % (criada.status_code, novo))
    assert criada.status_code == 201
    assert novo["id"] == 6
    assert novo["acordes"] == ["G", "Em"]

    encontrados = json.loads(cliente.get(
        "/similares?sequencia=G,Em").data.decode("utf-8"))
    collection = app_module.apply_filtro(app_module.musicas.values(), app_module.generos)
    referencia = [{
        'id_unico_musica': musica.id_unico_musica,
        'id_artista': musica.id_artista,
        'id_musica': musica.id_musica,
        'nome_artista': musica.nome_artista,
        'nome_musica': musica.nome_musica,
        'popularidade': musica.popularidade,
        'acordes': musica.acordes,
        'genero': musica.genero,
        'url': musica.url,
    } for musica in collection if generator_match(musica.cifra, ["G", "Em"])]
    print("  busca pela sequência nova -> api=%d referência=%d" % (
        len(encontrados), len(referencia)))
    assert encontrados == referencia

    for key, sequencia in SEQ_CHORDS.items():
        for musica in app_module.musicas.values():
            assert app_module.e_compativel(musica.cifra, sequencia) == \
                app_module.e_compativel_musica(musica, sequencia)
    print("  e_compativel x e_compativel_musica: equivalentes nas 6 sequências")

    caminho_original = os.environ["SEQUENCES_DB_PATH"]
    outro_dir = tempfile.mkdtemp(prefix="ciframe-sequences-restart-")
    os.environ["SEQUENCES_DB_PATH"] = os.path.join(outro_dir, "sequences.sqlite3")
    app_module.inicializar_catalogo()
    print("  catálogo em DB novo (seed):", len(app_module.listar_sequencias()))
    assert len(app_module.listar_sequencias()) == 6
    os.environ["SEQUENCES_DB_PATH"] = caminho_original
    print("  catálogo no DB original após 'restart':",
          len(app_module.listar_sequencias()))
    assert len(app_module.listar_sequencias()) == 7
    print()


def benchmark():
    import main as app_module

    musicas = list(app_module.musicas.values())
    print("BENCHMARK — matching em tempo de consulta")
    print("  músicas carregadas:", len(musicas))
    casos = [(key, SEQ_CHORDS[key]) for key in QUERY_TO_KEY]
    casos.append(("NOVA", ["G", "Em"]))
    resultados = []

    for key, sequencia in casos:
        app_module.e_compativel_musica(musicas[0], sequencia)  # aquecimento
        tempos = []
        encontrados = 0
        for _ in range(5):
            inicio = perf_counter()
            encontrados = sum(
                1 for musica in musicas
                if app_module.e_compativel_musica(musica, sequencia)
            )
            tempos.append(perf_counter() - inicio)
        mediana = statistics.median(tempos)
        p95 = sorted(tempos)[int(0.95 * (len(tempos) - 1))]
        resultados.append((mediana, p95))
        print("  seq=%-8s encontrados=%4d mediana=%7.1f ms p95=%7.1f ms" % (
            key, encontrados, mediana * 1000, p95 * 1000))

    pior_mediana = max(item[0] for item in resultados)
    pior_p95 = max(item[1] for item in resultados)
    aceitavel = pior_mediana <= 0.5 and pior_p95 <= 1.0
    print("  aceite (mediana<=500ms, p95<=1000ms):", aceitavel)

    cliente = app_module.app.test_client()
    resposta = cliente.get("/similares?sequencia=Bm,G,D,A&pagina=1")
    print("  endpoint /similares: status=%d itens=%d" % (
        resposta.status_code, len(json.loads(resposta.data.decode("utf-8")))))
    assert resposta.status_code == 200
    assert aceitavel


if __name__ == "__main__":
    if "--benchmark" in sys.argv:
        benchmark()
    else:
        linhas = load_rows()
        teste_sintetico()
        teste_csv(linhas)
        teste_alternativas(linhas)
        teste_endpoint()
        teste_catalogo()
        print("TODOS OS TESTES PASSARAM")
