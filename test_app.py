"""Checagem mínima do backend — roda com: python test_app.py

Cobre o schema novo (M7): migração v1→v2 preserva contagem e descrições dos
IWPs (banco sintético descartável em pasta temporária — NÃO toca o awp.db
real), o formato de resposta antigo de GET /api/pacotes/{squad} e /api/iwp,
criação de IWP com get-or-create da cadeia completa, bloqueio por FK RESTRICT
(409) e importação xlsx. Os testes que batem na API usam um código de IWP
descartável (prefixo KS-N103101-999...) para não poluir os dados reais.
"""
import io
import shutil
import sqlite3
import tempfile
from pathlib import Path

import openpyxl
from fastapi.testclient import TestClient

import app as appmod
from app import app

CODIGO_TESTE = "KS-N103101-999-S-MT-CWP-999-IWP-999"
COD_IMPORTADO = "KS-N103101-998-S-MT-CWP-998-IWP-001"


def testar_migracao():
    """Banco v1 sintético (schema antigo, mesmo formato do awp.db antes desta
    mudança) → _preparar_banco() → confere que virou v2 sem perder IWPs nem
    descrições. Usa uma pasta temporária; não toca o awp.db do projeto."""
    tmp = Path(tempfile.mkdtemp())
    db_v1 = tmp / "v1.db"
    try:
        con = sqlite3.connect(db_v1)
        con.execute("""CREATE TABLE iwp (id TEXT PRIMARY KEY, cwa TEXT NOT NULL,
            disc TEXT NOT NULL, cwp TEXT NOT NULL, iwp TEXT NOT NULL,
            descricao TEXT NOT NULL DEFAULT '', criado_em TEXT NOT NULL)""")
        con.execute("CREATE TABLE disciplina (codigo TEXT PRIMARY KEY, nome TEXT NOT NULL)")
        con.execute("INSERT INTO disciplina VALUES ('S','Estruturas Metálicas')")
        con.executemany(
            "INSERT INTO iwp VALUES (?,?,?,?,?,?,?)",
            [("KS-N103101-100-S-MT-CWP-001-IWP-001", "100", "S", "CWP-001", "IWP-001",
              "Descrição A", "2026-01-01 10:00:00"),
             ("KS-N103101-100-S-MT-CWP-001-IWP-002", "100", "S", "CWP-001", "IWP-002",
              "", "2026-01-01 10:00:00")])
        con.commit()
        con.close()

        db_original = appmod.DB
        squads_json_original = appmod.SQUADS_JSON
        appmod.DB = db_v1
        appmod.SQUADS_JSON = tmp / "squads-inexistente.json"  # sem squads.json neste teste
        try:
            appmod._preparar_banco()
        finally:
            appmod.DB = db_original
            appmod.SQUADS_JSON = squads_json_original

        con = sqlite3.connect(db_v1)
        con.row_factory = sqlite3.Row
        assert con.execute("SELECT COUNT(*) FROM iwp").fetchone()[0] == 2, \
            "migração perdeu ou duplicou IWPs"
        descricoes = {r["codigo"]: r["descricao"] for r in
                      con.execute("SELECT codigo, descricao FROM iwp")}
        assert descricoes["KS-N103101-100-S-MT-CWP-001-IWP-001"] == "Descrição A"
        assert descricoes["KS-N103101-100-S-MT-CWP-001-IWP-002"] == ""
        assert con.execute("SELECT COUNT(*) FROM iwp_v1").fetchone()[0] == 2, \
            "tabela iwp_v1 deveria ter sido preservada como registro"
        assert (tmp / "v1.db.bak-v1").is_file(), "backup .bak-v1 não foi criado"
        con.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def limpar_dados_teste():
    with appmod.db() as con:
        for codigo in (CODIGO_TESTE, COD_IMPORTADO):
            con.execute("DELETE FROM iwp WHERE codigo = ?", (codigo,))
        con.execute("DELETE FROM cwp WHERE codigo IN ('CWP-999','CWP-998')")
        con.execute("DELETE FROM cwa WHERE codigo IN ('999','998')")


def main():
    testar_migracao()
    print("OK: migração v1->v2 preserva contagem e descrições")

    limpar_dados_teste()
    cliente = TestClient(app)
    try:
        # --- formato antigo de GET /api/pacotes/{squad} e GET /api/iwp ---
        squads = cliente.get("/api/squads").json()
        assert squads, "esperava ao menos um squad cadastrado (squads.json migrado)"
        squad = next((s["pasta"] for s in squads if s["pasta"] == "classificacao"), squads[0]["pasta"])
        pacotes = cliente.get(f"/api/pacotes/{squad}").json()
        if pacotes:
            assert {"id", "area", "cwp", "iwp", "disc", "descricao", "views"} <= pacotes[0].keys()

        iwps = cliente.get("/api/iwp").json()
        if iwps:
            assert {"codigo", "cwa", "disc", "cwp", "iwp", "descricao", "criado_em", "status"} <= iwps[0].keys()
        print("OK: formato de /api/pacotes e /api/iwp preservado")

        # --- POST /api/iwp cria a cadeia projeto->cwa->disciplina->cwp ---
        r = cliente.post("/api/iwp", json={"codigo": CODIGO_TESTE, "descricao": "Teste automatizado"})
        assert r.status_code == 201, r.text
        assert r.json() == {"codigo": CODIGO_TESTE, "cwa": "999", "disc": "S",
                             "cwp": "CWP-999", "iwp": "IWP-999", "descricao": "Teste automatizado"}
        achado = [i for i in cliente.get("/api/iwp", params={"cwa": "999"}).json()
                  if i["codigo"] == CODIGO_TESTE]
        assert achado and achado[0]["descricao"] == "Teste automatizado"

        # duplicado -> 409
        assert cliente.post("/api/iwp", json={"codigo": CODIGO_TESTE}).status_code == 409
        print("OK: POST /api/iwp cria cadeia completa (get-or-create)")

        # --- PATCH aceita status_id além de descricao ---
        status_id = cliente.get("/api/status").json()[0]["id"]
        r = cliente.patch(f"/api/iwp/{CODIGO_TESTE}", json={"status_id": status_id})
        assert r.status_code == 200, r.text
        atualizado = next(i for i in cliente.get("/api/iwp", params={"cwa": "999"}).json()
                           if i["codigo"] == CODIGO_TESTE)
        assert atualizado["status"] is not None
        print("OK: PATCH /api/iwp aceita status_id")

        # --- FK RESTRICT: CWP com IWP vinculado e disciplina em uso não podem ser excluídos ---
        cwp_teste = next(c for c in cliente.get("/api/cwps").json() if c["codigo"] == "CWP-999")
        assert cliente.delete(f"/api/cwps/{cwp_teste['id']}").status_code == 409
        assert cliente.delete("/api/disciplinas/S").status_code == 409
        print("OK: DELETE bloqueado por FK RESTRICT (409)")

        # --- DELETE /api/iwp funciona e a cadeia órfã fica livre para excluir ---
        r = cliente.delete(f"/api/iwp/{CODIGO_TESTE}")
        assert r.status_code == 200 and r.json()["excluido"] is True
        assert cliente.delete(f"/api/iwp/{CODIGO_TESTE}").status_code == 404
        assert cliente.delete(f"/api/cwps/{cwp_teste['id']}").status_code == 200
        print("OK: DELETE /api/iwp remove o cadastro")

        # --- importação xlsx: válido + inválido, mesmo contrato de resposta ---
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["codigo", "descricao"])
        ws.append([COD_IMPORTADO, "Importado via teste"])
        ws.append(["codigo-invalido", ""])
        buf = io.BytesIO()
        wb.save(buf)
        r = cliente.post("/api/importar", files={"arquivo": (
            "t.xlsx", io.BytesIO(buf.getvalue()),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert r.status_code == 200, r.text
        rel = r.json()
        assert rel["importados"] == 1 and len(rel["invalidos"]) == 1, rel
        assert any(i["codigo"] == COD_IMPORTADO for i in
                   cliente.get("/api/iwp", params={"busca": "Importado via teste"}).json())
        print("OK: /api/importar cria IWP via get-or-create")

        print("TODOS OS TESTES PASSARAM")
    finally:
        limpar_dados_teste()


if __name__ == "__main__":
    main()
