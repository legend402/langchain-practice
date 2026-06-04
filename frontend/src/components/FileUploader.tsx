import { useState, useRef, useMemo } from "react";
import { FileUp, X, Loader2 } from "lucide-react";
import { uploadApi } from "../api/uploadApi";
import type { FileUpload } from "../types/knowledge";

const ALLOWED_EXTENSIONS = [".txt", ".md", ".html", ".pdf", ".docx"];

interface FileUploaderProps {
  onUploadComplete: (file: FileUpload) => void;
  onRemove: (fileId: string) => void;
  files: FileUpload[];
}

/**
 * 文件上传组件，支持拖拽和点击上传
 * @param onUploadComplete 上传成功回调
 * @param onRemove 删除文件回调
 * @param files 已上传文件列表
 */
export default function FileUploader({
  onUploadComplete,
  onRemove,
  files,
}: FileUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const acceptStr = useMemo(() => ALLOWED_EXTENSIONS.join(","), []);
  const displayTypes = useMemo(() => ALLOWED_EXTENSIONS.join("、"), []);

  async function handleFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    const file = fileList[0];
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError(`不支持的文件格式，仅支持 ${displayTypes}`);
      setTimeout(() => setError(null), 3000);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const result = await uploadApi.uploadFile(file);
      onUploadComplete(result);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "上传失败";
      setError(message);
      setTimeout(() => setError(null), 3000);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
  }

  async function handleRemove(fileId: string) {
    onRemove(fileId);
    try {
      await uploadApi.deleteFile(fileId);
    } catch {
      // ignore server-side cleanup errors
    }
  }

  return (
    <div className="space-y-3">
      <div
        onClick={() => !uploading && inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className={`border-2 border-dashed border-white/30 rounded-xl p-6 text-center transition-colors ${
          uploading ? "opacity-50 cursor-not-allowed" : "hover:border-accent hover:bg-accent-bg/20 cursor-pointer"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={acceptStr}
          onChange={(e) => handleFiles(e.target.files)}
          className="hidden"
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="w-8 h-8 text-accent animate-spin" />
            <p className="text-ink-400 text-sm">上传中...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <FileUp className="w-8 h-8 text-ink-400" />
            <p className="text-ink-400 text-sm">拖拽文件到此处，或点击选择文件</p>
            <p className="text-ink-600 text-xs">支持 {displayTypes}</p>
          </div>
        )}
      </div>

      {error && (
        <p className="text-red-400 text-sm">{error}</p>
      )}

      {files.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {files.map((file) => (
            <span
              key={file.id}
              className="glass-card inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-ink-400"
            >
              {file.file_name}
              <button
                onClick={() => handleRemove(file.id)}
                className="text-ink-600 hover:text-ink-100 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
