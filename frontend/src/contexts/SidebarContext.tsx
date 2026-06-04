import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface SidebarContextValue {
  collapsed: boolean;
  toggle: () => void;
}

const SidebarContext = createContext<SidebarContextValue | null>(null);

/**
 * 侧边栏状态 Context，提供折叠/展开控制
 */
export function SidebarProvider({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(() => window.innerWidth < 768);
  const toggle = useCallback(() => setCollapsed((v) => !v), []);

  return (
    <SidebarContext.Provider value={{ collapsed, toggle }}>
      {children}
    </SidebarContext.Provider>
  );
}

/**
 * 获取侧边栏状态，必须在 SidebarProvider 内使用
 */
export function useSidebar(): SidebarContextValue {
  const ctx = useContext(SidebarContext);
  if (!ctx) throw new Error("useSidebar 必须在 SidebarProvider 内使用");
  return ctx;
}
