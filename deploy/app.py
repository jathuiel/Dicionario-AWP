"""Dicionário Visual AWP — backend FastAPI.

M0: serve o site estático atual (intocado).
M1: cadastro de IWP em SQLite (POST/GET /api/iwp).
M2: upload de imagens.
M4: importação xlsx — cadastro em massa com relatório linha a linha
(colunas: codigo obrigatória, descricao opcional).
M5: escalabilidade — squads e disciplinas cadastráveis, descrição editável.
M6: imagens servidas como arquivos WebP em imagens/{squad}/ (substitui os
parquets base64 do M0/M2 — ver migrar_para_webp.py para a migração única).
Os leitores (classificacao.html etc.) passam a depender do backend rodando
(GET /api/pacotes/{squad} e /api/disciplinas) — deixaram de ser 100% estáticos.
M7: hierarquia normalizada projeto→squad/cwa→cwp→iwp (PKs inteiras, FKs
pai→filho) com CRUD completo por entidade. Banco v1 (tabela iwp com código
como PK) é migrado automaticamente no startup — ver _preparar_banco().

Rodar: python -m uvicorn app:app --port 8000
"""
import json
import shutil
import sqlite3
import threading
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import Response

ROOT = Path(__file__).resolve().parent
DB = ROOT / "awp.db"
IMAGENS = ROOT / "imagens"
IMAGENS.mkdir(exist_ok=True)
SQUADS_JSON = ROOT / "squads.json"

MAX_UPLOAD = 10 * 1024 * 1024  # 10 MB por imagem
QUALIDADE_WEBP = 80

# Assinaturas de arquivo aceitas (validação por conteúdo, não por extensão).
MAGIC = [b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n"]  # JPEG, PNG

# Caracteres proibidos em nomes de arquivo no Windows.
CHARS_PROIBIDOS = set('<>:"/\\|?*')

app = FastAPI(title="Dicionário Visual AWP")


# ---------------------------------------------------------------------------
# Banco — SQLite na pasta do projeto (decisão do usuário; risco OneDrive aceito).
# ponytail: journal padrão (sem WAL) para não espalhar -wal/-shm sob sync do
# OneDrive; com poucos usuários basta. Migrar para WAL se houver contenção.
# ---------------------------------------------------------------------------
def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _get_or_create(con: sqlite3.Connection, tabela: str, chave: dict, extra: dict | None = None) -> int:
    """SELECT id de `tabela` pelos campos de `chave`; INSERT (chave + extra)
    se não existir. Usado nos get-or-create da cadeia projeto→cwa→cwp."""
    onde = " AND ".join(f"{c} = ?" for c in chave)
    row = con.execute(f"SELECT id FROM {tabela} WHERE {onde}", tuple(chave.values())).fetchone()
    if row:
        return row["id"]
    campos = {**chave, **(extra or {})}
    cols = ", ".join(campos)
    marcas = ", ".join("?" for _ in campos)
    return con.execute(f"INSERT INTO {tabela} ({cols}) VALUES ({marcas})", tuple(campos.values())).lastrowid


def _atualizar(con: sqlite3.Connection, tabela: str, coluna_chave: str, valor_chave, dados: dict) -> int:
    """UPDATE genérico de `tabela` por uma coluna-chave; devolve rowcount.
    Usado pelos PATCH de entidades com poucos campos opcionais (dados já vem
    filtrado via Pydantic .model_dump(exclude_unset=True) por quem chama)."""
    campos = ", ".join(f"{c} = ?" for c in dados)
    cur = con.execute(f"UPDATE {tabela} SET {campos} WHERE {coluna_chave} = ?",
                       (*dados.values(), valor_chave))
    return cur.rowcount


def parse_codigo(codigo: str) -> dict | None:
    """Valida e decompõe o código no MESMO contrato do leitor (classificacao.html):
    ≥ 9 segmentos separados por '-'; projeto=seg[0]-seg[1], cwa=seg[2],
    disc=seg[3], cwp=seg[5]-seg[6], iwp=seg[7]-seg[8] (seg[4] é embutido só
    no código completo, sem coluna própria). Devolve None se inválido."""
    if " - " in codigo:  # ' - ' separa a vista nos parquets; não pertence ao código
        return None
    pts = codigo.split("-")
    if len(pts) < 9 or not all(p.strip() for p in pts):
        return None
    return {
        "projeto": f"{pts[0]}-{pts[1]}",
        "cwa": pts[2],
        "disc": pts[3],
        "cwp": f"{pts[5]}-{pts[6]}",
        "iwp": f"{pts[7]}-{pts[8]}",
    }


def _criar_schema(con: sqlite3.Connection) -> None:
    """DDL do schema v2 — hierarquia normalizada projeto→squad/cwa→cwp→iwp."""
    con.executescript("""
        CREATE TABLE IF NOT EXISTS projeto (
            id     INTEGER PRIMARY KEY,
            codigo TEXT NOT NULL UNIQUE,
            nome   TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS squad (
            id         INTEGER PRIMARY KEY,
            projeto_id INTEGER NOT NULL REFERENCES projeto(id) ON DELETE RESTRICT,
            pasta      TEXT NOT NULL UNIQUE,
            nome       TEXT NOT NULL,
            icone      TEXT NOT NULL DEFAULT '📦'
        );
        CREATE TABLE IF NOT EXISTS disciplina (
            id     INTEGER PRIMARY KEY,
            codigo TEXT NOT NULL UNIQUE,
            nome   TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS status (
            id    INTEGER PRIMARY KEY,
            nome  TEXT NOT NULL UNIQUE,
            ordem INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS cwa (
            id         INTEGER PRIMARY KEY,
            projeto_id INTEGER NOT NULL REFERENCES projeto(id) ON DELETE RESTRICT,
            squad_id   INTEGER REFERENCES squad(id) ON DELETE SET NULL,
            codigo     TEXT NOT NULL,
            descricao  TEXT NOT NULL DEFAULT '',
            UNIQUE (projeto_id, codigo)
        );
        CREATE TABLE IF NOT EXISTS cwp (
            id            INTEGER PRIMARY KEY,
            cwa_id        INTEGER NOT NULL REFERENCES cwa(id) ON DELETE RESTRICT,
            disciplina_id INTEGER NOT NULL REFERENCES disciplina(id) ON DELETE RESTRICT,
            codigo        TEXT NOT NULL,
            descricao     TEXT NOT NULL DEFAULT '',
            UNIQUE (cwa_id, disciplina_id, codigo)
        );
        CREATE TABLE IF NOT EXISTS iwp (
            id            INTEGER PRIMARY KEY,
            cwp_id        INTEGER NOT NULL REFERENCES cwp(id) ON DELETE RESTRICT,
            codigo        TEXT NOT NULL UNIQUE,
            rotulo        TEXT NOT NULL,
            descricao     TEXT NOT NULL DEFAULT '',
            status_id     INTEGER REFERENCES status(id) ON DELETE SET NULL,
            criado_em     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            atualizado_em TEXT
        );
    """)


def _seed_disciplinas_padrao(con: sqlite3.Connection) -> None:
    con.executemany(
        "INSERT OR IGNORE INTO disciplina (codigo, nome) VALUES (?,?)",
        [("S", "Estruturas Metálicas"), ("E", "Elétrica"), ("M", "Mecânica"),
         ("T", "Tubulação"), ("A", "Arquitetura")])


def _seed_status_padrao(con: sqlite3.Connection) -> None:
    con.executemany(
        "INSERT OR IGNORE INTO status (nome, ordem) VALUES (?,?)",
        [("Planejado", 1), ("Emitido", 2), ("Em execução", 3), ("Concluído", 4)])


def _importar_squads_json(con: sqlite3.Connection) -> None:
    """Cria o projeto KS-N103101 e um squad por entrada de squads.json, se o
    arquivo existir — só roda em banco novo ou recém-migrado (v1 nunca teve
    projeto/squad em tabela; a partir daqui squads.json não é mais lido)."""
    if not SQUADS_JSON.is_file():
        return
    squads = json.loads(SQUADS_JSON.read_text(encoding="utf-8"))
    if not squads:
        return
    projeto_id = _get_or_create(con, "projeto", {"codigo": "KS-N103101"}, {"nome": "Usina S11D"})
    for s in squads:
        con.execute(
            "INSERT OR IGNORE INTO squad (projeto_id, pasta, nome, icone) VALUES (?,?,?,?)",
            (projeto_id, s["pasta"], s["nome"], s.get("icone") or "📦"))


def cadeia_ids(con: sqlite3.Connection, campos: dict) -> tuple[int, int]:
    """Get-or-create projeto→cwa→disciplina→cwp a partir dos campos de
    parse_codigo(); devolve (cwp_id, disciplina_id). Usada por criar_iwp,
    importar_xlsx e pela migração v1→v2 — mesma lógica nos três lugares.
    Disciplina sem cadastro prévio usa o próprio código como nome (não
    deveria ocorrer com os seeds padrão, mas não trava o cadastro)."""
    projeto_id = _get_or_create(con, "projeto", {"codigo": campos["projeto"]}, {"nome": ""})
    cwa_id = _get_or_create(con, "cwa", {"projeto_id": projeto_id, "codigo": campos["cwa"]})
    disc_id = _get_or_create(con, "disciplina", {"codigo": campos["disc"]}, {"nome": campos["disc"]})
    cwp_id = _get_or_create(con, "cwp", {"cwa_id": cwa_id, "disciplina_id": disc_id, "codigo": campos["cwp"]})
    return cwp_id, disc_id


def _migrar_v1_para_v2(con: sqlite3.Connection) -> None:
    """v1→v2: renomeia iwp/disciplina antigas para *_v1 (mantidas como
    registro, não dropadas), cria o schema novo, importa disciplina_v1,
    squads.json e reconstrói a cadeia projeto→cwa→disciplina→cwp de cada
    iwp_v1 via cadeia_ids — mesma lógica usada pelo cadastro em produção."""
    con.execute("ALTER TABLE iwp RENAME TO iwp_v1")
    con.execute("ALTER TABLE disciplina RENAME TO disciplina_v1")
    _criar_schema(con)
    for r in con.execute("SELECT codigo, nome FROM disciplina_v1"):
        con.execute("INSERT OR IGNORE INTO disciplina (codigo, nome) VALUES (?,?)",
                    (r["codigo"], r["nome"]))
    _seed_disciplinas_padrao(con)  # completa S/E/M/T/A se faltar alguma no v1
    _seed_status_padrao(con)
    _importar_squads_json(con)
    for r in con.execute("SELECT * FROM iwp_v1"):
        campos = parse_codigo(r["id"])
        if campos is None:
            continue  # dado antigo fora do formato — não bloqueia a migração
        cwp_id, _ = cadeia_ids(con, campos)
        con.execute(
            "INSERT INTO iwp (cwp_id, codigo, rotulo, descricao, criado_em) VALUES (?,?,?,?,?)",
            (cwp_id, r["id"], campos["iwp"], r["descricao"], r["criado_em"]))


def _preparar_banco() -> None:
    """Cria o schema (banco novo) ou migra de v1 (tabela iwp sem cwp_id) para
    v2. Idempotente — banco já v2 não sofre nenhuma alteração. A cópia de
    segurança (awp.db.bak-v1) é a salvaguarda real da migração; o restante
    roda numa única conexão/transação."""
    with db() as con:
        colunas = {r["name"] for r in con.execute("PRAGMA table_info(iwp)")}

    if not colunas:  # banco novo, sem tabela iwp
        with db() as con:
            _criar_schema(con)
            _seed_disciplinas_padrao(con)
            _seed_status_padrao(con)
            _importar_squads_json(con)
        return

    if "cwp_id" in colunas:  # já é v2
        return

    bak = DB.with_name(DB.name + ".bak-v1")
    if not bak.is_file():
        shutil.copyfile(DB, bak)
    with db() as con:
        _migrar_v1_para_v2(con)


_preparar_banco()


@app.get("/api/pacotes/{squad}")
def listar_pacotes(squad: str):
    """Lista os pacotes do squad no formato consumido pelo leitor: agrupa os
    arquivos de imagens/{squad}/*.webp por código, com a URL de cada vista."""
    pasta = dir_squad(squad)
    if not pasta.is_dir():
        return []

    with db() as con:
        descricoes = {r["codigo"]: r["descricao"] for r in
                      con.execute("SELECT codigo, descricao FROM iwp WHERE descricao != ''")}

    mapa: dict[str, dict] = {}
    for arq in sorted(pasta.glob("*.webp")):
        sep = arq.stem.rfind(" - ")
        if sep == -1:
            continue
        codigo, vista = arq.stem[:sep], arq.stem[sep + 3:]
        campos = parse_codigo(codigo)
        if campos is None:
            continue
        pac = mapa.setdefault(codigo, {
            "id": codigo, "area": campos["cwa"], "cwp": campos["cwp"],
            "iwp": campos["iwp"], "disc": campos["disc"],
            "descricao": descricoes.get(codigo, ""), "views": {},
        })
        # Relativo (não "/imagens/...") — funciona tanto na raiz do domínio
        # quanto num subcaminho (ex.: /dicionario-awp/), sem depender de
        # configuração de root_path no servidor. É consumido de
        # {squad}/{squad}.html, um nível abaixo da raiz do app.
        pac["views"][vista] = f"../imagens/{squad}/{quote(arq.name)}"

    return list(mapa.values())


class NovoIwp(BaseModel):
    codigo: str
    descricao: str = ""


@app.post("/api/iwp", status_code=201)
def criar_iwp(novo: NovoIwp):
    codigo = novo.codigo.strip()
    campos = parse_codigo(codigo)
    if campos is None:
        raise HTTPException(
            status_code=422,
            detail="Código inválido. Formato esperado: "
                   "KS-N103101-{CWA}-{DISC}-MT-CWP-{nnn}-IWP-{nnn}",
        )
    try:
        with db() as con:
            cwp_id, _ = cadeia_ids(con, campos)
            con.execute(
                "INSERT INTO iwp (cwp_id, codigo, rotulo, descricao) VALUES (?,?,?,?)",
                (cwp_id, codigo, campos["iwp"], novo.descricao.strip()),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"IWP '{codigo}' já cadastrado")
    return {"codigo": codigo, "cwa": campos["cwa"], "disc": campos["disc"],
            "cwp": campos["cwp"], "iwp": campos["iwp"], "descricao": novo.descricao.strip()}


class EditaIwp(BaseModel):
    descricao: str | None = None
    status_id: int | None = None


@app.patch("/api/iwp/{codigo}")
def editar_iwp(codigo: str, edicao: EditaIwp):
    """Inclui/edita descrição e/ou status de um IWP já cadastrado — campos
    independentes; qualquer um presente no corpo já basta. Marca atualizado_em."""
    dados = edicao.model_dump(exclude_unset=True)
    if not dados:
        raise HTTPException(status_code=422, detail="Informe descricao e/ou status_id")
    if "descricao" in dados:
        dados["descricao"] = (dados["descricao"] or "").strip()
    campos_sql = ", ".join(f"{c} = ?" for c in dados)
    try:
        with db() as con:
            cur = con.execute(
                f"UPDATE iwp SET {campos_sql}, atualizado_em = datetime('now','localtime') WHERE codigo = ?",
                (*dados.values(), codigo))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="status_id inválido")
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"IWP '{codigo}' não cadastrado")
    return {"codigo": codigo, **dados}


@app.delete("/api/iwp/{codigo}")
def excluir_iwp(codigo: str):
    """Remove o cadastro do IWP. As imagens em imagens/{squad}/ NÃO são
    apagadas — ficam órfãs no disco (comportamento deliberado)."""
    with db() as con:
        cur = con.execute("DELETE FROM iwp WHERE codigo = ?", (codigo,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"IWP '{codigo}' não cadastrado")
    return {"codigo": codigo, "excluido": True}


# SELECT reutilizado por listar_iwp — junta os códigos da cadeia via FK para
# manter o mesmo formato de resposta de quando cwa/disc/cwp eram colunas
# diretas da tabela iwp.
_SELECT_IWP = """
    SELECT iwp.codigo AS codigo, cwa.codigo AS cwa, disciplina.codigo AS disc,
           cwp.codigo AS cwp, iwp.rotulo AS iwp, iwp.descricao AS descricao,
           iwp.criado_em AS criado_em, status.nome AS status
    FROM iwp
    JOIN cwp ON cwp.id = iwp.cwp_id
    JOIN cwa ON cwa.id = cwp.cwa_id
    JOIN disciplina ON disciplina.id = cwp.disciplina_id
    LEFT JOIN status ON status.id = iwp.status_id
"""


@app.get("/api/iwp")
def listar_iwp(cwa: str = "", cwp: str = "", disc: str = "", busca: str = ""):
    """Lista os IWPs cadastrados; parâmetros vazios não filtram (M3). Os
    filtros recebem os CÓDIGOS texto (ex.: cwa=294, disc=S), não os ids
    internos — mesmo contrato de antes da normalização."""
    sql, args = _SELECT_IWP + " WHERE 1=1", []
    if cwa:
        sql += " AND cwa.codigo = ?"; args.append(cwa)
    if cwp:
        sql += " AND cwp.codigo = ?"; args.append(cwp)
    if disc:
        sql += " AND disciplina.codigo = ?"; args.append(disc)
    if busca:
        sql += " AND (iwp.codigo LIKE ? OR iwp.descricao LIKE ?)"; args += [f"%{busca}%"] * 2
    with db() as con:
        rows = con.execute(sql + " ORDER BY iwp.codigo", args).fetchall()
    return [dict(r) for r in rows]


_FILTROS_SQL = {
    "cwa": """SELECT DISTINCT cwa.codigo FROM iwp JOIN cwp ON cwp.id = iwp.cwp_id
              JOIN cwa ON cwa.id = cwp.cwa_id ORDER BY 1""",
    "cwp": """SELECT DISTINCT cwp.codigo FROM iwp JOIN cwp ON cwp.id = iwp.cwp_id ORDER BY 1""",
    "disc": """SELECT DISTINCT disciplina.codigo FROM iwp JOIN cwp ON cwp.id = iwp.cwp_id
               JOIN disciplina ON disciplina.id = cwp.disciplina_id ORDER BY 1""",
}


@app.get("/api/iwp/filtros")
def filtros_iwp():
    """Valores distintos (só os que têm ao menos um IWP) para preencher os
    selects de filtro da consulta."""
    with db() as con:
        return {campo: [r[0] for r in con.execute(sql)] for campo, sql in _FILTROS_SQL.items()}


# ---------------------------------------------------------------------------
# Disciplinas — cadastráveis; visualizadores leem via GET /api/disciplinas
# ---------------------------------------------------------------------------

class Disciplina(BaseModel):
    codigo: str
    nome: str


@app.get("/api/disciplinas")
def listar_disciplinas():
    with db() as con:
        return [dict(r) for r in
                con.execute("SELECT id, codigo, nome FROM disciplina ORDER BY codigo")]


@app.post("/api/disciplinas", status_code=201)
def salvar_disciplina(d: Disciplina):
    """Cria ou atualiza (mesmo código = edição) preservando o id — UPDATE em
    vez de INSERT OR REPLACE, senão o REPLACE apagaria e recriaria a linha e
    quebraria a FK de cwp.disciplina_id quando a disciplina já está em uso."""
    codigo, nome = d.codigo.strip().upper(), d.nome.strip()
    if not codigo or not codigo.isalnum() or len(codigo) > 5:
        raise HTTPException(status_code=422, detail="Código: 1 a 5 letras/números")
    if not nome:
        raise HTTPException(status_code=422, detail="Nome é obrigatório")
    with db() as con:
        linhas = _atualizar(con, "disciplina", "codigo", codigo, {"nome": nome})
        if linhas == 0:
            con.execute("INSERT INTO disciplina (codigo, nome) VALUES (?,?)", (codigo, nome))
    return {"codigo": codigo, "nome": nome}


class EditaDisciplina(BaseModel):
    nome: str


@app.patch("/api/disciplinas/{codigo}")
def editar_disciplina(codigo: str, edicao: EditaDisciplina):
    nome = edicao.nome.strip()
    if not nome:
        raise HTTPException(status_code=422, detail="Nome é obrigatório")
    with db() as con:
        linhas = _atualizar(con, "disciplina", "codigo", codigo.strip().upper(), {"nome": nome})
    if linhas == 0:
        raise HTTPException(status_code=404, detail=f"Disciplina '{codigo}' não existe")
    return {"codigo": codigo.strip().upper(), "nome": nome}


@app.delete("/api/disciplinas/{codigo}")
def excluir_disciplina(codigo: str):
    try:
        with db() as con:
            cur = con.execute("DELETE FROM disciplina WHERE codigo = ?", (codigo,))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Disciplina '{codigo}' possui CWP(s) vinculado(s)")
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Disciplina '{codigo}' não existe")
    return {"codigo": codigo, "excluida": True}


# ---------------------------------------------------------------------------
# Projetos
# ---------------------------------------------------------------------------

class NovoProjeto(BaseModel):
    codigo: str
    nome: str = ""


@app.get("/api/projetos")
def listar_projetos():
    with db() as con:
        return [dict(r) for r in con.execute("SELECT id, codigo, nome FROM projeto ORDER BY codigo")]


@app.post("/api/projetos", status_code=201)
def criar_projeto(novo: NovoProjeto):
    codigo = novo.codigo.strip()
    if not codigo:
        raise HTTPException(status_code=422, detail="Código é obrigatório")
    try:
        with db() as con:
            pid = con.execute("INSERT INTO projeto (codigo, nome) VALUES (?,?)",
                               (codigo, novo.nome.strip())).lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Projeto '{codigo}' já cadastrado")
    return {"id": pid, "codigo": codigo, "nome": novo.nome.strip()}


class EditaProjeto(BaseModel):
    nome: str


@app.patch("/api/projetos/{projeto_id}")
def editar_projeto(projeto_id: int, edicao: EditaProjeto):
    with db() as con:
        linhas = _atualizar(con, "projeto", "id", projeto_id, {"nome": edicao.nome.strip()})
    if linhas == 0:
        raise HTTPException(status_code=404, detail=f"Projeto {projeto_id} não encontrado")
    return {"id": projeto_id, "nome": edicao.nome.strip()}


@app.delete("/api/projetos/{projeto_id}")
def excluir_projeto(projeto_id: int):
    try:
        with db() as con:
            cur = con.execute("DELETE FROM projeto WHERE id = ?", (projeto_id,))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Projeto {projeto_id} possui squad(s)/CWA(s) vinculado(s)")
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Projeto {projeto_id} não encontrado")
    return {"id": projeto_id, "excluido": True}


# ---------------------------------------------------------------------------
# CWAs
# ---------------------------------------------------------------------------

class NovoCwa(BaseModel):
    projeto_id: int
    codigo: str
    descricao: str = ""


@app.get("/api/cwas")
def listar_cwas(projeto_id: int | None = None, squad_id: int | None = None):
    sql, args = "SELECT * FROM cwa WHERE 1=1", []
    if projeto_id is not None:
        sql += " AND projeto_id = ?"; args.append(projeto_id)
    if squad_id is not None:
        sql += " AND squad_id = ?"; args.append(squad_id)
    with db() as con:
        rows = con.execute(sql + " ORDER BY codigo", args).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/cwas", status_code=201)
def criar_cwa(novo: NovoCwa):
    try:
        with db() as con:
            cid = con.execute(
                "INSERT INTO cwa (projeto_id, codigo, descricao) VALUES (?,?,?)",
                (novo.projeto_id, novo.codigo.strip(), novo.descricao.strip())).lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="CWA já existe nesse projeto, ou projeto_id inválido")
    return {"id": cid, "projeto_id": novo.projeto_id, "codigo": novo.codigo.strip(),
            "descricao": novo.descricao.strip()}


class EditaCwa(BaseModel):
    descricao: str | None = None
    squad_id: int | None = None


@app.patch("/api/cwas/{cwa_id}")
def editar_cwa(cwa_id: int, edicao: EditaCwa):
    dados = edicao.model_dump(exclude_unset=True)
    if not dados:
        raise HTTPException(status_code=422, detail="Nada para atualizar")
    if "descricao" in dados:
        dados["descricao"] = (dados["descricao"] or "").strip()
    try:
        with db() as con:
            linhas = _atualizar(con, "cwa", "id", cwa_id, dados)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="squad_id inválido")
    if linhas == 0:
        raise HTTPException(status_code=404, detail=f"CWA {cwa_id} não encontrada")
    return {"id": cwa_id, **dados}


@app.delete("/api/cwas/{cwa_id}")
def excluir_cwa(cwa_id: int):
    try:
        with db() as con:
            cur = con.execute("DELETE FROM cwa WHERE id = ?", (cwa_id,))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"CWA {cwa_id} possui CWP(s) vinculado(s)")
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"CWA {cwa_id} não encontrada")
    return {"id": cwa_id, "excluido": True}


# ---------------------------------------------------------------------------
# CWPs — nascem do cadastro de IWP (get-or-create); aqui só consulta/edição/exclusão
# ---------------------------------------------------------------------------

@app.get("/api/cwps")
def listar_cwps(cwa_id: int | None = None):
    sql, args = "SELECT * FROM cwp WHERE 1=1", []
    if cwa_id is not None:
        sql += " AND cwa_id = ?"; args.append(cwa_id)
    with db() as con:
        rows = con.execute(sql + " ORDER BY codigo", args).fetchall()
    return [dict(r) for r in rows]


class EditaCwp(BaseModel):
    descricao: str


@app.patch("/api/cwps/{cwp_id}")
def editar_cwp(cwp_id: int, edicao: EditaCwp):
    with db() as con:
        linhas = _atualizar(con, "cwp", "id", cwp_id, {"descricao": edicao.descricao.strip()})
    if linhas == 0:
        raise HTTPException(status_code=404, detail=f"CWP {cwp_id} não encontrado")
    return {"id": cwp_id, "descricao": edicao.descricao.strip()}


@app.delete("/api/cwps/{cwp_id}")
def excluir_cwp(cwp_id: int):
    try:
        with db() as con:
            cur = con.execute("DELETE FROM cwp WHERE id = ?", (cwp_id,))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"CWP {cwp_id} possui IWP(s) vinculado(s)")
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"CWP {cwp_id} não encontrado")
    return {"id": cwp_id, "excluido": True}


# ---------------------------------------------------------------------------
# Status do IWP
# ---------------------------------------------------------------------------

class NovoStatus(BaseModel):
    nome: str
    ordem: int = 0


@app.get("/api/status")
def listar_status():
    with db() as con:
        return [dict(r) for r in con.execute("SELECT * FROM status ORDER BY ordem")]


@app.post("/api/status", status_code=201)
def criar_status(novo: NovoStatus):
    nome = novo.nome.strip()
    if not nome:
        raise HTTPException(status_code=422, detail="Nome é obrigatório")
    try:
        with db() as con:
            sid = con.execute("INSERT INTO status (nome, ordem) VALUES (?,?)",
                               (nome, novo.ordem)).lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Status '{nome}' já existe")
    return {"id": sid, "nome": nome, "ordem": novo.ordem}


class EditaStatus(BaseModel):
    nome: str | None = None
    ordem: int | None = None


@app.patch("/api/status/{status_id}")
def editar_status(status_id: int, edicao: EditaStatus):
    dados = edicao.model_dump(exclude_unset=True)
    if not dados:
        raise HTTPException(status_code=422, detail="Nada para atualizar")
    if "nome" in dados:
        dados["nome"] = (dados["nome"] or "").strip()
    try:
        with db() as con:
            linhas = _atualizar(con, "status", "id", status_id, dados)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Nome de status já existe")
    if linhas == 0:
        raise HTTPException(status_code=404, detail=f"Status {status_id} não encontrado")
    return {"id": status_id, **dados}


@app.delete("/api/status/{status_id}")
def excluir_status(status_id: int):
    """iwp.status_id vira NULL via ON DELETE SET NULL — não há 409 aqui."""
    with db() as con:
        cur = con.execute("DELETE FROM status WHERE id = ?", (status_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Status {status_id} não encontrado")
    return {"id": status_id, "excluido": True}


# ---------------------------------------------------------------------------
# Squads — fonte é a tabela squad (squads.json só é lido na migração/criação
# inicial do banco; POST grava pasta+HTML no disco e squad na tabela)
# ---------------------------------------------------------------------------

class NovoSquad(BaseModel):
    nome: str
    icone: str = "📦"
    projeto_id: int | None = None


@app.get("/api/squads")
def listar_squads():
    with db() as con:
        return [dict(r) for r in con.execute("SELECT id, pasta, nome, icone FROM squad ORDER BY pasta")]


@app.post("/api/squads", status_code=201)
def criar_squad(novo: NovoSquad):
    """Cria a pasta do squad com a página do visualizador (cópia de
    classificacao/classificacao.html — o template de leitura) e registra na
    tabela squad. As imagens entram depois via upload."""
    import re
    import unicodedata

    nome = novo.nome.strip()
    slug = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    if not slug:
        raise HTTPException(status_code=422, detail="Nome do squad inválido")

    pasta = ROOT / slug
    if pasta.exists():
        raise HTTPException(status_code=409, detail=f"Squad '{slug}' já existe")

    with db() as con:
        projeto_id = novo.projeto_id
        if projeto_id is None:
            linhas = con.execute("SELECT id FROM projeto").fetchall()
            if len(linhas) != 1:
                raise HTTPException(
                    status_code=422,
                    detail="Informe projeto_id (há mais de um projeto cadastrado, ou nenhum)")
            projeto_id = linhas[0]["id"]

        pasta.mkdir()
        shutil.copyfile(ROOT / "classificacao" / "classificacao.html", pasta / f"{slug}.html")

        icone = novo.icone.strip() or "📦"
        try:
            con.execute("INSERT INTO squad (projeto_id, pasta, nome, icone) VALUES (?,?,?,?)",
                        (projeto_id, slug, nome, icone))
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail=f"Squad '{slug}' já existe, ou projeto_id inválido")

    return {"pasta": slug, "nome": nome, "pagina": f"{slug}/{slug}.html"}


class EditaSquad(BaseModel):
    nome: str | None = None
    icone: str | None = None
    projeto_id: int | None = None


@app.patch("/api/squads/{squad_id}")
def editar_squad(squad_id: int, edicao: EditaSquad):
    dados = edicao.model_dump(exclude_unset=True)
    if not dados:
        raise HTTPException(status_code=422, detail="Nada para atualizar")
    if "nome" in dados:
        dados["nome"] = (dados["nome"] or "").strip()
    if "icone" in dados:
        dados["icone"] = (dados["icone"] or "").strip() or "📦"
    try:
        with db() as con:
            linhas = _atualizar(con, "squad", "id", squad_id, dados)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="projeto_id inválido")
    if linhas == 0:
        raise HTTPException(status_code=404, detail=f"Squad {squad_id} não encontrado")
    return {"id": squad_id, **dados}


@app.delete("/api/squads/{squad_id}")
def excluir_squad(squad_id: int):
    """FK de cwa.squad_id é ON DELETE SET NULL (atribuição manual, não posse)
    — mas a API bloqueia com 409 se houver CWA apontando, forçando reatribuir
    antes de excluir em vez de órfãos silenciosos. Pasta/HTML ficam no disco."""
    with db() as con:
        em_uso = con.execute("SELECT 1 FROM cwa WHERE squad_id = ? LIMIT 1", (squad_id,)).fetchone()
        if em_uso:
            raise HTTPException(status_code=409,
                                 detail=f"Squad {squad_id} possui CWA(s) vinculada(s); reatribua antes de excluir")
        cur = con.execute("DELETE FROM squad WHERE id = ?", (squad_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Squad {squad_id} não encontrado")
    return {"id": squad_id, "excluido": True}


# ---------------------------------------------------------------------------
# M2/M6 — Upload de imagens (convertidas e servidas como WebP)
# ---------------------------------------------------------------------------

# ponytail: lock global — uploads simultâneos gravam no mesmo diretório;
# trocar por lock por squad se houver contenção real.
_upload_lock = threading.Lock()


def dir_squad(squad: str) -> Path:
    """Valida o squad (precisa estar cadastrado na tabela squad) e devolve
    seu diretório de imagens (imagens/{squad}/)."""
    with db() as con:
        existe = con.execute("SELECT 1 FROM squad WHERE pasta = ?", (squad,)).fetchone()
    if not existe:
        raise HTTPException(status_code=404, detail=f"Squad '{squad}' não encontrado")
    return IMAGENS / squad


def registro_uploads(squad: str) -> Path:
    """Arquivo que guarda quais imagens de imagens/{squad}/ vieram de upload
    (para diferenciar, na página de upload, do restante migrado da base)."""
    return IMAGENS / squad / ".uploads.json"


def registrar_upload(squad: str, nome_arquivo: str) -> None:
    reg = registro_uploads(squad)
    nomes = json.loads(reg.read_text(encoding="utf-8")) if reg.is_file() else []
    if nome_arquivo not in nomes:
        nomes.append(nome_arquivo)
    reg.write_text(json.dumps(nomes, ensure_ascii=False), encoding="utf-8")


@app.post("/api/upload", status_code=201)
def enviar_imagem(
    squad: str = Form(),
    codigo: str = Form(),
    vista: str = Form(),
    arquivo: UploadFile = File(),
):
    pasta = dir_squad(squad)
    codigo, vista = codigo.strip(), vista.strip()

    if parse_codigo(codigo) is None:
        raise HTTPException(status_code=422, detail="Código inválido. Formato esperado: "
                            "KS-N103101-{CWA}-{DISC}-MT-CWP-{nnn}-IWP-{nnn}")
    if not vista or " - " in vista:
        # ' - ' é o separador código/vista no nome do arquivo
        raise HTTPException(status_code=422, detail="Nome da vista é obrigatório e não pode conter ' - '")
    if CHARS_PROIBIDOS & set(codigo + vista):
        raise HTTPException(status_code=422, detail='Código/vista não podem conter < > : " / \\ | ? *')

    conteudo = arquivo.file.read(MAX_UPLOAD + 1)
    if len(conteudo) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Imagem acima de 10 MB")
    if not any(conteudo.startswith(magia) for magia in MAGIC):
        raise HTTPException(status_code=415, detail="Arquivo não é JPEG nem PNG")

    import io
    from PIL import Image
    try:
        webp = io.BytesIO()
        Image.open(io.BytesIO(conteudo)).save(webp, "WEBP", quality=QUALIDADE_WEBP)
    except Exception:
        raise HTTPException(status_code=415, detail="Não foi possível processar a imagem")

    iwp_completo = f"{codigo} - {vista}"
    with _upload_lock:
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"{iwp_completo}.webp"
        substituida = destino.is_file()
        destino.write_bytes(webp.getvalue())
        registrar_upload(squad, destino.name)

    return {"iwp": iwp_completo, "squad": squad, "substituida": substituida,
            "url": f"/imagens/{squad}/{quote(destino.name)}"}


@app.get("/api/upload/{squad}")
def listar_uploads(squad: str):
    """Lista as imagens enviadas via upload (não inclui as migradas da base)."""
    pasta = dir_squad(squad)
    reg = registro_uploads(squad)
    if not reg.is_file():
        return []
    nomes = json.loads(reg.read_text(encoding="utf-8"))
    resultado = []
    for nome in nomes:
        arq = pasta / nome
        if arq.is_file():
            resultado.append({"iwp": arq.stem, "arquivo": arq.name, "bytes": arq.stat().st_size})
    return resultado


# ---------------------------------------------------------------------------
# M4 — Importação xlsx (cadastro em massa)
# ---------------------------------------------------------------------------

@app.post("/api/importar")
def importar_xlsx(arquivo: UploadFile = File()):
    """Importa IWPs de uma planilha: 1ª aba, cabeçalho na linha 1 com a coluna
    'codigo' (obrigatória) e 'descricao' (opcional). Linhas inválidas ou
    duplicadas não abortam o lote — voltam no relatório com o motivo."""
    import io

    import openpyxl

    conteudo = arquivo.file.read(5 * 1024 * 1024 + 1)
    if len(conteudo) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Planilha acima de 5 MB")
    if not conteudo.startswith(b"PK"):  # xlsx é um zip
        raise HTTPException(status_code=415, detail="Arquivo não é .xlsx")

    try:
        aba = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True).worksheets[0]
    except Exception:
        raise HTTPException(status_code=415, detail="Não foi possível ler a planilha")

    linhas = aba.iter_rows(values_only=True)
    cabecalho = [str(c).strip().lower() if c else "" for c in next(linhas, [])]
    if "codigo" not in cabecalho:
        raise HTTPException(status_code=422, detail="Cabeçalho precisa ter a coluna 'codigo'")
    col_cod = cabecalho.index("codigo")
    col_desc = cabecalho.index("descricao") if "descricao" in cabecalho else None

    importados, duplicados, invalidos = 0, [], []
    with db() as con:
        for n, linha in enumerate(linhas, start=2):
            codigo = str(linha[col_cod] or "").strip() if len(linha) > col_cod else ""
            if not codigo:
                continue  # linha em branco
            descricao = ""
            if col_desc is not None and len(linha) > col_desc and linha[col_desc]:
                descricao = str(linha[col_desc]).strip()

            campos = parse_codigo(codigo)
            if campos is None:
                invalidos.append({"linha": n, "codigo": codigo, "motivo": "formato inválido"})
                continue
            try:
                cwp_id, _ = cadeia_ids(con, campos)
                con.execute(
                    "INSERT INTO iwp (cwp_id, codigo, rotulo, descricao) VALUES (?,?,?,?)",
                    (cwp_id, codigo, campos["iwp"], descricao),
                )
                importados += 1
            except sqlite3.IntegrityError:
                duplicados.append({"linha": n, "codigo": codigo})

    return {"importados": importados, "duplicados": duplicados, "invalidos": invalidos}


# Bloqueia código-fonte e dados internos de serem baixados como estático —
# o mount abaixo serve TUDO em ROOT (é o que permite servir os HTMLs/assets
# sem uma rota por arquivo), então sem isso awp.db e app.py ficam públicos.
_SUFIXOS_BLOQUEADOS = {".py", ".db", ".md", ".pyc"}
_NOMES_BLOQUEADOS = {"requirements.txt", ".gitignore"}
_PASTAS_BLOQUEADAS = {".git", ".claude", "__pycache__"}


@app.middleware("http")
async def bloquear_arquivos_internos(request, call_next):
    p = Path(request.url.path)
    if (p.suffix in _SUFIXOS_BLOQUEADOS or p.name in _NOMES_BLOQUEADOS
            or p.name.startswith(DB.name)  # cobre também awp.db.bak-v1 (backup da migração)
            or _PASTAS_BLOQUEADAS & set(p.parts)):
        return Response(status_code=404)
    return await call_next(request)


# Montado por último: tudo que não é /api/* nem um arquivo bloqueado acima é
# servido como arquivo estático, preservando o site atual sem alteração.
app.mount("/", StaticFiles(directory=ROOT, html=True), name="site")
