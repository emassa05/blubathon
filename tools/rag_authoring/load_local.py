"""Carga un documento (PDF o texto plano) a la base local, para probar el
runtime de recomendaciones (`BLUBATHON_P1_ADAPTERS=real`) con contenido real.

No pasa por `tools.rag_authoring build`: ese comando solo escribe un
manifiesto offline, no hay loader que lo lleve a la base. Este script hace el
paso que falta: extrae texto, chunkea con `rag.domain.chunking` (el chunker
real) e inserta en `document_versions`/`document_chunks`.

Un PDF escaneado (imágenes sin capa de texto) no extrae nada; el script lo
dice en vez de cargar un documento vacío. Para esos hace falta OCR, que no
está en el repo.

Uso:
    python -m tools.rag_authoring.load_local --db data/blubathon.db \
        --title "Guía TEA" --file guia.pdf
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from rag.domain.chunking import ChunkPlan, chunk_document

CHUNK_PLAN = ChunkPlan(chunk_size=220, chunk_overlap=40)
NAMESPACE = uuid.UUID("6f2a8b1e-0000-4000-8000-000000000000")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_text(path: Path) -> str:
    """Texto plano tal cual; PDF vía pypdf, página por página."""

    if path.suffix.lower() != ".pdf":
        return path.read_text(encoding="utf-8")

    from pypdf import PdfReader

    pages = [page.extract_text() or "" for page in PdfReader(str(path)).pages]
    text = "\n\n".join(page.strip() for page in pages if page.strip())
    if not text.strip():
        raise SystemExit(
            f"{path} no expone capa de texto (probablemente escaneado). "
            "Hace falta OCR, que no está en este repo."
        )
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--file", type=Path, required=True, help="PDF, .txt o .md")
    parser.add_argument("--title", required=True)
    parser.add_argument("--publisher", default="local-dev")
    parser.add_argument("--canonical-url", default="https://example.invalid/local-dev")
    parser.add_argument("--language", default="es")
    args = parser.parse_args(argv)

    text = extract_text(args.file)
    document_version_id = uuid.uuid5(NAMESPACE, str(args.file.resolve()))
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    chunks = chunk_document(
        document_version_id=document_version_id,
        text=text,
        plan=CHUNK_PLAN,
        chunk_id_for=lambda locator: uuid.uuid5(document_version_id, locator),
    )
    if not chunks:
        raise SystemExit("el texto no produjo ningún párrafo chunkeable")

    connection = sqlite3.connect(args.db)
    connection.execute(
        "INSERT INTO document_versions(document_version_id, source_id, publisher, title,"
        " document_version, publication_date, retrieved_at, canonical_url, rights_basis,"
        " original_bytes_sha256, extracted_text_sha256, extraction_manifest_id, language,"
        " status, corpus_version, created_at)"
        " VALUES (?, ?, ?, ?, '1', ?, ?, ?, 'local_dev_only', ?, ?, 'local-dev', ?, 'active',"
        " NULL, ?)",
        (
            str(document_version_id),
            str(document_version_id),
            args.publisher,
            args.title,
            now,
            now,
            args.canonical_url,
            _sha256(text),
            _sha256(text),
            args.language,
            now,
        ),
    )
    for chunk in chunks:
        connection.execute(
            "INSERT INTO document_chunks(document_chunk_id, document_version_id, locator,"
            " text, chunk_sha256, chunker_version, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(chunk.document_chunk_id),
                str(document_version_id),
                chunk.locator,
                chunk.text,
                chunk.chunk_sha256,
                chunk.chunker_version,
                now,
            ),
        )
    connection.commit()
    connection.close()
    print(f"{len(chunks)} chunks cargados desde {args.file} ({document_version_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
