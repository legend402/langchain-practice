<template>
  <div class="flex flex-col h-screen">
    <header class="bg-dark-card border-b border-dark-border flex items-center gap-8 px-8 h-14 shrink-0 max-md:px-4 max-md:gap-4">
      <h1 class="text-lg font-bold text-text-primary whitespace-nowrap max-md:text-[0.95rem]">LangChain 实验平台</h1>
      <nav class="flex items-center gap-1 h-full">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-2 px-4 py-2 rounded-md text-text-muted text-sm transition-all duration-200 h-9 hover:text-text-secondary hover:bg-white/5 [&.nav-link--active]:text-accent-cyan [&.nav-link--active]:bg-accent-blue/15 [&.nav-link--active]:font-medium [&.nav-link--active]:hover:bg-accent-blue/20 max-md:px-3 max-md:text-[0.85rem] max-md:[&_span:last-child]:hidden"
          active-class="nav-link--active"
        >
          <span class="text-base">{{ item.icon }}</span>
          <span>{{ item.title }}</span>
        </router-link>
      </nav>
    </header>
    <main class="flex-1 overflow-y-auto">
      <router-view />
    </main>
  </div>
</template>

<script setup>
/**
 * 默认布局组件
 * 包含顶部导航栏和主内容区域
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const navItems = computed(() => {
  const routes = router.options.routes
  const layoutRoute = routes.find(r => r.path === '/')
  if (!layoutRoute || !layoutRoute.children) return []
  return layoutRoute.children
    .filter(r => r.meta)
    .map(r => ({
      path: r.path === '' ? '/' : `/${r.path}`,
      title: r.meta.title,
      icon: r.meta.icon,
    }))
})
</script>
