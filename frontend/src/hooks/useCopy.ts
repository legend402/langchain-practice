import { useState, useCallback } from "react";

/**
 * 复制文本到剪贴板的 hook，兼容 HTTP 非安全环境
 * @returns [copied, handleCopy] - copied 表示是否已复制，handleCopy 接受要复制的文本
 */
export function useCopy() {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback((text: string) => {
    const done = () => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    };

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(() => fallback(text, done));
    } else {
      fallback(text, done);
    }
  }, []);

  return [copied, handleCopy] as const;
}

function fallback(text: string, onSuccess: () => void) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.cssText = "position:fixed;left:-9999px;opacity:0";
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand("copy");
    onSuccess();
  } catch {
    /* ignore */
  }
  document.body.removeChild(ta);
}
