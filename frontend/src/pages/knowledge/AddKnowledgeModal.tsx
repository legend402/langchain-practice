import { useState } from "react";
import Modal from "../../components/Modal";
import FileUploader from "../../components/FileUploader";
import { knowledgeApi } from "../../api/knowledgeApi";
import { uploadApi } from "../../api/uploadApi";
import type { FileUpload } from "../../types/knowledge";

interface AddKnowledgeModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

type InputMode = "manual" | "upload";

/**
 * 添加知识条目模态框
 * @param open 是否显示
 * @param onClose 关闭回调
 * @param onSuccess 创建成功回调
 */
export default function AddKnowledgeModal({ open, onClose, onSuccess }: AddKnowledgeModalProps) {
  const [title, setTitle] = useState("");
  const [mode, setMode] = useState<InputMode>("manual");
  const [content, setContent] = useState("");
  const [files, setFiles] = useState<FileUpload[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function resetForm() {
    setTitle("");
    setContent("");
    setFiles([]);
    setMode("manual");
    setError(null);
  }

  function handleClose() {
    resetForm();
    onClose();
  }

  function handleFileUpload(file: FileUpload) {
    setFiles((prev) => [...prev, file]);
  }

  function handleFileRemove(fileId: string) {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  }

  async function handleSubmit() {
    if (!title.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "manual") {
        await knowledgeApi.createEntry({ title: title.trim(), content: content.trim() });
      } else {
        const uploadedFile = files[0];
        if (!uploadedFile) {
          setError("请上传文件");
          setSubmitting(false);
          return;
        }
        await knowledgeApi.createEntry({
          title: title.trim(),
          file_id: uploadedFile.id,
          source_type: "file",
        });
      }
      onSuccess();
      handleClose();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "创建失败";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmit = title.trim() && !submitting;

  return (
    <Modal open={open} onClose={handleClose} title="添加知识" size="md">
      <div className="space-y-4">
        <div>
          <label className="block text-sm text-ink-400 mb-1.5">标题</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="输入知识标题"
            className="w-full glass-card px-3 py-2 text-ink-100 placeholder:text-ink-600 outline-none focus:ring-1 focus:ring-accent/50"
          />
        </div>

        <div>
          <label className="block text-sm text-ink-400 mb-1.5">内容来源</label>
          <div className="flex gap-1 p-1 glass-card rounded-xl">
            <button
              onClick={() => setMode("manual")}
              className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                mode === "manual"
                  ? "bg-accent text-white"
                  : "text-ink-400 hover:bg-white/40"
              }`}
            >
              手动输入
            </button>
            <button
              onClick={() => setMode("upload")}
              className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                mode === "upload"
                  ? "bg-accent text-white"
                  : "text-ink-400 hover:bg-white/40"
              }`}
            >
              上传文件
            </button>
          </div>
        </div>

        {mode === "manual" ? (
          <div>
            <label className="block text-sm text-ink-400 mb-1.5">内容</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="输入知识内容..."
              className="w-full glass-card px-3 py-2 text-ink-100 placeholder:text-ink-600 outline-none focus:ring-1 focus:ring-accent/50 min-h-[120px] resize-y"
            />
          </div>
        ) : (
          <FileUploader
            onUploadComplete={handleFileUpload}
            onRemove={handleFileRemove}
            files={files}
          />
        )}

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full py-2.5 rounded-xl bg-accent text-white font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
        >
          {submitting ? "提交中..." : "添加"}
        </button>
      </div>
    </Modal>
  );
}
