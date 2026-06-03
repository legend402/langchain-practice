# 文件读取工具（reader.py）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `src/utils/` 下新增 `reader.py`，支持自动识别文件类型并读取纯文本内容，覆盖 txt/md/html/pdf/docx 五种核心格式。

**Architecture:** 同步函数式 API + 分发表模式。公开入口 `read(path) -> str` 根据文件扩展名自动路由到对应的私有 reader 函数。每个 reader 返回 `(text, ReadMeta)` 元组，公开 API 按需暴露完整结果或仅文本。可选依赖通过 try/except 检测，缺失时抛出明确的安装提示。

**Tech Stack:** Python 标准库 + charset_normalizer（已装） + PyPDF2（已装） + beautifulsoup4（新增） + lxml（新增） + python-docx（新增）

---

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 修改 | `requirements.txt` | 追加 3 个新依赖 |
| 新建 | `src/utils/reader.py` | 文件读取工具（约 180 行） |

不动 `src/utils/__init__.py`，避免循环导入风险，调用方按需显式 import。

---

## 依赖说明

| 库 | 用途 | 安装状态 |
|----|------|----------|
| `charset_normalizer` | txt/md 编码检测 | 已装 |
| `PyPDF2` (3.0.1) | PDF 文本提取 | 已装（已废弃但可用） |
| `beautifulsoup4` | HTML 文本抽取 | **待装** |
| `lxml` | BS4 的后端解析器 | **待装** |
| `python-docx` | DOCX 段落+表格 | **待装** |

---

### Task 1: 安装依赖并更新 requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 安装 3 个新依赖**

Run:
```bash
pip install beautifulsoup4 lxml python-docx
```

Expected: Successfully installed beautifulsoup4, lxml, python-docx

- [ ] **Step 2: 更新 requirements.txt**

在 `requirements.txt` 末尾追加 3 行（按字母序排列）：

```
beautifulsoup4
lxml
python-docx
```

最终 `requirements.txt` 内容：

```
langchain
langchain-community
langchain-core
langchain-openai
langchain-tavily
langgraph
langgraph-checkpoint-postgres
psycopg[binary]
psycopg-pool
fastapi
pydantic
python-dotenv
rich
uvicorn[standard]
sqlmodel
alembic
asyncpg
greenlet
fastapi-fullauth[sqlmodel,redis]
beautifulsoup4
lxml
python-docx
```

- [ ] **Step 3: 提交依赖变更**

```bash
git add requirements.txt
git commit -m "chore: 添加文件读取工具所需的第三方依赖"
```

---

### Task 2: 实现 reader.py — 异常与数据结构

**Files:**
- Create: `src/utils/reader.py`

- [ ] **Step 1: 创建 reader.py，写入异常类和数据结构**

```python
"""
文件读取工具，支持自动识别文件类型并读取纯文本内容。
覆盖 txt、md、html、pdf、docx 五种核心格式。
"""

import io
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
```

- [ ] **Step 2: 暂不提交，继续 Task 3**

---

### Task 3: 实现 reader.py — 可选依赖导入

**Files:**
- Modify: `src/utils/reader.py`

- [ ] **Step 1: 在数据结构代码之后追加可选依赖导入**

```python
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
```

说明：
- `PyPDF2` 已装但已标记 deprecated，用 `from PyPDF2 import PdfReader` 而非 `pypdf`，与当前 venv 一致
- 每个 import 失败时设为 `None`，reader 函数内部检测到 `None` 后抛出带安装提示的 `ReaderError`
- `# type: ignore` 消除 mypy 对 `None` 赋值的警告

- [ ] **Step 2: 暂不提交，继续 Task 4**

---

### Task 4: 实现 reader.py — 编码检测与 txt/md reader

**Files:**
- Modify: `src/utils/reader.py`

- [ ] **Step 1: 追加编码检测和文本类 reader**

```python
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
```

- [ ] **Step 2: 暂不提交，继续 Task 5**

---

### Task 5: 实现 reader.py — HTML reader

**Files:**
- Modify: `src/utils/reader.py`

- [ ] **Step 1: 追加 HTML reader**

```python
_HTML_STRIP_TAGS = frozenset({"script", "style", "noscript", "header", "footer", "nav"})


def _read_html(path: Path) -> tuple[str, ReadMeta]:
    """
    读取 HTML 文件，移除脚本和样式标签后提取纯文本。
    需要 beautifulsoup4 和 lxml。
    """
    if BeautifulSoup is None:
        raise ReaderError("读取 HTML 需要 beautifulsoup4 和 lxml，请运行：pip install beautifulsoup4 lxml")
    raw = path.read_bytes()
    enc = _detect_encoding(raw)
    html = raw.decode(enc, errors="replace")
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(_HTML_STRIP_TAGS):
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
```

说明：
- 剥离 `script/style/noscript/header/footer/nav` 六类标签
- `get_text(separator="\n", strip=True)` 后再按行去空行，避免大量连续换行
- 未装 BS4 时抛出带安装命令的 `ReaderError`

- [ ] **Step 2: 暂不提交，继续 Task 6**

---

### Task 6: 实现 reader.py — PDF reader

**Files:**
- Modify: `src/utils/reader.py`

- [ ] **Step 1: 追加 PDF reader**

```python
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
```

说明：
- `is_encrypted` 为 `True` 时直接抛 `DecodeError`，不尝试 `decrypt("")`
- 跳过空页（`page_text.strip()` 为空时不拼入结果）
- 单页解析失败记入 `warnings` 而不中断整体流程

- [ ] **Step 2: 暂不提交，继续 Task 7**

---

### Task 7: 实现 reader.py — DOCX reader

**Files:**
- Modify: `src/utils/reader.py`

- [ ] **Step 1: 追加 DOCX reader**

```python
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
    for element in doc.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
        if tag == "p":
            text = element.text_content().strip() if hasattr(element, "text_content") else ""
            if text:
                parts.append(text)
        elif tag == "tbl":
            table_elements = doc.tables
            for table in table_elements:
                if table._element is element:
                    for row in table.rows:
                        cells = [cell.text.strip() for cell in row.cells]
                        parts.append(" | ".join(cells))
                    break
    text = "\n".join(parts)
    meta = ReadMeta(
        path=str(path),
        format="docx",
        size_bytes=path.stat().st_size,
    )
    return text, meta
```

说明：
- 遍历 `doc.element.body` 保持段落和表格的原始顺序（直接迭代 `doc.paragraphs` + `doc.tables` 会丢失交替顺序）
- 表格行用 ` | ` 分隔各单元格文本
- 未装 python-docx 时抛出带安装命令的 `ReaderError`

- [ ] **Step 2: 暂不提交，继续 Task 8**

---

### Task 8: 实现 reader.py — 分发表与公共 API

**Files:**
- Modify: `src/utils/reader.py`

- [ ] **Step 1: 追加分发表、公共入口和扩展接口**

```python
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
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在：{p}")
    size = p.stat().st_size
    if size > _MAX_FILE_SIZE_BYTES:
        limit_mb = _MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise FileSizeLimitError(f"文件 {p} 大小 {size} 字节，超过 {limit_mb}MB 限制")
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
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在：{p}")
    size = p.stat().st_size
    if size > _MAX_FILE_SIZE_BYTES:
        limit_mb = _MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise FileSizeLimitError(f"文件 {p} 大小 {size} 字节，超过 {limit_mb}MB 限制")
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
```

- [ ] **Step 2: 暂不提交，继续 Task 9**

---

### Task 9: 验证与提交

**Files:**
- `src/utils/reader.py` (只读验证)

- [ ] **Step 1: 验证模块可正常导入**

Run:
```bash
python -c "from src.utils.reader import read, read_file, supported_formats, register_reader, ReadResult, ReadMeta, ReaderError, UnsupportedFormatError, FileSizeLimitError, DecodeError; print('导入成功'); print('支持格式:', supported_formats())"
```

Expected:
```
导入成功
支持格式: ['.docx', '.htm', '.html', '.markdown', '.md', '.pdf', '.txt']
```

- [ ] **Step 2: 验证读取一个真实 txt 文件**

创建临时测试文件并验证：

Run:
```bash
python -c "
from src.utils.reader import read, read_file
import tempfile, os

with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write('Hello World\n测试中文')
    tmp = f.name

text = read(tmp)
print('read() =>', repr(text))

result = read_file(tmp)
print('read_file().text =>', repr(result.text))
print('meta.format =>', result.meta.format)
print('meta.encoding =>', result.meta.encoding)
print('meta.size_bytes =>', result.meta.size_bytes)

os.unlink(tmp)
print('OK')
"
```

Expected:
```
read() => 'Hello World\n测试中文'
read_file().text => 'Hello World\n测试中文'
meta.format => 'txt'
meta.encoding => 'utf-8'
meta.size_bytes => 22
OK
```

- [ ] **Step 3: 验证不支持的格式报错**

Run:
```bash
python -c "
from src.utils.reader import read, UnsupportedFormatError
import tempfile, os

with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
    f.write(b'test')
    tmp = f.name

try:
    read(tmp)
except UnsupportedFormatError as e:
    print(f'Caught: {e}')
finally:
    os.unlink(tmp)
"
```

Expected:
```
Caught: 不支持的文件格式：.xyz。当前支持：.docx, .htm, .html, .markdown, .md, .pdf, .txt
```

- [ ] **Step 4: 提交**

```bash
git add src/utils/reader.py
git commit -m "feat: 添加文件读取工具 reader.py，支持 txt/md/html/pdf/docx"
```

---

## 自检清单

- [x] **Spec 覆盖**：txt、md、html、pdf、docx 五种格式均有对应 reader
- [x] **无占位符**：所有步骤包含完整代码，无 TBD/TODO
- [x] **类型一致性**：所有 reader 签名统一为 `(Path) -> tuple[str, ReadMeta]`，公共 API 类型签名在 Task 8 中定义并在后续使用
- [x] **DRY**：txt/md/markdown 共享 `_read_text_like`；`_resolve_reader` 抽取路径/大小检查逻辑避免 `read` 和 `read_file` 重复
- [x] **YAGNI**：未加入 csv/json/xml/xlsx/pptx/epub 等用户未确认的格式，但预留了 `register_reader` 扩展点
- [x] **可选依赖优雅降级**：BS4/PDF/DOCX 未安装时抛出带 `pip install` 提示的 `ReaderError`，不会 ImportError
