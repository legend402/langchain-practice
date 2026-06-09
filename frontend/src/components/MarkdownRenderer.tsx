import { useState, useCallback, useEffect, useRef, useId, memo, type ComponentPropsWithoutRef } from "react";
import { MarkdownHooks } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { OverlayScrollbarsComponent } from "overlayscrollbars-react";
import "overlayscrollbars/overlayscrollbars.css";
import { useCopy } from "../hooks/useCopy";
import {
  Copy,
  Check,
  Download,
  Maximize2,
  Minimize2,
  Code2,
  GitBranch,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  securityLevel: "loose",
});

let mermaidRenderCount = 0;

function MermaidBlock({ code }: { code: string }) {
  const svgWrapRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const osRef = useRef<React.ComponentRef<typeof OverlayScrollbarsComponent>>(null);
  const [svg, setSvg] = useState<string>("");
  const [tab, setTab] = useState<"chart" | "code">("chart");
  const [copied, handleCopy] = useCopy();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [zoom, setZoom] = useState(100);
  const [naturalSize, setNaturalSize] = useState<{ w: number; h: number } | null>(null);
  const scopeId = useId();

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(async () => {
      const container = document.createElement("div");
      container.style.cssText = "position:fixed;left:-9999px;opacity:0;pointer-events:none";
      document.body.appendChild(container);
      try {
        const id = `mermaid-${scopeId.replace(/:/g, "")}-${++mermaidRenderCount}`;
        const { svg: renderedSvg } = await mermaid.render(id, code, container);
        if (!cancelled) {
          setSvg(renderedSvg);
        }
      } catch {
      } finally {
        container.remove();
        if (!cancelled) {
          const errEl = document.querySelector(`#d${scopeId.replace(/:/g, "")}`);
          if (errEl) errEl.remove();
        }
      }
    }, 300);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [code, scopeId]);

  useEffect(() => {
    if (!svg || !svgWrapRef.current) return;
    const svgEl = svgWrapRef.current.querySelector("svg");
    if (!svgEl) return;
    let w = svgEl.clientWidth || svgEl.getBoundingClientRect().width || 400;
    let h = svgEl.clientHeight || svgEl.getBoundingClientRect().height || 200;
    const vb = svgEl.getAttribute("viewBox");
    if (vb) {
      const parts = vb.split(/[\s,]+/).map(Number);
      if (parts.length === 4 && parts[2] > 0 && parts[3] > 0) {
        if (!svgEl.getAttribute("width") || !svgEl.getAttribute("height")) {
          w = parts[2];
          h = parts[3];
        }
      }
    }
    svgEl.style.width = w + "px";
    svgEl.style.height = h + "px";
    setNaturalSize({ w, h });
  }, [svg]);

  useEffect(() => {
    const osInstance = osRef.current?.osInstance();
    if (!osInstance || !naturalSize) return;
    const viewport = osInstance.elements().viewport;
    const sw = Math.max(naturalSize.w * zoom / 100, viewport.clientWidth);
    const sh = Math.max(naturalSize.h * zoom / 100, viewport.clientHeight);
    requestAnimationFrame(() => {
      viewport.scrollLeft = (sw - viewport.clientWidth) / 2;
      viewport.scrollTop = (sh - viewport.clientHeight) / 2;
    });
  }, [zoom, naturalSize]);

  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
    const handler = () => setIsFullscreen(!!document.fullscreenElement && document.fullscreenElement === wrapper);
    wrapper.addEventListener("fullscreenchange", handler);
    return () => wrapper.removeEventListener("fullscreenchange", handler);
  }, []);

  const handleCopyCode = useCallback(() => handleCopy(code), [handleCopy, code]);

  const handleDownload = useCallback(() => {
    if (!svg) return;
    const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "mermaid-diagram.svg";
    a.click();
    URL.revokeObjectURL(url);
  }, [svg]);

  const handleFullscreen = useCallback(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      wrapper.requestFullscreen();
    }
  }, []);

  const handleZoomIn = useCallback(() => setZoom((z) => Math.min(z + 20, 300)), []);
  const handleZoomOut = useCallback(() => setZoom((z) => Math.max(z - 20, 40)), []);
  const handleZoomReset = useCallback(() => setZoom(100), []);

  return (
    <div ref={wrapperRef} className="mermaid-wrapper">
      <div className="mermaid-toolbar">
        <div className="mermaid-tabs">
          <button
            type="button"
            className={`mermaid-tab ${tab === "chart" ? "active" : ""}`}
            onClick={() => setTab("chart")}
          >
            <GitBranch className="w-3.5 h-3.5" />
            图表
          </button>
          <button
            type="button"
            className={`mermaid-tab ${tab === "code" ? "active" : ""}`}
            onClick={() => setTab("code")}
          >
            <Code2 className="w-3.5 h-3.5" />
            代码
          </button>
        </div>
        <div className="mermaid-actions">
          <button type="button" className="mermaid-action-btn" onClick={handleCopyCode} title="复制代码">
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <div className="mermaid-divider" />
          <button type="button" className="mermaid-action-btn" onClick={handleZoomOut} title="缩小" disabled={zoom <= 40}>
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            className="mermaid-action-btn mermaid-zoom-label"
            onClick={handleZoomReset}
            title="重置缩放"
          >
            {zoom}%
          </button>
          <button type="button" className="mermaid-action-btn" onClick={handleZoomIn} title="放大" disabled={zoom >= 300}>
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <div className="mermaid-divider" />
          <button
            type="button"
            className="mermaid-action-btn"
            onClick={handleDownload}
            title="下载 SVG"
            disabled={!svg}
          >
            <Download className="w-3.5 h-3.5" />
            <span>下载</span>
          </button>
          <button type="button" className="mermaid-action-btn" onClick={handleFullscreen} title="全屏查看">
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            <span>{isFullscreen ? "退出" : "全屏"}</span>
          </button>
        </div>
      </div>
      <div className="mermaid-content">
        {tab === "chart" ? (
          <OverlayScrollbarsComponent
            ref={osRef}
            defer
            options={{ scrollbars: { autoHide: "leave", autoHideDelay: 300 } }}
            className="mermaid-chart"
            style={naturalSize ? { height: naturalSize.h + 76 } : undefined}
          >
            {svg ? (
              <div
                className="mermaid-chart-spacer"
                style={
                  naturalSize
                    ? { minWidth: '100%', width: naturalSize.w * zoom / 100, height: "100%" }
                    : undefined
                }
              >
                <div
                  ref={svgWrapRef}
                  className="mermaid-chart-inner"
                  style={{
                    transform: `scale(${zoom / 100})`,
                    transformOrigin: "center center",
                    width: naturalSize?.w,
                    height: naturalSize?.h,
                  }}
                >
                  <div dangerouslySetInnerHTML={{ __html: svg }} />
                </div>
              </div>
            ) : null}
          </OverlayScrollbarsComponent>
        ) : (
          <SyntaxHighlighter
            style={oneDark}
            language="mermaid"
            PreTag="div"
            customStyle={{
              margin: 0,
              borderRadius: "10px",
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
        )}
      </div>
    </div>
  );
}

const CodeBlock = memo(function CodeBlock({
  className,
  children,
  ...rest
}: ComponentPropsWithoutRef<"code"> & { children?: React.ReactNode }) {
  const match = /language-(\w+)/.exec(className ?? "");
  const code = String(children).replace(/\n$/, "");
  const isBlock = match || String(children).includes("\n");
  const [copied, handleCopyText] = useCopy();
  const handleCopy = useCallback(() => handleCopyText(code), [handleCopyText, code]);

  if (!isBlock) {
    return <code className={className} {...rest}>{children}</code>;
  }

  const lang = match?.[1] ?? "text";

  if (lang === "mermaid") {
    return <MermaidBlock code={code} />;
  }

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
});

interface MarkdownRendererProps {
  children: string;
  className?: string;
  streaming?: boolean;
}

/**
 * Markdown 渲染组件
 * streaming 模式下跳过重计算组件，等流式结束后再完整渲染
 */
const MarkdownRenderer = memo(function MarkdownRenderer({ children, className = "", streaming }: MarkdownRendererProps) {
  return (
    <div className={`md-body ${className}`}>
      <MarkdownHooks
        remarkPlugins={[remarkGfm]}
        components={streaming ? {} : { code: CodeBlock as any }}
      >
        {children}
      </MarkdownHooks>
    </div>
  );
});

export default MarkdownRenderer;
