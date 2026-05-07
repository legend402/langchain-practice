<template>
  <div class="h-full flex flex-col p-6 px-8 gap-5 overflow-hidden max-md:p-4">
    <header class="shrink-0">
      <h1 class="text-2xl font-bold text-text-primary leading-tight">数据分析系统</h1>
      <p class="text-sm text-text-dim mt-1">上传 Excel 数据，通过 AI 智能分析</p>
    </header>

    <div class="flex-1 grid grid-cols-[1fr_360px] gap-5 min-h-0 max-[900px]:grid-cols-1 max-[900px]:grid-rows-[1fr_auto]">
      <!-- 左栏：聊天 -->
      <section class="flex flex-col bg-dark-card border border-dark-border rounded-xl overflow-hidden min-h-0">
        <div class="flex items-center justify-between mb-3 px-4 pt-4">
          <h2 class="text-base font-semibold text-text-secondary">数据分析对话</h2>
          <div :class="['flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium', dataLoaded ? 'bg-accent-green/15 text-accent-green' : 'bg-accent-yellow/15 text-accent-yellow']">
            <span class="w-1.5 h-1.5 rounded-full bg-current" />
            <span>{{ dataLoaded ? '数据已加载' : '等待上传' }}</span>
          </div>
        </div>

        <div ref="chatAreaRef" class="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          <div v-if="messages.length === 0" class="flex-1 flex flex-col items-center justify-center text-text-faint gap-3">
            <svg class="w-12 h-12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
            </svg>
            <p>上传 Excel 文件后开始数据分析</p>
          </div>

          <div v-for="msg in messages" :key="msg.id" :class="['max-w-[85%] px-4 py-3 rounded-xl animate-[fadeIn_0.2s_ease]', msg.role === 'user' ? 'self-end bg-accent-blue-dark text-white' : 'self-start bg-dark-inner border border-dark-border text-text-secondary']">
            <div class="text-[0.7rem] font-semibold uppercase tracking-wider opacity-60 mb-1.5">{{ msg.role === 'user' ? '你' : 'AI' }}</div>
            <div v-if="msg.type === 'table'" class="overflow-x-auto mt-1">
              <table class="w-full border-collapse text-xs">
                <thead>
                  <tr>
                    <th v-for="col in msg.content.columns" :key="col" class="bg-dark-border text-text-muted font-semibold text-left px-3 py-2 whitespace-nowrap border-b border-dark-border-light">{{ col }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in msg.content.rows" :key="ri" class="hover:bg-accent-cyan/[0.06]">
                    <td v-for="(cell, ci) in row" :key="ci" class="px-3 py-1.5 border-b border-dark-border text-text-secondary whitespace-nowrap">{{ cell }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else-if="msg.type === 'chart'" class="flex flex-col gap-2">
              <img v-if="msg.content.imageUrl" :src="msg.content.imageUrl" alt="chart" class="max-w-full rounded-md" />
              <p v-if="msg.content.text">{{ msg.content.text }}</p>
            </div>
            <div v-else class="text-sm leading-relaxed whitespace-pre-wrap">{{ msg.content }}</div>
          </div>

          <div v-if="isLoading" class="max-w-[85%] self-start px-4 py-3 rounded-xl bg-dark-inner border border-dark-border text-text-secondary animate-[fadeIn_0.2s_ease]">
            <div class="text-[0.7rem] font-semibold uppercase tracking-wider opacity-60 mb-1.5">AI</div>
            <div class="flex gap-1 py-1">
              <span class="w-1.5 h-1.5 rounded-full bg-accent-cyan animate-[bounce_1.2s_infinite]" />
              <span class="w-1.5 h-1.5 rounded-full bg-accent-cyan animate-[bounce_1.2s_infinite_0.15s]" />
              <span class="w-1.5 h-1.5 rounded-full bg-accent-cyan animate-[bounce_1.2s_infinite_0.3s]" />
            </div>
          </div>
        </div>

        <div class="flex gap-2 px-4 py-3 border-t border-dark-border bg-dark-inner">
          <input
            v-model="queryText"
            type="text"
            class="flex-1 py-2.5 px-3.5 bg-dark-card border border-dark-border-light rounded-lg text-text-primary text-sm transition-colors duration-200 placeholder:text-text-faint focus:outline-none focus:border-[#3b82f6] disabled:opacity-50 disabled:cursor-not-allowed"
            placeholder="输入分析指令，例如：统计各列的均值"
            :disabled="!dataLoaded || isLoading"
            @keypress.enter="submitQuery"
          />
          <button
            class="flex items-center justify-center w-[38px] h-[38px] rounded-lg bg-accent-blue-dark text-white border-none cursor-pointer transition-colors duration-200 shrink-0 hover:bg-accent-blue disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="!dataLoaded || isLoading || !queryText.trim()"
            @click="submitQuery"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
              <path d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
      </section>

      <!-- 右栏：数据管理 -->
      <aside class="flex flex-col gap-3 bg-dark-card border border-dark-border rounded-xl p-4 overflow-y-auto">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-base font-semibold text-text-secondary">数据管理</h2>
        </div>

        <div
          :class="['flex flex-col items-center gap-2 py-6 px-4 border-2 border-dashed rounded-lg cursor-pointer transition-all duration-200', isDragover ? 'border-[#3b82f6] bg-[#3b82f6]/8' : 'border-dark-border-light hover:border-[#3b82f6] hover:bg-[#3b82f6]/4']"
          @click="triggerUpload"
          @dragover.prevent="isDragover = true"
          @dragleave="isDragover = false"
          @drop.prevent="handleDrop"
        >
          <svg class="text-text-faint" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="32" height="32">
            <path d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
          <p class="text-[0.85rem] text-text-muted">点击或拖拽上传 Excel</p>
          <input
            ref="fileInputRef"
            type="file"
            accept=".xlsx,.xls"
            class="hidden"
            @change="handleFileChange"
          />
        </div>

        <div v-if="fileName" class="bg-dark-inner border border-dark-border rounded-lg p-3">
          <div class="flex items-center gap-2 text-[0.85rem] text-text-secondary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">
              <path d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{ fileName }}</span>
          </div>
          <div v-if="dataShape" class="text-text-dim mt-1 text-xs">
            <span>{{ dataShape.rows }} 行 × {{ dataShape.cols }} 列</span>
          </div>
        </div>

        <div v-if="previewData" class="border border-dark-border rounded-lg overflow-hidden">
          <button class="w-full flex items-center justify-between px-3 py-2.5 bg-dark-inner border-none text-text-secondary text-[0.85rem] font-medium cursor-pointer transition-colors duration-200 hover:bg-[#23262e]" @click="showPreview = !showPreview">
            <span>数据预览</span>
            <svg :class="['transition-transform duration-200', showPreview ? 'rotate-180' : '']" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </button>
          <div v-if="showPreview" class="overflow-x-auto max-h-[200px] overflow-y-auto">
            <table class="w-full border-collapse text-[0.75rem]">
              <thead>
                <tr>
                  <th v-for="col in previewData.columns" :key="col" class="bg-dark-border text-text-muted font-semibold text-left px-2 py-1.5 whitespace-nowrap border-b border-dark-border-light">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, ri) in previewData.rows" :key="ri" class="hover:bg-accent-cyan/[0.06]">
                  <td v-for="(cell, ci) in row" :key="ci" class="px-2 py-1 border-b border-dark-border text-text-secondary whitespace-nowrap">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <button
          v-if="dataLoaded"
          class="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg border-none text-[0.85rem] font-medium cursor-pointer transition-all duration-200 bg-[#3b82f6]/10 text-accent-cyan border border-[#3b82f6]/25 hover:bg-[#3b82f6]/18"
          @click="toggleDataInfo"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">
            <path d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
          </svg>
          <span>{{ showDataInfo ? '隐藏数据信息' : '查看数据信息' }}</span>
        </button>

        <div v-if="showDataInfo && dataInfo" class="bg-dark-inner border border-dark-border rounded-lg p-3 flex flex-col gap-1.5">
          <div class="flex items-baseline justify-between text-xs gap-2">
            <span class="text-text-dim shrink-0">行数</span>
            <span class="text-text-secondary text-right">{{ dataInfo.rows }}</span>
          </div>
          <div class="flex items-baseline justify-between text-xs gap-2">
            <span class="text-text-dim shrink-0">列数</span>
            <span class="text-text-secondary text-right">{{ dataInfo.cols }}</span>
          </div>
          <div class="flex items-baseline justify-between text-xs gap-2">
            <span class="text-text-dim shrink-0">列名</span>
            <span class="text-text-secondary text-right break-all leading-relaxed">{{ dataInfo.columns.join(', ') }}</span>
          </div>
          <div v-if="dataInfo.dtypes" class="mt-2 pt-2 border-t border-dark-border">
            <div class="flex items-baseline justify-between text-xs gap-2 pb-1.5 mb-0.5 border-b border-dark-border">
              <span class="text-text-dim shrink-0">列名</span>
              <span class="text-text-dim shrink-0">类型</span>
            </div>
            <div v-for="(dtype, col) in dataInfo.dtypes" :key="col" class="flex items-baseline justify-between text-xs gap-2">
              <span class="text-text-secondary">{{ col }}</span>
              <span class="text-[0.7rem] font-mono px-1.5 py-0.5 bg-[#3b82f6]/12 text-accent-cyan rounded">{{ dtype }}</span>
            </div>
          </div>
        </div>

        <button
          v-if="dataLoaded"
          class="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg text-[0.85rem] font-medium cursor-pointer transition-all duration-200 bg-transparent text-accent-red border border-accent-red/30 hover:bg-accent-red/8"
          @click="clearData"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">
            <path d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
          </svg>
          <span>清除数据</span>
        </button>
      </aside>
    </div>
  </div>
</template>

<script setup>
/**
 * 数据分析视图组件
 * 提供 CSV 上传、数据预览和 AI 对话式数据分析功能
 */
import { ref, nextTick } from 'vue'
import { upload, stream, post } from '../api/request'
import * as XLSX from 'xlsx'

const fileInputRef = ref(null)
const chatAreaRef = ref(null)

const isDragover = ref(false)
const dataLoaded = ref(false)
const isLoading = ref(false)
const fileName = ref('')
const dataShape = ref(null)
const previewData = ref(null)
const showPreview = ref(true)
const showDataInfo = ref(false)
const dataInfo = ref(null)
const queryText = ref('')
const messages = ref([])

/**
 * 触发文件选择对话框
 */
function triggerUpload() {
  fileInputRef.value?.click()
}

/**
 * 处理文件选择事件
 * @param {Event} e - 文件输入变化事件
 */
function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (file) processUploadedFile(file)
  fileInputRef.value.value = ''
}

/**
 * 处理拖拽放置事件
 * @param {DragEvent} e - 拖拽放置事件
 */
function handleDrop(e) {
  isDragover.value = false
  const file = e.dataTransfer.files?.[0]
  if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
    processUploadedFile(file)
  }
}

/**
 * 处理上传的 CSV 文件：解析并更新状态
 * @param {File} file - 上传的 CSV 文件
 */
async function processUploadedFile(file) {
  fileName.value = file.name

  // TODO: 对接后端上传接口，取消注释即可
  // const data = await upload('/upload-xlsx', file)

  // 本地解析 xlsx 前几行用于预览
  const buffer = await file.arrayBuffer()
  const workbook = XLSX.read(buffer, { type: 'array' })
  const sheet = workbook.Sheets[workbook.SheetNames[0]]
  const jsonData = XLSX.utils.sheet_to_json(sheet, { header: 1 })

  const headers = (jsonData[0] || []).map(String)
  const totalRows = jsonData.length - 1
  const rows = jsonData.map(row => row.map(cell => (cell ?? '').toString()))

  previewData.value = { columns: headers, rows }
  dataShape.value = { rows: totalRows, cols: headers.length }
  dataInfo.value = {
    rows: totalRows,
    cols: headers.length,
    columns: headers,
    dtypes: null, // TODO: 由后端返回实际类型信息
  }
  dataLoaded.value = true
  showPreview.value = true
}

/**
 * 切换数据统计信息显示
 */
function toggleDataInfo() {
  showDataInfo.value = !showDataInfo.value
}

/**
 * 清除所有数据和对话记录
 */
function clearData() {
  dataLoaded.value = false
  fileName.value = ''
  dataShape.value = null
  previewData.value = null
  dataInfo.value = null
  showPreview.value = true
  showDataInfo.value = false
  messages.value = []
  queryText.value = ''
}

/**
 * 提交分析查询
 */
async function submitQuery() {
  const q = queryText.value.trim()
  if (!q || !dataLoaded.value || isLoading.value) return

  messages.value.push({ id: Date.now(), role: 'user', type: 'text', content: q })
  queryText.value = ''
  isLoading.value = true
  await nextTick(scrollToBottom)

  try {
    const response = await fetchAnalysisResult(q)
    messages.value.push(response)
  } catch (err) {
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      type: 'text',
      content: `分析出错: ${err.message}`,
    })
  } finally {
    isLoading.value = false
    await nextTick(scrollToBottom)
  }
}

/**
 * 调用后端数据分析接口
 * TODO: 对接实际的后端 API，根据返回类型构建不同的消息对象
 * @param {string} query - 用户的分析指令
 * @returns {Object} 格式化的消息对象，支持以下类型：
 *   - { type: 'text', content: string } 文本回复
 *   - { type: 'table', content: { columns: string[], rows: any[][] } } 表格数据
 *   - { type: 'chart', content: { imageUrl: string, text?: string } } 图表数据
 */
async function fetchAnalysisResult(query) {
  // 流式文本响应：
  // let text = ''
  // await stream('/analyze', { question: query }, (token) => { text += token })
  // return { id: Date.now(), role: 'assistant', type: 'text', content: text }

  // 表格类型响应：
  // const data = await post('/analyze', { question: query })
  // return { id: Date.now(), role: 'assistant', type: 'table', content: data }

  // 图表类型响应：
  // const data = await post('/analyze', { question: query })
  // return { id: Date.now(), role: 'assistant', type: 'chart', content: data }

  return {
    id: Date.now(),
    role: 'assistant',
    type: 'text',
    content: `[待对接] 已收到分析指令: "${query}"，请在此处替换为实际的后端 API 调用。`,
  }
}

/**
 * 滚动聊天区域到底部
 */
function scrollToBottom() {
  if (chatAreaRef.value) {
    chatAreaRef.value.scrollTop = chatAreaRef.value.scrollHeight
  }
}
</script>

<style>
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes bounce {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.1); }
}
</style>
