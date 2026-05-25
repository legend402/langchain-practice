import { Sparkles } from "lucide-react";

export default function Header() {
  return (
    <header className="py-6 px-4 text-center">
      <div className="flex items-center justify-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <h1 className="text-xl font-semibold text-ink-100 tracking-tight">
          知识点总结 Agent
        </h1>
      </div>
      <p className="text-sm text-ink-400">
        输入知识点问题，AI 自动搜索、分析、总结
      </p>
    </header>
  );
}
