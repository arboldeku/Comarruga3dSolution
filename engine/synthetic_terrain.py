"""Terreno de la zona de estudio.

Si existe `data/raw/dem_comarruga.tif` y rasterio está instalado se usa ese MDT
(rama NO probada en el hackathon). En caso contrario se genera un terreno
SINTÉTICO reproducible (semilla 42): no representa la topografía real de Comarruga.

Convención (contrato 6.1): arrays float32, forma (ny, nx), fila 0 = norte, metros.
landuse: 0 = no urbano, 1 = urbano, 2 = cauce.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

NY, NX, CELL_M = 200, 200, 5.0
URBAN_ROWS = (85, 190)          # tramo urbano (filas)
URBAN_COLS = (25, 175)
REAL_DEM = Path("data/raw/dem_comarruga.tif")

# Depresiones urbanas sintéticas: (fila, desplazamiento en columnas respecto al
# eje del cauce, profundidad m, radio en celdas). Supuestos del terreno sintético.
DEPRESSIONS = [
    (105, +9, 0.9, 5.0), (135, -10, 0.8, 5.0), (166, +10, 0.7, 6.0),   # junto al cauce
    (100, -45, 0.6, 6.0), (125, +50, 0.7, 6.0), (150, -55, 0.6, 5.0),  # alejadas
    (176, +45, 0.5, 6.0), (143, +27, 0.5, 5.0),
]


@dataclass(frozen=True)
class Terrain:
    dem: np.ndarray        # (ny, nx) float32, m
    landuse: np.ndarray    # (ny, nx) float32
    cell_m: float
    dem_source: str
    dem_sha256: str
    seed: int


def channel_center(rows: np.ndarray) -> np.ndarray:
    """Columna del eje del cauce (riera) en cada fila."""
    return 100.0 + 18.0 * np.sin(rows / 32.0)


def sha256_array(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float32).tobytes()).hexdigest()


def make_synthetic(seed: int = 42) -> Terrain:
    rng = np.random.default_rng(seed)
    r = np.arange(NY, dtype=float)[:, None]
    c = np.arange(NX, dtype=float)[None, :]
    cc = channel_center(r)
    off = c - cc

    # Ladera hacia el sur (mar): 4 % en cabecera, ~1,1 % en el tramo urbano.
    base = np.where(r < 80, 8.0 + (80 - r) * CELL_M * 0.04, 8.0 - (r - 80) * CELL_M * 0.011)
    z = base + 0.008 * np.abs(off) * CELL_M            # pendiente transversal hacia el cauce
    noise = gaussian_filter(rng.standard_normal((NY, NX)), 4.0)
    z = z + 0.10 * noise / noise.std()                 # microrrelieve suave (~10 cm)

    urban = (r >= URBAN_ROWS[0]) & (r < URBAN_ROWS[1]) & (c >= URBAN_COLS[0]) & (c < URBAN_COLS[1])
    for row, doff, depth, rad in DEPRESSIONS:
        col = float(channel_center(np.array(float(row)))) + doff
        d2 = (r - row) ** 2 + (c - col) ** 2
        z = z - depth * np.exp(-d2 / (2.0 * (rad / 1.6) ** 2))

    # Cauce: más ancho y hondo en cabecera, estrechado en el tramo urbano (cuello de botella).
    in_urban_reach = (r >= URBAN_ROWS[0]) & (r < URBAN_ROWS[1])
    half_w = np.where(in_urban_reach, 1.0, 1.6)
    # la profundidad pasa de 1,6 m a 0,8 m de forma gradual (filas 60-85) para no crear un escalón
    depth = np.clip(1.6 - 0.8 * (r - 60.0) / 25.0, 0.8, 1.6)
    depth = np.where(r >= URBAN_ROWS[1], 0.8, depth)
    channel = np.abs(off) <= half_w
    bed = np.broadcast_to(base - depth, (NY, NX))
    z = np.where(channel, bed, z)

    landuse = np.zeros((NY, NX), dtype=np.float32)
    landuse[urban] = 1.0
    landuse[channel] = 2.0
    dem = z.astype(np.float32)
    return Terrain(dem, landuse, CELL_M, "sintético", sha256_array(dem), seed)


def _load_real() -> Terrain | None:  # pragma: no cover - rama opcional no probada
    if not REAL_DEM.exists():
        return None
    try:
        import rasterio
    except ImportError:
        return None
    with rasterio.open(REAL_DEM) as src:
        dem = src.read(1).astype(np.float32)
        cell = float(abs(src.transform.a))
    # Sin capa de usos del suelo real: todo "no urbano" (sin dato).
    landuse = np.zeros_like(dem, dtype=np.float32)
    return Terrain(dem, landuse, cell, str(REAL_DEM).replace("\\", "/"), sha256_array(dem), 42)


def load_terrain(seed: int = 42) -> Terrain:
    return _load_real() or make_synthetic(seed)
