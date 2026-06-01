import { Outlet } from "react-router-dom";

/**
 * 认证页面布局：居中全屏布局，供登录和注册页面共用
 */
export default function AuthLayout() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Outlet />
    </div>
  );
}
