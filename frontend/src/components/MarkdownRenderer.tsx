import { useState, useCallback, type ComponentPropsWithoutRef } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Copy, Check } from "lucide-react";

function CodeBlock({
  className,
  children,
  ...rest
}: ComponentPropsWithoutRef<"code"> & { children?: React.ReactNode }) {
  const match = /language-(\w+)/.exec(className ?? "");
  const code = String(children).replace(/\n$/, "");
  const isBlock = match || String(children).includes("\n");

  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [code]);

  if (!isBlock) {
    return <code className={className} {...rest}>{children}</code>;
  }

  const lang = match?.[1] ?? "text";

  return (
    <div className="md-code-wrapper">
      <div className="md-code-header">
        <span>{lang}</span>
        <button
          type="button"
          className={`md-code-copy ${copied ? "copied" : ""}`}
          onClick={handleCopy}
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "已复制" : "复制"}
        </button>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={lang}
        PreTag="div"
        customStyle={{
          margin: 0,
          borderRadius: "0 0 10px 10px",
          padding: "1em 1.2em",
          fontSize: "13px",
          lineHeight: "1.7",
          background: "#1e1e2e",
        }}
        codeTagProps={{
          style: {
            fontFamily: '"JetBrains Mono", "Fira Code", "SF Mono", Consolas, monospace',
          },
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

interface MarkdownRendererProps {
  children: string;
  className?: string;
}

export default function MarkdownRenderer({ children, className = "" }: MarkdownRendererProps) {
  return (
    <div className={`md-body ${className}`}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          code: CodeBlock as any,
        }}
      >
        {children}
      </Markdown>
    </div>
  );
}
