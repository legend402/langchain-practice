# 前端对话系统性能优化整改方案

> 审查日期: 2026-06-09
> 涉及文件: useAgentChat.ts, agentApi.ts, httpClient.ts, MessageList.tsx, MarkdownRenderer.tsx, ChatPage.tsx, AgentChatContext.tsx 等

## 问题总览

| 优先级 | 问题 | 影响 | 状态 |
|--------|------|------|------|
| P0 | flushChunks O(N*M) 数组拷贝 | 流式输出卡顿 | 待修复 |
| P0 | 消息携带全量 AgentState | 内存 + diff 开销 | 待修复 |
| P0 | Markdown 每帧重解析 | 流式输出卡顿 | 待修复 |
| P1 | currentState 触发链路重渲染 | 高频无用渲染 | 待修复 |
| P1 | 流式自动滚动失效 | UX 问题 | 待修复 |
| P1 | glass-card hover 重绘 | 滚动卡顿 | 待修复 |
| P1 | 加载动画过度 | 合成器负担 | 待修复 |
| S0 | Context 粒度过粗 | 无用渲染 | 待修复 |
| S0 | useAgentChat 过重 | 可维护性 | 待修复 |
| S0 | handleMessage 重复分支 | 可维护性 | 待修复 |
| S0 | 常量重复定义 | 一致性风险 | 待修复 |
| S1 | SSE 无重连/超时 | 健壮性 | 待修复 |
| S1 | abort 竞态 | 偶现 bug | 待修复 |
| S2 | BASE_URL 硬编码 | 部署问题 | 待修复 |
| S2 | 无 Error Boundary | 白屏风险 | 待修复 |
| S2 | uuid 碰撞风险 | React key 冲突 | 待修复 |

## 实施路径

### 第一阶段：快速见效
1. 修复 flushChunks 算法（线性拷贝）
2. 消息不再携带全量 AgentState（只存增量）
3. 流式自动滚动修复
4. MarkdownRenderer memo + 流式降级渲染
5. 加载动画简化
6. uuid 改进

### 第二阶段：核心优化
7. currentState 从 MessageList 剥离
8. 消息列表虚拟滚动（可选）
9. glass-card 性能优化

### 第三阶段：架构改善
10. 拆分 Context
11. 统一常量定义
12. SSE 连接健壮性
13. Error Boundary
