import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

/**
 * 登录页面：提供邮箱/用户名和密码登录表单
 */
export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [loginField, setLoginField] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login({ login: loginField, password });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="glass-card w-full max-w-md p-8">
      <h1 className="text-2xl font-semibold text-ink-100 mb-6 text-center">登录</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm text-ink-400 mb-1">邮箱 / 用户名</label>
          <input
            type="text"
            value={loginField}
            onChange={(e) => setLoginField(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl glass-input text-ink-100 outline-none focus:ring-2 focus:ring-accent/30 text-sm"
            placeholder="输入邮箱或用户名"
            required
          />
        </div>
        <div>
          <label className="block text-sm text-ink-400 mb-1">密码</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl glass-input text-ink-100 outline-none focus:ring-2 focus:ring-accent/30 text-sm"
            placeholder="输入密码"
            required
          />
        </div>
        {error && <p className="text-sm text-red-500 text-center">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2.5 rounded-xl bg-accent text-white font-medium text-sm hover:bg-accent-light transition-colors disabled:opacity-50 cursor-pointer"
        >
          {submitting ? "登录中..." : "登录"}
        </button>
      </form>
      <p className="text-sm text-ink-400 text-center mt-4">
        还没有账号？{" "}
        <Link to="/register" className="text-accent hover:underline">
          注册
        </Link>
      </p>
    </div>
  );
}
