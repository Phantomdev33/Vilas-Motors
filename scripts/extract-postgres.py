"""Extract only the PostgreSQL server, not the optional pgAdmin/StackBuilder installers."""
import sys
import zipfile
import zlib
from pathlib import Path
root = Path(__file__).resolve().parents[1] / '.runtime'
with zipfile.ZipFile(root / 'postgres.zip') as archive:
    for info in archive.infolist():
        parts = Path(info.filename).parts
        if len(parts) < 2 or parts[0] != 'pgsql' or parts[1] not in ('bin', 'lib', 'share', 'server_license.txt', 'commandlinetools_3rd_party_licenses.txt'):
            continue
        target = (root / info.filename).resolve()
        if not target.is_relative_to(root.resolve()): raise RuntimeError('Ruta de archivo inválida.')
        if not info.is_dir() and target.exists() and target.stat().st_size == info.file_size:
            crc = 0
            with target.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024*1024), b''):
                    crc = zlib.crc32(chunk, crc)
            if crc == info.CRC: continue
        archive.extract(info, root)
(root / 'postgres-extracted').write_text('18.6', encoding='utf-8')
print('Servidor PostgreSQL extraído.')
