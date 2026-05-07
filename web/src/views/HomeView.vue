<template>
  <div class="p-12 max-w-[900px] mx-auto max-md:p-6">
    <h1 class="text-4xl font-bold text-text-primary mb-2">LangChain 实验平台</h1>
    <p class="text-lg text-text-muted mb-10">基于 LangChain 的 AI 应用实验与测试平台</p>
    <div class="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-5">
      <router-link
        v-for="item in features"
        :key="item.path"
        :to="item.path"
        class="bg-dark-card border border-dark-border rounded-xl p-6 no-underline transition-all duration-200 cursor-pointer hover:border-accent-cyan hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(0,0,0,0.3)]"
      >
        <span class="text-4xl block mb-3">{{ item.icon }}</span>
        <h2 class="text-lg font-semibold text-text-primary mb-2">{{ item.title }}</h2>
        <p class="text-sm text-text-muted leading-relaxed">{{ item.description }}</p>
      </router-link>
    </div>
  </div>
</template>

<script setup>
/**
 * 首页视图组件
 * 展示平台功能入口卡片列表
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const features = computed(() => {
  const routes = router.options.routes
  const layoutRoute = routes.find(r => r.path === '/')
  if (!layoutRoute || !layoutRoute.children) return []
  return layoutRoute.children
    .filter(r => r.meta && r.path !== '')
    .map(r => ({
      path: `/${r.path}`,
      title: r.meta.title,
      icon: r.meta.icon,
      description: r.meta.description || '',
    }))
})
</script>
