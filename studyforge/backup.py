from __future__ import annotations
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from .config import settings

FORMAT_VERSION = 1


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _safe_member(name: str) -> bool:
    p = Path(name)
    return not p.is_absolute() and '..' not in p.parts


def export_backup(destination: str | None = None) -> str:
    """Create a portable backup containing SQLite state and uploaded documents.

    Model weights are intentionally excluded: they can be downloaded again on the target.
    """
    destination = destination or f'tutor-llm-backup-{_utc_stamp()}.zip'
    destination = str(Path(destination).expanduser().resolve())
    db_source = Path(settings.db_path)
    uploads = Path(settings.upload_dir)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        db_copy = root / 'studyforge.db'
        db_copy.parent.mkdir(parents=True, exist_ok=True)
        if db_source.exists():
            src = sqlite3.connect(str(db_source))
            dst = sqlite3.connect(str(db_copy))
            try:
                src.backup(dst)
            finally:
                dst.close(); src.close()
        else:
            sqlite3.connect(str(db_copy)).close()
        manifest = {
            'format': 'tutor-llm-backup',
            'format_version': FORMAT_VERSION,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'deploy_mode': settings.deploy_mode,
            'chat_model': settings.chat_model,
            'embedding_model': settings.embedding_model,
            'models_included': False,
        }
        (root / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(db_copy, 'studyforge.db')
            zf.write(root / 'manifest.json', 'manifest.json')
            if uploads.exists():
                for path in uploads.rglob('*'):
                    if path.is_file():
                        zf.write(path, str(Path('uploads') / path.relative_to(uploads)))
    return destination


def inspect_backup(archive: str) -> dict:
    archive = str(Path(archive).expanduser().resolve())
    with zipfile.ZipFile(archive, 'r') as zf:
        names = zf.namelist()
        if any(not _safe_member(n) for n in names):
            raise ValueError('Backup non valido: contiene percorsi non sicuri.')
        if 'manifest.json' not in names or 'studyforge.db' not in names:
            raise ValueError('Backup Tutor LLM non valido.')
        manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
        if manifest.get('format') != 'tutor-llm-backup' or int(manifest.get('format_version', -1)) != FORMAT_VERSION:
            raise ValueError('Versione backup non supportata.')
        manifest['file_count'] = len(names)
        return manifest


def _relocate_document_paths(db_target: Path, uploads_target: Path) -> None:
    con = sqlite3.connect(str(db_target))
    con.row_factory = sqlite3.Row
    try:
        exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='documents'").fetchone()
        if not exists:
            return
        rows = con.execute('SELECT id,workspace_id,path FROM documents').fetchall()
        for row in rows:
            old_name = Path(row['path']).name
            new_path = uploads_target / str(row['workspace_id']) / old_name
            con.execute('UPDATE documents SET path=? WHERE id=?', (str(new_path), int(row['id'])))
        con.commit()
    finally:
        con.close()


def import_backup(archive: str, *, replace: bool = False) -> dict:
    """Restore a backup. Intended to run while Tutor LLM services are stopped."""
    manifest = inspect_backup(archive)
    db_target = Path(settings.db_path).expanduser().resolve()
    uploads_target = Path(settings.upload_dir).expanduser().resolve()
    if not replace and (db_target.exists() or (uploads_target.exists() and any(uploads_target.rglob('*')))):
        raise FileExistsError('Esistono già dati Tutor LLM. Usa replace=True solo dopo aver creato un backup.')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(str(Path(archive).expanduser().resolve()), 'r') as zf:
            for name in zf.namelist():
                if not _safe_member(name):
                    raise ValueError('Backup non valido: percorso non sicuro.')
            zf.extractall(root)
        db_target.parent.mkdir(parents=True, exist_ok=True)
        if replace and db_target.exists():
            db_target.unlink()
        shutil.copy2(root / 'studyforge.db', db_target)
        extracted_uploads = root / 'uploads'
        if replace and uploads_target.exists():
            shutil.rmtree(uploads_target)
        uploads_target.mkdir(parents=True, exist_ok=True)
        if extracted_uploads.exists():
            for src in extracted_uploads.rglob('*'):
                if src.is_file():
                    dst = uploads_target / src.relative_to(extracted_uploads)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
        _relocate_document_paths(db_target, uploads_target)
    return manifest
