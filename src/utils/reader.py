"""
文件读取工具，支持自动识别文件类型并读取纯文本内容。
覆盖 txt、md、html、pdf、docx 五种核心格式。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from charset_normalizer import from_bytes

_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


class ReaderError(Exception):
    """文件读取异常基类"""
    pass


class UnsupportedFormatError(ReaderError):
    """不支持的文件格式"""
    pass


class FileSizeLimitError(ReaderError):
    """文件超过大小限制"""
    pass


class DecodeError(ReaderError):
    """文件解码或解析失败"""
    pass


@dataclass
class ReadMeta:
    """文件读取元数据"""
    path: str
    format: str
    size_bytes: int
    encoding: str | None = None
    pages: int | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class ReadResult:
    """文件读取完整结果"""
    text: str
    meta: ReadMeta


try:
    import lxml  # noqa: F401
    _HAS_LXML = True
except ImportError:
    _HAS_LXML = False

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment, misc]

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None  # type: ignore[assignment, misc]

try:
    from docx import Document
except ImportError:
    Document = None  # type: ignore[assignment]


def _detect_encoding(raw: bytes) -> str:
    """
    检测字节序列的文本编码。
    优先使用 charset_normalizer，失败时依次回退 utf-8、gb18030、latin-1。
    """
    result = from_bytes(raw)
    best = result.best()
    if best is not None and best.chaos < 0.5:
        return best.encoding
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    return "utf-8"


def _read_text_like(path: Path) -> tuple[str, ReadMeta]:
    """
    读取纯文本文件（txt、md、markdown 等）。
    自动检测编码，返回文本和元数据。
    """
    raw = path.read_bytes()
    enc = _detect_encoding(raw)
    try:
        text = raw.decode(enc)
    except UnicodeDecodeError:
        for fallback in ("utf-8", "gb18030", "latin-1"):
            try:
                text = raw.decode(fallback)
                enc = fallback
                break
            except UnicodeDecodeError:
                continue
        else:
            raise DecodeError(f"无法解码文件：{path}")
    meta = ReadMeta(
        path=str(path),
        format=path.suffix.lstrip("."),
        size_bytes=len(raw),
        encoding=enc,
    )
    return text, meta


_HTML_STRIP_TAGS = frozenset({"script", "style", "noscript", "header", "footer", "nav"})


def _read_html(path: Path) -> tuple[str, ReadMeta]:
    """
    读取 HTML 文件，移除脚本和样式标签后提取纯文本。
    需要 beautifulsoup4 和 lxml。
    """
    if BeautifulSoup is None or not _HAS_LXML:
        raise ReaderError("读取 HTML 需要 beautifulsoup4 和 lxml，请运行：pip install beautifulsoup4 lxml")
    raw = path.read_bytes()
    enc = _detect_encoding(raw)
    html = raw.decode(enc, errors="replace")
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(list(_HTML_STRIP_TAGS)):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [line for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)
    meta = ReadMeta(
        path=str(path),
        format="html",
        size_bytes=len(raw),
        encoding=enc,
    )
    return text, meta


def _read_pdf(path: Path) -> tuple[str, ReadMeta]:
    """
    读取 PDF 文件，按页提取文本并用双换行拼接。
    检测到加密时抛出 DecodeError。
    需要 PyPDF2。
    """
    if PdfReader is None:
        raise ReaderError("读取 PDF 需要 PyPDF2，请运行：pip install PyPDF2")
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise DecodeError(f"PDF 已加密，无法读取：{path}")
    parts = []
    warnings = []
    for i, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
            if page_text.strip():
                parts.append(page_text.strip())
        except Exception as e:
            warnings.append(f"第 {i + 1} 页解析失败：{e}")
    text = "\n\n".join(parts)
    meta = ReadMeta(
        path=str(path),
        format="pdf",
        size_bytes=path.stat().st_size,
        pages=len(reader.pages),
        warnings=warnings,
    )
    return text, meta


def _read_docx(path: Path) -> tuple[str, ReadMeta]:
    """
    读取 DOCX 文件，提取段落和表格文本。
    段落按顺序拼接，表格每行用 | 分隔单元格。
    需要 python-docx。
    """
    if Document is None:
        raise ReaderError("读取 DOCX 需要 python-docx，请运行：pip install python-docx")
    doc = Document(str(path))
    parts = []
    table_map = {id(t._element): t for t in doc.tables}
    for element in doc.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
        if tag == "p":
            text = element.text_content().strip() if hasattr(element, "text_content") else ""
            if text:
                parts.append(text)
        elif tag == "tbl":
            table = table_map.get(id(element))
            if table is not None:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    parts.append(" | ".join(cells))
    text = "\n".join(parts)
    meta = ReadMeta(
        path=str(path),
        format="docx",
        size_bytes=path.stat().st_size,
    )
    return text, meta


_READERS: dict[str, Callable[[Path], tuple[str, ReadMeta]]] = {
    ".txt": _read_text_like,
    ".md": _read_text_like,
    ".markdown": _read_text_like,
    ".html": _read_html,
    ".htm": _read_html,
    ".pdf": _read_pdf,
    ".docx": _read_docx,
}


def _resolve_reader(path: Path) -> Callable[[Path], tuple[str, ReadMeta]]:
    """
    根据文件扩展名查找对应的 reader 函数。
    找不到时抛出 UnsupportedFormatError。
    """
    ext = path.suffix.lower()
    reader = _READERS.get(ext)
    if reader is None:
        supported = ", ".join(sorted(_READERS.keys()))
        raise UnsupportedFormatError(f"不支持的文件格式：{ext}。当前支持：{supported}")
    return reader


def _validate_path(path: str | Path) -> Path:
    """
    校验文件路径：存在性检查和大小限制检查。
    参数:
        path: 文件路径
    返回:
        Path: 校验通过的 Path 对象
    异常:
        FileNotFoundError: 文件不存在
        FileSizeLimitError: 文件超过大小限制
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在：{p}")
    size = p.stat().st_size
    if size > _MAX_FILE_SIZE_BYTES:
        limit_mb = _MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise FileSizeLimitError(f"文件 {p} 大小 {size} 字节，超过 {limit_mb}MB 限制")
    return p


def read(path: str | Path) -> str:
    """
    读取文件并返回纯文本内容。
    自动根据文件扩展名选择对应的读取器。
    参数:
        path: 文件路径，支持 str 或 Path 对象
    返回:
        str: 文件纯文本内容
    异常:
        FileNotFoundError: 文件不存在
        FileSizeLimitError: 文件超过 50MB
        UnsupportedFormatError: 不支持的文件格式
        DecodeError: 解码或解析失败
        ReaderError: 第三方依赖缺失等
    """
    p = _validate_path(path)
    reader = _resolve_reader(p)
    text, _ = reader(p)
    return text


def read_file(path: str | Path) -> ReadResult:
    """
    读取文件并返回完整结果（含元数据）。
    参数:
        path: 文件路径，支持 str 或 Path 对象
    返回:
        ReadResult: 包含 text（纯文本）和 meta（元数据）
    异常:
        同 read()
    """
    p = _validate_path(path)
    reader = _resolve_reader(p)
    text, meta = reader(p)
    return ReadResult(text=text, meta=meta)


def supported_formats() -> list[str]:
    """
    返回当前支持的文件扩展名列表（按字母排序）。
    返回:
        list[str]: 扩展名列表，如 ['.docx', '.htm', '.html', '.markdown', '.md', '.pdf', '.txt']
    """
    return sorted(_READERS.keys())


def register_reader(extension: str, reader_fn: Callable[[Path], tuple[str, ReadMeta]]) -> None:
    """
    注册自定义文件读取器，用于扩展新格式。
    参数:
        extension: 文件扩展名（带或不带点号均可，如 '.epub' 或 'epub'）
        reader_fn: 读取器函数，签名 (Path) -> tuple[str, ReadMeta]
    """
    ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
    _READERS[ext] = reader_fn
