import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('../layouts/DefaultLayout.vue'),
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('../views/HomeView.vue'),
        meta: { title: '首页', icon: '🏠' },
      },
      {
        path: 'data-analysis',
        name: 'DataAnalysis',
        component: () => import('../views/DataAnalysis.vue'),
        meta: { title: '数据分析', icon: '📊', description: '上传CSV文件，通过AI智能体进行数据分析和可视化' },
      },
      {
        path: 'rag-knowledge',
        name: 'RAGKnowledge',
        component: () => import('../views/RAGKnowledge.vue'),
        meta: { title: 'RAG知识库', icon: '🤖', description: '基于RAG的PDF文档问答系统，上传文档后可通过AI进行智能问答' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'LangChain'} - LangChain 实验平台`
  next()
})

export default router
