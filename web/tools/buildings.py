"""Convierte GML de edificios del Catastro INSPIRE a results/buildings.json para el visor.

Solo visual: el solver NO usa los edificios.
Uso (desde la raíz del repo):
    python web/tools/buildings.py [gml ...] [-o results/buildings.json]
Por defecto lee data/raw/catastro_bupart_brisamar.gml (BU.BUILDINGPART, trae nº de plantas) y,
si no existe, data/raw/catastro_bu_brisamar.gml (BU.BUILDING, sin plantas -> floors null).
Salida: lista de {"ring": [[x, y], ...] en EPSG:25831, "floors": int | null}.
Solo anillo exterior (se ignoran patios). Las partes con 0 plantas sobre rasante se descartan.
Solo biblioteca estándar; el GML se lee como texto con expresiones regulares (no se resuelven entidades).
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEATURE = re.compile(r"<bu-ext2d:(Building|BuildingPart)\b.*?</bu-ext2d:\1>", re.S)
EXTERIOR = re.compile(r"<gml:exterior>.*?<gml:posList[^>]*>([^<]+)</gml:posList>", re.S)
FLOORS = re.compile(r"<bu-ext2d:numberOfFloorsAboveGround>\s*(\d+)\s*<")


def parse(text):
    out, dropped = [], 0
    for m in FEATURE.finditer(text):
        block = m.group(0)
        fm = FLOORS.search(block)
        floors = int(fm.group(1)) if fm else None
        if floors == 0:
            dropped += 1
            continue
        for em in EXTERIOR.finditer(block):
            v = [float(t) for t in em.group(1).split()]
            ring = [[round(v[i], 2), round(v[i + 1], 2)] for i in range(0, len(v) - 1, 2)]
            if len(ring) >= 4:
                out.append({"ring": ring, "floors": floors})
    return out, dropped


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("gml", nargs="*")
    ap.add_argument("-o", "--out", default=str(ROOT / "results" / "buildings.json"))
    a = ap.parse_args()
    paths = [Path(p) for p in a.gml]
    if not paths:
        for name in ("catastro_bupart_brisamar.gml", "catastro_bu_brisamar.gml"):
            p = ROOT / "data" / "raw" / name
            if p.exists():
                paths = [p]
                break
    if not paths:
        raise SystemExit("No hay GML de Catastro en data/raw/")
    items, dropped = [], 0
    for p in paths:
        got, d = parse(p.read_text(encoding="latin-1"))
        items += got
        dropped += d
    Path(a.out).write_text(json.dumps(items, separators=(",", ":")), encoding="utf-8")
    known = sum(1 for b in items if b["floors"] is not None)
    print(f"{len(items)} huellas ({known} con plantas, {dropped} descartadas por 0 plantas sobre rasante) -> {a.out}")


if __name__ == "__main__":
    main()
