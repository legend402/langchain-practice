import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

/**
 * 注册页面：提供邮箱、用户名、密码注册表单
 */
export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [userName, setUserName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("两次密码不一致");
      return;
    }
    if (password.length < 8) {
      setError("密码至少 8 位");
      return;
    }
    setSubmitting(true);
    try {
      await register({ email, user_name: userName, password });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "注册失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="glass-card w-full max-w-md p-8">
      <h1 className="text-2xl font-semibold text-ink-100 mb-6 text-center">注册</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm text-ink-400 mb-1">邮箱</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl glass-input text-ink-100 outline-none focus:ring-2 focus:ring-accent/30 text-sm"
            placeholder="输入邮箱"
            required
          />
        </div>
        <div>
          <label className="block text-sm text-ink-400 mb-1">用户名</label>
          <input
            type="text"
            value={userName}
            onChange={(e) => setUserName(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl glass-input text-ink-100 outline-none focus:ring-2 focus:ring-accent/30 text-sm"
            placeholder="输入用户名"
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
            placeholder="至少 8 位"
            required
          />
        </div>
        <div>
          <label className="block text-sm text-ink-400 mb-1">确认密码</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl glass-input text-ink-100 outline-none focus:ring-2 focus:ring-accent/30 text-sm"
            placeholder="再次输入密码"
            required
          />
        </div>
        {error && <p className="text-sm text-red-500 text-center">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2.5 rounded-xl bg-accent text-white font-medium text-sm hover:bg-accent-light transition-colors disabled:opacity-50 cursor-pointer"
        >
          {submitting ? "注册中..." : "注册"}
        </button>
      </form>
      <p className="text-sm text-ink-400 text-center mt-4">
        已有账号？{" "}
        <Link to="/login" className="text-accent hover:underline">
          登录
        </Link>
      </p>
    </div>
  );
}
