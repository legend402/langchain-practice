import { useState, useRef, useEffect } from "react";
import { ArrowUp, Square, Paperclip, X, Loader2 } from "lucide-react";
import type { FileUpload } from "../types/knowledge";
import { uploadApi } from "../api/uploadApi";

interface SearchFormProps {
  onSubmit: (query: string) => void;
  onStop: () => void;
  loading: boolean;
  attachments?: FileUpload[];
  onAddAttachment?: (file: FileUpload) => void;
  onRemoveAttachment?: (fileId: string) => void;
}

const MAX_ROWS = 6;
const LINE_HEIGHT = 24;

/**
 * 自动增长的输入框组件，支持文件附件上传
 * @param onSubmit 提交回调
 * @param loading 是否加载中
 * @param attachments 当前已附加的文件列表
 * @param onAddAttachment 添加附件回调
 * @param onRemoveAttachment 移除附件回调
 */
export default function SearchForm({
  onSubmit,
  onStop,
  loading,
  attachments = [],
  onAddAttachment,
  onRemoveAttachment,
}: SearchFormProps) {
  const [input, setInput] = useState("");
  const [uploading, setUploading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const composingRef = useRef(false);

  /**
   * 根据内容自动调整输入框高度
   */
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const maxHeight = LINE_HEIGHT * MAX_ROWS;
    el.style.height = Math.min(el.scrollHeight, maxHeight) + "px";
  }, [input]);

  /**
   * 处理文件选择事件，上传文件并回调
   * @param e - 文件输入变化事件
   */
  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !onAddAttachment) return;
    setUploading(true);
    try {
      const result = await uploadApi.uploadFile(file);
      onAddAttachment(result);
    } catch {
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  /**
   * 移除附件并删除已上传的文件
   * @param fileId - 文件 ID
   */
  function handleRemove(fileId: string) {
    uploadApi.deleteFile(fileId).catch(() => {});
    onRemoveAttachment?.(fileId);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    onSubmit(trimmed);
    setInput("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !composingRef.current) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="glass-card relative px-5 py-4">
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {attachments.map((f) => (
              <span
                key={f.id}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs text-ink-400 bg-white/10"
              >
                {f.file_name}
                <button
                  type="button"
                  onClick={() => handleRemove(f.id)}
                  className="text-ink-600 hover:text-ink-100 transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onCompositionStart={() => { composingRef.current = true; }}
          onCompositionEnd={() => { composingRef.current = false; }}
          onKeyDown={handleKeyDown}
          placeholder="输入你要总结的知识点..."
          disabled={loading}
          rows={3}
          className="w-full bg-transparent text-ink-100 text-base placeholder:text-ink-600 focus:outline-none disabled:opacity-50 resize-none leading-7 scrollbar-hide pr-12"
          style={{ maxHeight: LINE_HEIGHT * MAX_ROWS + 'px', height: LINE_HEIGHT * 3 + 'px' }}
        />
        <div className="absolute right-4 bottom-4 flex items-center gap-1.5">
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || loading}
            className="text-ink-400 hover:text-ink-100 transition-colors disabled:opacity-40"
          >
            {uploading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Paperclip className="w-5 h-5" />
            )}
          </button>
          <button
            type={loading ? "button" : "submit"}
            disabled={!loading && !input.trim()}
            onClick={loading ? (e) => { e.preventDefault(); onStop(); } : undefined}
            className={`w-9 h-9 rounded-full flex items-center justify-center text-white transition-colors ${loading ? "bg-red-500 hover:bg-red-600" : "bg-accent hover:bg-accent-light disabled:opacity-40 disabled:cursor-not-allowed"}`}
          >
            {loading ? (
              <Square className="w-4 h-4 fill-white" />
            ) : (
              <ArrowUp className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
