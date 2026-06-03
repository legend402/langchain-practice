from dataclasses import dataclass
from typing import Optional


@dataclass
class Chunk:
  text: str
  index: str

def chunk_text(content: str, title: str, chunk_size: Optional[int] = 800, overlap: Optional[int] = 200) -> list[Chunk]:
  """
    递归字符分块器。
    将 title + content 按段落、行、字符优先级分割，每个 chunk 开头拼接 title。
    参数:
        content: 待分块的原始文本
        title: 知识标题，拼接到每个 chunk 开头
        chunk_size: 每块最大字符数
        overlap: 相邻块重叠字符数
    返回:
        Chunk 列表，包含 text 和 index
  """
  full_text = f"{title}\n\n{content}" if title else content
  if len(full_text) <= chunk_size:
    return [Chunk(text=full_text, index=0)]
  
  chunks: list[str] = []
  _recursive_split(full_text, chunk_size, overlap, chunks)
  result: list[Chunk] = []
  for i, text in enumerate(chunks):
    result.append(Chunk(text=text, index=i))
  return result

def _recursive_split(text: str, chunk_size: int, overlap: int, chunks: list[str]) -> None:
  """
    递归分割文本。优先按 \\n\\n 分，再按 \\n 分，最后按字符分。
  """
  if len(text) < chunk_size:
    chunks.append(text)
    return
  separators = ["\n\n", "\n"]
  for sep in separators:
    if sep in text:
      parts = text.split(sep)
      _merge_parts(parts, sep, chunk_size, overlap, chunks)
      return
  _split_by_chars(text, chunk_size, overlap, chunks)

def _merge_parts(parts: list[str], sep: str, chunk_size: int, overlap: int, chunks: list[str]):
  """
    将分割后的段落合并为不超过 chunk_size 的块。
  """
  current = ""
  for part in parts:
      candidate = current + sep + part if current else part
      if len(candidate) <= chunk_size:
          current = candidate
      else:
          if current:
              chunks.append(current)
          current = part
          if len(current) > chunk_size:
              _recursive_split(current, chunk_size, overlap, chunks)
              current = ""
  if current and len(current) <= chunk_size:
      chunks.append(current)
  elif current:
      _recursive_split(current, chunk_size, overlap, chunks)

def _split_by_chars(text: str, chunk_size: int, overlap: int, chunks: list[str]) -> None:
  """
    按固定字符数分割文本，步长为 chunk_size - overlap。
  """
  step = max(1, chunk_size - overlap)
  for i in range(0, len(text), step):
    chunk = text[i: i + chunk_size]
    if chunk:
       chunks.append(chunk)