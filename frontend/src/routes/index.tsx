import { createBrowserRouter } from "react-router-dom";
import GuestRoute from "./GuestRoute";
import ProtectedRoute from "./ProtectedRoute";
import AuthLayout from "../layouts/AuthLayout";
import AppLayout from "../layouts/AppLayout";
import LoginPage from "../pages/auth/LoginPage";
import RegisterPage from "../pages/auth/RegisterPage";
import ChatPage from "../pages/chat/ChatPage";
import NotFound from "../pages/NotFound";

/**
 * 应用路由表：定义所有路由、守卫和布局的嵌套关系
 */
export const router = createBrowserRouter([
  {
    element: <GuestRoute />,
    children: [
      {
        element: <AuthLayout />,
        children: [
          { path: "/login", element: <LoginPage /> },
          { path: "/register", element: <RegisterPage /> },
        ],
      },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [{ path: "/", element: <ChatPage /> }],
      },
    ],
  },
  {
    path: "*",
    element: <NotFound />,
  },
]);
