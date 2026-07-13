"""Migração única: extrai as imagens dos parquets (data/*.parquet, incluindo
uploads-{squad}.parquet) para arquivos .webp em imagens/{squad}/.

Depois de migrar e conferir os leitores, os parquets e uploads/ antigos podem
ser removidos — deixe de propósito para o usuário confirmar antes de apagar.

Rodar uma vez, com o servidor parado: python migrar_para_webp.py
"""
import base64
import io
import json
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image

ROOT = Path(__file__).resolve().parent
QUALIDADE_WEBP = 80


def migrar_squad(squad: str) -> None:
    manifest = ROOT / squad / "manifest.json"
    if not manifest.is_file():
        print(f"[{squad}] manifest.json não encontrado, pulando")
        return

    nomes = json.loads(manifest.read_text(encoding="utf-8"))
    fragmentos: dict[str, list[str]] = {}

    for nome in nomes:
        p = (ROOT / squad / nome).resolve()
        if not p.is_file():
            print(f"[{squad}] parquet ausente, ignorado: {nome}")
            continue
        print(f"[{squad}] lendo {p.name}...")
        tabela = pq.read_table(p, columns=["IWP", "Pic"])
        for iwp, pic in zip(tabela.column("IWP").to_pylist(),
                             tabela.column("Pic").to_pylist()):
            fragmentos.setdefault(iwp, []).append(pic)

    destino = ROOT / "imagens" / squad
    destino.mkdir(parents=True, exist_ok=True)

    total, falhas = 0, 0
    for iwp_completo, partes in fragmentos.items():
        try:
            b64 = "".join(partes)
            img = Image.open(io.BytesIO(base64.b64decode(b64)))
            img.save(destino / f"{iwp_completo}.webp", "WEBP", quality=QUALIDADE_WEBP)
            total += 1
        except Exception as e:
            falhas += 1
            print(f"[{squad}] falha ao converter '{iwp_completo}': {e}")

    print(f"[{squad}] {total} imagens migradas para imagens/{squad}/"
          f"{f' ({falhas} falharam)' if falhas else ''}")


if __name__ == "__main__":
    squads = json.loads((ROOT / "squads.json").read_text(encoding="utf-8"))
    for s in squads:
        migrar_squad(s["pasta"])
