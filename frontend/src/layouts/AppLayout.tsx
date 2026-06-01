import { Outlet } from "react-router-dom";

/**
 * 应用主布局：已认证页面的外层壳，未来可扩展侧栏等共享元素
 */
export default function AppLayout() {
  return (
    <div className="h-screen bg-background">
      <Outlet />
    </div>
  );
}
