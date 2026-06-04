# 侧边栏提升到 AppLayout 设计文档

## 背景

当前 `SessionSidebar` 仅在 `ChatPage` 中渲染，切换到知识库页面后侧边栏消失，用户无法导航回聊天。需要将侧边栏提升到布局层，使所有认证页面共享。

## 方案

将 `SessionSidebar` 从 `ChatPage` 移到 `AppLayout`，所有认证页面（聊天、知识库）共享侧边栏。侧边栏始终显示会话列表和导航入口。

## 布局结构

```
AppLayout
├── SessionSidebar（左侧固定，280px）
│   ├── 顶部：新建会话按钮 + 折叠按钮
│   ├── 导航菜单：聊天 / 知识库（当前页高亮）
│   ├── 会话列表（可滚动）
│   └── 底部：用户信息 + 退出
├── 主内容区（<Outlet />）
│   ├── /         → ChatPage（仅消息列表 + 输入框）
│   └── /knowledge → KnowledgePage（移除独立 header）
└── 折叠时的浮动展开按钮
```

## 改动清单

### 1. AppLayout 添加侧边栏

- 引入 `SessionSidebar` 和折叠/展开状态管理
- 布局改为侧边栏 + `<Outlet />` 并排结构
- 移动端保持 overlay 模式

### 2. SessionSidebar 调整

- 导航菜单从单个"知识库"链接改为聊天/知识库两个菜单项
- 当前路由高亮对应菜单项（用 `useLocation` 判断）
- 移除知识库入口的单独按钮样式，改为统一导航菜单

### 3. ChatPage 瘦身

- 移除 `SessionSidebar` 渲染
- 移除侧边栏折叠状态管理（由 AppLayout 接管）
- 只保留消息列表和输入框

### 4. KnowledgePage 适配

- 移除独立的顶部 header（导航由侧边栏负责）
- 内容区适配侧边栏展开时的 `margin-left`
- 保留搜索栏和卡片列表等内容

### 5. 侧边栏状态管理

- 折叠/展开状态由 `AppLayout` 管理
- 通过 `SidebarContext` 向子组件提供状态（可选，视需要）
- 移动端默认折叠，桌面端默认展开

## 不涉及的改动

- 会话列表的数据获取逻辑不变
- 侧边栏的 CSS 动画和响应式逻辑保持现有实现
- 路由结构不变，只是页面组件的职责调整
