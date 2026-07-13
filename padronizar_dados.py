"""Padroniza a tabela iwp: registra codigos de imagens faltantes no banco,
limpa linhas orfas, atribui squad_id as CWAs.

Roda uma vez (idempotente): python padronizar_dados.py
"""
import sys
import sqlite3
from pathlib import Path
from collections import defaultdict
import io

# Force UTF-8 output no Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Importa app.py do deploy/ para reusar suas funções
sys.path.insert(0, str(Path(__file__).resolve().parent / "deploy"))
import app

ROOT = Path(__file__).resolve().parent
IMAGENS = ROOT / "deploy" / "imagens"


def varrer_imagens():
    """Lê todas as imagens em imagens/{squad}/*.webp e devolve
    {codigo: {squad, vistas}} — agrupa por código, pra saber de qual squad
    cada código veio."""
    codigos = defaultdict(lambda: {"squads": set(), "vistas": set()})

    if not IMAGENS.is_dir():
        return codigos

    # Varre todos os squads (pastas em imagens/)
    for squad_dir in IMAGENS.iterdir():
        if not squad_dir.is_dir():
            continue
        squad = squad_dir.name

        # Varre arquivos .webp da pasta do squad
        for arq in squad_dir.glob("*.webp"):
            # Nome: {codigo} - {vista}.webp
            sep = arq.stem.rfind(" - ")
            if sep == -1:
                continue
            codigo = arq.stem[:sep]
            vista = arq.stem[sep + 3:]
            codigos[codigo]["squads"].add(squad)
            codigos[codigo]["vistas"].add(vista)

    return codigos


def main():
    print("=" * 70)
    print("Padronizando dados: cadastrando imagens, limpando orfaos, atribuindo squads")
    print("=" * 70)
    print()

    con = app.db()
    codigos_imagem = varrer_imagens()

    # Estatísticas
    novos_projetos = set()
    novas_cwas = set()
    novos_cwps = set()
    novos_iwps = []
    iwps_deletados = []
    cwas_com_squad = []
    cwas_multiplos_squads = []

    # -----------------------------------------------------------------------
    # 1. Inserir códigos de imagem que faltam no banco
    # -----------------------------------------------------------------------
    print("1. Varrendo imagens e cadastrando códigos faltantes...")
    codigo_sem_imagem = set()  # códigos que existem em iwp mas não têm imagem

    for codigo, info in sorted(codigos_imagem.items()):
        squads = info["squads"]

        # Valida o código e processa
        campos = app.parse_codigo(codigo)
        if campos is None:
            print(f"   AVISO: código não parseável: {codigo}")
            continue

        # Verifica se existe na tabela iwp
        existe = con.execute("SELECT id FROM iwp WHERE codigo = ?", (codigo,)).fetchone()
        if existe:
            # Código já cadastrado; registra que tem imagem
            continue

        # Inserir: get-or-create projeto→cwa→cwp
        try:
            cwp_id, _ = app.cadeia_ids(con, campos)
            con.execute(
                "INSERT INTO iwp (cwp_id, codigo, rotulo, descricao) VALUES (?,?,?,?)",
                (cwp_id, codigo, campos["iwp"], "")
            )
            novos_iwps.append(codigo)
            novos_projetos.add(campos["projeto"])
            novas_cwas.add((campos["projeto"], campos["cwa"]))
            novos_cwps.add((campos["cwa"], campos["disc"], campos["cwp"]))
        except sqlite3.IntegrityError as e:
            print(f"   ERRO ao inserir {codigo}: {e}")
            continue

    # -----------------------------------------------------------------------
    # 2. Limpar linhas de iwp sem imagem (case-insensitive, só se houver imagem)
    # -----------------------------------------------------------------------
    print()
    print("2. Limpando linhas orfas (iwp sem imagem)...")

    # Cria um mapa case-insensitive de códigos de imagem
    codigos_imagem_lower = {k.lower(): k for k in codigos_imagem.keys()}

    for row in con.execute("SELECT id, codigo FROM iwp").fetchall():
        codigo = row["codigo"]
        codigo_lower = codigo.lower()

        if codigo_lower not in codigos_imagem_lower:
            # Não existe imagem para este código
            existe_imagem_com_outro_case = codigo_lower in codigos_imagem_lower
            if existe_imagem_com_outro_case:
                # Case diferente, mas mesmo código com imagem
                con.execute("DELETE FROM iwp WHERE id = ?", (row["id"],))
                iwps_deletados.append(codigo)
                print(f"   DELETADO (case diferente): {codigo}")
            # Senão, só reporta sem deletar

    # -----------------------------------------------------------------------
    # 3. Atribuir squad_id às CWAs
    # -----------------------------------------------------------------------
    print()
    print("3. Atribuindo squad_id às CWAs...")

    for row in con.execute("SELECT id, codigo FROM cwa").fetchall():
        cwa_id = row["id"]

        # Acha todos os códigos de iwp desta CWA que têm imagem
        codigos_cwa_com_imagem = set()
        for iwp_row in con.execute(
            """SELECT iwp.codigo FROM iwp
               JOIN cwp ON cwp.id = iwp.cwp_id
               WHERE cwp.cwa_id = ?""",
            (cwa_id,)
        ).fetchall():
            cod = iwp_row["codigo"]
            if cod in codigos_imagem or cod.lower() in {k.lower() for k in codigos_imagem}:
                codigos_cwa_com_imagem.add(cod)

        if not codigos_cwa_com_imagem:
            # Nenhuma imagem para esta CWA
            continue

        # Acha de qual(is) squad(s) são as imagens
        squads_desta_cwa = set()
        for cod in codigos_cwa_com_imagem:
            if cod in codigos_imagem:
                squads_desta_cwa.update(codigos_imagem[cod]["squads"])
            else:
                # Tenta case-insensitive
                cod_lower = cod.lower()
                for k, v in codigos_imagem.items():
                    if k.lower() == cod_lower:
                        squads_desta_cwa.update(v["squads"])
                        break

        if len(squads_desta_cwa) == 1:
            squad_name = list(squads_desta_cwa)[0]
            # Acha o id do squad
            squad_row = con.execute("SELECT id FROM squad WHERE pasta = ?", (squad_name,)).fetchone()
            if squad_row:
                squad_id = squad_row["id"]
                con.execute("UPDATE cwa SET squad_id = ? WHERE id = ?", (squad_id, cwa_id))
                cwas_com_squad.append((row["codigo"], squad_name))
                print(f"   CWA {row['codigo']} > squad {squad_name}")
        elif len(squads_desta_cwa) > 1:
            print(f"   AVISO: CWA {row['codigo']} tem imagens em múltiplos squads: {squads_desta_cwa}")
            cwas_multiplos_squads.append((row["codigo"], squads_desta_cwa))

    con.commit()

    # -----------------------------------------------------------------------
    # Relatório
    # -----------------------------------------------------------------------
    print()
    print("=" * 70)
    print("RELATÓRIO FINAL")
    print("=" * 70)
    print()
    print(f"Projetos criados:       {len(novos_projetos)}")
    print(f"CWAs criadas:           {len(novas_cwas)}")
    print(f"CWPs criados:           {len(novos_cwps)}")
    print(f"IWPs registrados:       {len(novos_iwps)}")
    print(f"IWPs deletados:         {len(iwps_deletados)}")
    print(f"CWAs com squad_id:      {len(cwas_com_squad)}")
    if cwas_multiplos_squads:
        print(f"CWAs em múltiplos squads: {len(cwas_multiplos_squads)}")
    print()

    if iwps_deletados:
        print("IWPs deletados (case mismatch):")
        for cod in iwps_deletados:
            print(f"  - {cod}")
        print()

    if cwas_multiplos_squads:
        print("CWAs em múltiplos squads (sem atribuição):")
        for cwa, squads in cwas_multiplos_squads:
            print(f"  - {cwa}: {squads}")
        print()

    # -----------------------------------------------------------------------
    # Autoteste: valida que todo código de imagem tem exatamente 1 linha em iwp
    # -----------------------------------------------------------------------
    print("=" * 70)
    print("AUTOTESTE")
    print("=" * 70)
    print()

    erros = []
    for codigo in codigos_imagem.keys():
        count = con.execute("SELECT COUNT(*) as cnt FROM iwp WHERE codigo = ?", (codigo,)).fetchone()["cnt"]
        if count != 1:
            erros.append(f"{codigo}: {count} linhas (esperado 1)")

    if erros:
        print("FALHA:")
        for erro in erros:
            print(f"  - {erro}")
    else:
        print("[OK] Todos os codigos de imagem tem exatamente 1 linha em iwp")

    con.close()


if __name__ == "__main__":
    main()
