from pathlib import Path

from app.rag.types import IndexDocument

CODE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".toml"}


def _line_window(lines: list[str], size: int, overlap: int) -> list[tuple[int, int, str]]:
    if not lines:
        return []
    chunks: list[tuple[int, int, str]] = []
    step = max(1, size - overlap)
    for start in range(0, len(lines), step):
        end = min(len(lines), start + size)
        text = "".join(lines[start:end]).strip()
        if text:
            chunks.append((start + 1, end, text))
        if end == len(lines):
            break
    return chunks


def chunk_markdown(
    path: Path,
    repo_root: Path,
    size: int = 80,
    overlap: int = 10,
) -> list[IndexDocument]:
    rel = path.relative_to(repo_root).as_posix()
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    docs: list[IndexDocument] = []
    for i, (start, end, text) in enumerate(_line_window(lines, size, overlap)):
        section = _nearest_heading(lines, start)
        docs.append(
            IndexDocument(
                id=f"doc:{rel}:{start}:{end}:{i}",
                source_type="doc",
                text=text,
                metadata={
                    "source_type": "doc",
                    "path": rel,
                    "section_title": section,
                    "start_line": start,
                    "end_line": end,
                },
            )
        )
    return docs


def chunk_code(
    path: Path,
    repo_root: Path,
    size: int = 80,
    overlap: int = 10,
) -> list[IndexDocument]:
    rel = path.relative_to(repo_root).as_posix()
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    language = _language_for(path.suffix)
    docs: list[IndexDocument] = []
    for i, (start, end, text) in enumerate(_line_window(lines, size, overlap)):
        docs.append(
            IndexDocument(
                id=f"code:{rel}:{start}:{end}:{i}",
                source_type="code",
                text=text,
                metadata={
                    "source_type": "code",
                    "path": rel,
                    "language": language,
                    "symbol_name": None,
                    "start_line": start,
                    "end_line": end,
                },
            )
        )
    return docs


def _nearest_heading(lines: list[str], start_line: int) -> str | None:
    for line in reversed(lines[:start_line]):
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return None


def _language_for(suffix: str) -> str:
    return {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript-react",
        ".js": "javascript",
        ".jsx": "javascript-react",
        ".go": "go",
        ".rs": "rust",
        ".toml": "toml",
    }.get(suffix, "text")
