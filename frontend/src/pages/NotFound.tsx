import { Link } from "react-router-dom";

/**
 * 404 页面：显示错误提示和返回首页链接
 */
export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-ink-400 mb-4">404</h1>
        <p className="text-ink-400 mb-6">页面不存在</p>
        <Link
          to="/"
          className="px-6 py-2.5 rounded-xl bg-accent text-white font-medium text-sm hover:bg-accent-light transition-colors"
        >
          返回首页
        </Link>
      </div>
    </div>
  );
}
