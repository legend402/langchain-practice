"""
全局 print 美化替换模块。
在入口文件（如 main.py）顶部导入并调用 enable_rich_print()，
即可将项目内所有 print() 调用自动替换为 Rich 的 console.print()。
不影响 sys.stdout，Uvicorn/FastAPI 等第三方库的日志保持原样。
"""
import builtins
from rich.console import Console
# 保存原始 print 引用
_original_print = builtins.print
# Rich 控制台实例
_console = Console()
# 标记当前是否已启用
_is_enabled = False

def _rich_print(*args, sep=" ", end="\n", file=None, flush=False, **kwargs):
    """
    包装函数：将普通 print 的调用参数适配到 console.print。
    忽略 file 和 flush 参数（Rich Console 会自动处理），保持 sep/end 语义。
    """
    # 将 args 按 sep 拼接成一个字符串，console.print 默认 sep 也是空格
    message = sep.join(str(arg) for arg in args)
    _console.print(message, end=end, **kwargs)

def enable_rich_print():
    """启用 Rich 版本的 print（全局替换 builtins.print）。"""
    global _is_enabled
    if _is_enabled:
        return
    builtins.print = _rich_print
    _is_enabled = True

def disable_rich_print():
    """恢复原始的 print 函数。"""
    global _is_enabled
    if not _is_enabled:
        return
    builtins.print = _original_print
    _is_enabled = False

def is_rich_print_enabled() -> bool:
    """检查当前是否处于 Rich print 模式。"""
    return _is_enabled