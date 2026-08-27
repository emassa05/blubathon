"""Carga un documento (PDF o texto plano) a la base local, para probar el
runtime de recomendaciones (`BLUBATHON_P1_ADAPTERS=real`) con contenido real.

No pasa por `tools.rag_authoring build`: ese comando solo escribe un
manifiesto offline, no hay loader que lo lleve a la base. Este script hace el
paso que falta: extrae texto, chunkea con `rag.domain.chunking` (el chunker
real) e inserta en `document_versions`/`document_chunks`.

Un PDF escaneado (imágenes sin capa de texto) no extrae nada; el script lo
dice en vez de cargar un documento vacío. Para esos hace falta OCR, que no
está en el repo.

`load_local_corpus` carga de una todo `data/local_corpus/`, y la llama
`tools.demo` para que el corpus real sobreviva a un `--reset`. La carga es
idempotente: el `document_version_id` sale de la ruta del archivo, así que
volver a cargar el mismo PDF no duplica nada.

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

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LOCAL_CORPUS_DIR = _REPOSITORY_ROOT / "data" / "local_corpus"
LOADABLE_SUFFIXES = (".pdf", ".txt", ".md")


class NoTextLayerError(RuntimeError):
    """El archivo no expone texto extraíble. Cargarlo dejaría un documento vacío."""


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
        raise NoTextLayerError(
            f"{path} no expone capa de texto (probablemente escaneado). "
            "Hace falta OCR, que no está en este repo."
        )
    return text


def load_document(
    connection: sqlite3.Connection,
    path: Path,
    *,
    title: str | None = None,
    publisher: str = "local-dev",
    canonical_url: str = "https://example.invalid/local-dev",
    language: str = "es",
) -> int:
    """Carga un archivo y devuelve cuántos chunks insertó. 0 si ya estaba.

    El `document_version_id` es `uuid5` de la ruta absoluta, así que cargar dos
    veces el mismo archivo no duplica: la segunda vez no hay nada que insertar.
    """

    document_version_id = uuid.uuid5(NAMESPACE, str(path.resolve()))
    already = connection.execute(
        "SELECT 1 FROM document_versions WHERE document_version_id = ?",
        (str(document_version_id),),
    ).fetchone()
    if already is not None:
        return 0

    text = extract_text(path)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    chunks = chunk_document(
        document_version_id=document_version_id,
        text=text,
        plan=CHUNK_PLAN,
        chunk_id_for=lambda locator: uuid.uuid5(document_version_id, locator),
    )
    if not chunks:
        raise NoTextLayerError(f"{path} no produjo ningún párrafo chunkeable")

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
            publisher,
            title or path.stem,
            now,
            now,
            canonical_url,
            _sha256(text),
            _sha256(text),
            language,
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
    return len(chunks)


def load_local_corpus(
    connection: sqlite3.Connection, directory: Path = LOCAL_CORPUS_DIR
) -> tuple[int, int, tuple[str, ...]]:
    """Carga todo el corpus local. Devuelve (documentos, chunks, omitidos).

    Un escaneado sin capa de texto se omite con su motivo en vez de abortar: el
    montaje tiene que terminar aunque un PDF del directorio no sirva.
    """

    if not directory.is_dir():
        return 0, 0, ()
    documentos = 0
    fragmentos = 0
    omitidos: list[str] = []
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in LOADABLE_SUFFIXES:
            continue
        try:
            cargados = load_document(connection, path)
        except NoTextLayerError as error:
            omitidos.append(str(error))
            continue
        if cargados:
            documentos += 1
            fragmentos += cargados
    return documentos, fragmentos, tuple(omitidos)


def export_corpus(db_path: Path) -> dict[str, list[tuple]]:
    """Las filas del corpus local, para que sobrevivan a un borrado de la base.

    Solo `local_dev_only`: lo sembrado vuelve con `seed()`, y copiarlo además
    duplicaría trabajo. Devuelve vacío si la base no existe todavía o si las
    tablas aún no fueron migradas, que es el caso de un montaje desde cero.
    """

    if not db_path.exists():
        return {}
    connection = sqlite3.connect(db_path)
    try:
        versions = connection.execute(
            "SELECT * FROM document_versions WHERE rights_basis = 'local_dev_only'"
        ).fetchall()
        if not versions:
            return {}
        identifiers = tuple(row[0] for row in versions)
        marcas = ",".join("?" * len(identifiers))
        chunks = connection.execute(
            f"SELECT * FROM document_chunks WHERE document_version_id IN ({marcas})",
            identifiers,
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        connection.close()
    return {"document_versions": versions, "document_chunks": chunks}


def restore_corpus(connection: sqlite3.Connection, snapshot: dict[str, list[tuple]]) -> int:
    """Reinserta lo que devolvió `export_corpus`. Devuelve cuántos chunks volvieron."""

    if not snapshot:
        return 0
    for tabla, filas in snapshot.items():
        if not filas:
            continue
        marcas = ",".join("?" * len(filas[0]))
        connection.executemany(f"INSERT OR IGNORE INTO {tabla} VALUES ({marcas})", filas)
    connection.commit()
    return len(snapshot.get("document_chunks", ()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--file", type=Path, required=True, help="PDF, .txt o .md")
    parser.add_argument("--title", required=True)
    parser.add_argument("--publisher", default="local-dev")
    parser.add_argument("--canonical-url", default="https://example.invalid/local-dev")
    parser.add_argument("--language", default="es")
    args = parser.parse_args(argv)

    connection = sqlite3.connect(args.db)
    try:
        cargados = load_document(
            connection,
            args.file,
            title=args.title,
            publisher=args.publisher,
            canonical_url=args.canonical_url,
            language=args.language,
        )
        connection.commit()
    except NoTextLayerError as error:
        raise SystemExit(str(error)) from error
    finally:
        connection.close()

    if not cargados:
        print(f"{args.file} ya estaba cargado; no se duplicó")
        return 0
    print(f"{cargados} chunks cargados desde {args.file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
