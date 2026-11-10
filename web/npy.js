// Parser mínimo de .npy según docs/CONTRACTS.md 6.1: float32, orden C, forma (ny, nx), fila 0 = norte.
// Devuelve { data: Float32Array, ny, nx }. Lanza Error con mensaje en español si el archivo no cumple.
export function parseNpy(buffer, expected) {
  const u8 = new Uint8Array(buffer);
  const magic = [0x93, 0x4e, 0x55, 0x4d, 0x50, 0x59]; // \x93NUMPY
  if (u8.length < 10 || magic.some((b, i) => u8[i] !== b)) throw new Error('no es un archivo .npy (cabecera mágica incorrecta)');
  const major = u8[6];
  const dv = new DataView(buffer);
  let hlen, off;
  if (major === 1) { hlen = dv.getUint16(8, true); off = 10; }
  else if (major === 2 || major === 3) { hlen = dv.getUint32(8, true); off = 12; }
  else throw new Error(`versión .npy no soportada: ${major}`);
  if (off + hlen > u8.length) throw new Error('cabecera .npy truncada');
  const header = new TextDecoder(major === 3 ? 'utf-8' : 'latin1').decode(u8.subarray(off, off + hlen));
  const descr = /'descr'\s*:\s*'([^']+)'/.exec(header)?.[1];
  const fortran = /'fortran_order'\s*:\s*(True|False)/.exec(header)?.[1];
  const shapeTxt = /'shape'\s*:\s*\(([^)]*)\)/.exec(header)?.[1];
  if (!descr || !fortran || shapeTxt === undefined) throw new Error('cabecera .npy ilegible');
  if (descr !== '<f4') throw new Error(`dtype ${descr}: se esperaba float32 little-endian ('<f4')`);
  if (fortran !== 'False') throw new Error('orden Fortran: se esperaba orden C');
  const shape = shapeTxt.split(',').map(s => s.trim()).filter(Boolean).map(Number);
  if (shape.length !== 2 || shape.some(n => !Number.isInteger(n) || n <= 0)) throw new Error(`forma (${shapeTxt}): se esperaba (ny, nx)`);
  const [ny, nx] = shape;
  if (expected && (expected.ny !== ny || expected.nx !== nx)) {
    throw new Error(`forma (${ny}, ${nx}) distinta de la malla de index.json (${expected.ny}, ${expected.nx})`);
  }
  const start = off + hlen;
  if (u8.length - start < ny * nx * 4) throw new Error('datos .npy truncados');
  // slice => copia alineada (el offset no siempre es múltiplo de 4)
  const data = new Float32Array(buffer.slice(start, start + ny * nx * 4));
  return { data, ny, nx };
}
