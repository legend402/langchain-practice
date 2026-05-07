<template>
  <div class="flex h-full max-md:flex-col">
    <aside class="w-80 bg-dark-card border-r border-dark-border flex flex-col overflow-y-auto shrink-0 max-md:w-full max-md:max-h-[50vh] max-md:border-r-0 max-md:border-b">
      <div class="p-6 px-4">
        <h2 class="text-xl font-semibold mb-6 text-text-primary">📁 文档管理</h2>

        <div :class="['px-4 py-3 rounded-lg mb-4 text-sm flex items-center gap-2', dbExists ? 'bg-accent-green/15 text-accent-green border border-accent-green/30' : 'bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30']">
          <span>{{ dbExists ? '✅' : '📝' }}</span>
          <span>{{ dbExists ? '数据库状态：已就绪' : '状态：等待上传PDF' }}</span>
        </div>

        <div class="h-px bg-dark-border my-5" />

        <div
          :class="['border-2 border-dashed border-dark-border-light rounded-lg py-8 px-4 text-center cursor-pointer transition-all duration-200 mb-4', isDragover ? 'border-accent-cyan bg-accent-cyan/10' : 'hover:border-accent-cyan hover:bg-accent-cyan/5']"
          @click="triggerUpload"
          @dragover.prevent="isDragover = true"
          @dragleave="isDragover = false"
          @drop.prevent="handleDrop"
        >
          <div class="text-3xl mb-2">📎</div>
          <div class="text-sm text-text-muted">点击或拖拽上传PDF文件</div>
          <div class="text-xs text-text-dim mt-2">支持上传多个PDF文件</div>
          <input
            ref="fileInputRef"
            type="file"
            accept=".pdf"
            multiple
            class="hidden"
            @change="handleFileChange"
          />
        </div>

        <div class="mb-4">
          <div v-for="(file, i) in uploadedFiles" :key="file.name" class="flex items-center justify-between px-3 py-2 bg-dark-inner rounded-md mb-2 text-[0.85rem]">
            <span class="text-text-secondary overflow-hidden text-ellipsis whitespace-nowrap flex-1">{{ i + 1 }}. {{ file.name }}</span>
            <span class="text-accent-red cursor-pointer ml-2 text-lg leading-none hover:text-red-400" title="移除" @click="removeFile(i)">&times;</span>
          </div>
        </div>

        <button
          :class="['w-full py-3 text-white border-none rounded-lg text-base font-medium cursor-pointer transition-all duration-200 flex items-center justify-center gap-2', isProcessing ? 'bg-accent-yellow cursor-wait' : uploadedFiles.length === 0 || isProcessing ? 'bg-dark-border-light text-text-muted cursor-not-allowed' : 'bg-accent-blue hover:bg-blue-700']"
          :disabled="uploadedFiles.length === 0 || isProcessing"
          @click="processFiles"
        >
          <div v-if="isProcessing" class="w-4 h-4 border-2 border-dark-border-light border-t-accent-cyan rounded-full animate-spin" />
          <span v-else>🚀</span>
          <span>{{ isProcessing ? '正在处理...' : '提交并处理' }}</span>
        </button>

        <div v-if="uploadedFiles.length > 0" class="mt-3 px-3 py-3 bg-accent-cyan/15 border border-accent-cyan/30 rounded-md text-accent-cyan text-[0.85rem] flex items-center gap-2">
          <span>📄</span>
          <span>已选择 {{ uploadedFiles.length }} 个文件</span>
        </div>

        <div :class="['mt-6 border border-dark-border rounded-lg overflow-hidden', { open: expanderOpen }]">
          <div class="px-4 py-3 bg-dark-inner cursor-pointer flex items-center justify-between text-[0.95rem] select-none hover:bg-[#23262e]" @click="expanderOpen = !expanderOpen">
            <span>💡 使用说明</span>
            <span :class="['text-xs transition-transform duration-200', expanderOpen ? 'rotate-180' : '']">▼</span>
          </div>
          <div :class="['overflow-hidden transition-[max-height] duration-300 ease bg-dark-bg', expanderOpen ? 'max-h-[500px]' : 'max-h-0']">
            <div class="p-4 text-sm leading-relaxed text-[#cbd5e0]">
              <strong>步骤：</strong>
              <ol class="ml-5 mb-4">
                <li v-for="step in steps" :key="step" class="mb-2">{{ step }}</li>
              </ol>
              <strong>提示：</strong>
              <ul class="ml-5 list-disc">
                <li v-for="tip in tips" :key="tip" class="mb-2">{{ tip }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <main class="flex-1 overflow-y-auto p-8 px-12 max-md:p-6">
      <h1 class="text-3xl font-bold mb-8 text-text-primary">🤖 LangChain知识库系统开发</h1>

      <div class="grid grid-cols-[3fr_1fr] gap-6 mb-8 max-md:grid-cols-1">
        <div class="flex items-center">
          <div v-if="dbExists" class="bg-accent-green/15 border border-accent-green/30 text-accent-green px-5 py-4 rounded-lg flex items-center gap-2 text-[0.95rem] w-full">
            <span>✅</span>
            <span>数据库已就绪，可以开始提问</span>
          </div>
          <div v-else class="bg-accent-yellow/15 border border-accent-yellow/30 text-[#ecc94b] px-5 py-4 rounded-lg flex items-center gap-2 text-[0.95rem] w-full">
            <span>⚠️</span>
            <span>请先上传并处理PDF文件</span>
          </div>
        </div>
        <div class="flex items-center justify-end max-md:justify-start">
          <button class="px-5 py-3 bg-transparent text-accent-red border border-accent-red rounded-lg text-[0.95rem] cursor-pointer transition-all duration-200 flex items-center gap-2 hover:bg-accent-red/10" @click="clearDatabase">
            <span>🗑️</span>
            <span>清除数据库</span>
          </button>
        </div>
      </div>

      <div class="mb-8">
        <label class="flex items-center gap-2 mb-2 text-base text-text-secondary">
          <span>💬</span>
          <span>请输入问题</span>
        </label>
        <input
          v-model="questionText"
          type="text"
          class="w-full py-3.5 px-4 bg-dark-card border border-dark-border-light rounded-lg text-text-primary text-base transition-colors duration-200 placeholder:text-text-dim focus:outline-none focus:border-accent-cyan disabled:bg-dark-inner disabled:text-text-dim disabled:cursor-not-allowed"
          placeholder="例如：这个文档的主要内容是什么？"
          :disabled="!dbExists"
          @keypress.enter="askQuestion"
        />
      </div>

      <div ref="chatAreaRef" class="mt-6">
        <div
          v-for="msg in messages"
          :key="msg.id"
          :class="['mb-4 px-5 py-4 rounded-lg animate-[fadeIn_0.3s_ease]', msg.sender === 'user' ? 'bg-accent-blue text-white ml-8' : 'bg-dark-card border border-dark-border text-text-secondary mr-8']"
        >
          <div class="text-xs font-semibold mb-2 opacity-80">{{ msg.sender === 'user' ? '👤 用户' : '🤖 AI' }}</div>
          <div v-if="msg.thinking" class="flex items-center gap-3 text-text-muted italic p-4">
            <div class="w-5 h-5 border-2 border-dark-border-light border-t-accent-cyan rounded-full animate-spin" />
            <span>AI正在分析文档...</span>
          </div>
          <div v-else>{{ msg.text }}</div>
        </div>
      </div>
    </main>

    <div class="fixed top-6 right-6 z-[1000] flex flex-col gap-3">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="['px-5 py-4 rounded-lg text-sm flex items-center gap-3 min-w-[280px] animate-[slideIn_0.3s_ease] shadow-[0_4px_6px_rgba(0,0,0,0.3)]', toastColors[toast.type]]"
      >
        {{ toast.message }}
      </div>
    </div>

    <div class="fixed inset-0 pointer-events-none z-[999] overflow-hidden">
      <div
        v-for="b in balloonList"
        :key="b.id"
        class="absolute -bottom-[100px] w-10 h-[50px] rounded-full opacity-80 animate-[floatUp_3s_ease-in_forwards] after:content-[''] after:absolute after:-bottom-2.5 after:left-1/2 after:w-0.5 after:h-5 after:bg-inherit after:-translate-x-1/2"
        :style="b.style"
      />
    </div>
  </div>
</template>

<script setup>
/**
 * RAG知识库视图组件
 * 提供PDF上传、处理和基于文档的AI问答功能
 */
import { ref, nextTick, onMounted } from 'vue'
import { get, upload, stream } from '../api/request'

const steps = ['📎 上传一个或多个PDF文件', '🚀 点击"提交并处理"处理文档', '💬 在主页面输入您的问题', '🤖 AI将基于PDF内容回答问题']
const tips = ['支持多个PDF文件同时上传', '处理大文件可能需要一些时间', '可以随时清除数据库重新开始']

const toastColors = {
  success: 'bg-accent-green text-white',
  error: 'bg-[#e53e3e] text-white',
  warning: 'bg-accent-yellow text-[#1a202c]',
  info: 'bg-[#3182ce] text-white',
}

const uploadedFiles = ref([])
const dbExists = ref(false)
const isProcessing = ref(false)
const isDragover = ref(false)
const expanderOpen = ref(false)
const questionText = ref('')
const messages = ref([])
const toasts = ref([])
const balloonList = ref([])
const fileInputRef = ref(null)
const chatAreaRef = ref(null)

onMounted(() => {
  checkDbExists()
})

/**
 * 检查数据库是否已存在
 */
async function checkDbExists() {
  try {
    const json = await get('/checkDb')
    dbExists.value = json.code === 200
  } catch {
    dbExists.value = false
  }
}

/**
 * 触发文件选择器
 */
function triggerUpload() {
  fileInputRef.value?.click()
}

/**
 * 处理文件选择变化
 * @param {Event} e - 文件选择事件
 */
function handleFileChange(e) {
  addFiles(Array.from(e.target.files))
  fileInputRef.value.value = ''
}

/**
 * 处理文件拖拽放置
 * @param {DragEvent} e - 拖拽事件
 */
function handleDrop(e) {
  isDragover.value = false
  const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf')
  addFiles(files)
}

/**
 * 添加文件到上传列表（去重）
 * @param {File[]} files - 要添加的文件数组
 */
function addFiles(files) {
  const newFiles = files.filter(f => !uploadedFiles.value.some(uf => uf.name === f.name))
  uploadedFiles.value = [...uploadedFiles.value, ...newFiles]
}

/**
 * 从上传列表中移除指定索引的文件
 * @param {number} index - 文件索引
 */
function removeFile(index) {
  uploadedFiles.value.splice(index, 1)
}

/**
 * 提交并处理上传的PDF文件
 */
async function processFiles() {
  if (uploadedFiles.value.length === 0 || isProcessing.value) return

  isProcessing.value = true

  try {
    await Promise.all(uploadedFiles.value.map(file => uploadFile(file)))
    dbExists.value = true
    showToast('success', '✅ PDF处理完成！现在可以开始提问了')
    launchBalloons()
    uploadedFiles.value = []
  } catch (error) {
    showToast('error', `❌ 处理PDF时出错: ${error.message}`)
  } finally {
    isProcessing.value = false
  }
}

/**
 * 上传单个文件到后端
 * @param {File} file - 要上传的文件
 * @returns {Promise<Object>} 上传响应
 */
function uploadFile(file) {
  return upload('/uploadPdf', file)
}

/**
 * 清除数据库并重置UI状态
 */
function clearDatabase() {
  if (!dbExists.value) {
    showToast('warning', '数据库已经是空状态')
    return
  }
  dbExists.value = false
  uploadedFiles.value = []
  messages.value = []
  questionText.value = ''
  showToast('success', '数据库已清除')
}

/**
 * 提交问题并获取AI流式回答
 */
async function askQuestion() {
  const question = questionText.value.trim()
  if (!question || !dbExists.value) return

  messages.value.push({
    id: Date.now(),
    sender: 'user',
    text: question,
    thinking: false,
  })
  questionText.value = ''

  const aiMsgId = Date.now() + 1
  messages.value.push({
    id: aiMsgId,
    sender: 'ai',
    text: '',
    thinking: true,
  })

  await nextTick()
  scrollToBottom()

  const aiMsg = messages.value.find(m => m.id === aiMsgId)
  let started = false

  await queryAnswer(question, (chunk) => {
    if (!started) {
      aiMsg.thinking = false
      started = true
    }
    aiMsg.text += chunk
    nextTick(scrollToBottom)
  })
}

/**
 * 通过SSE流式传输查询AI回答
 * @param {string} question - 用户问题
 * @param {Function} chunkHandler - 数据块处理回调
 */
async function queryAnswer(question, chunkHandler) {
  await stream('/chat', { question }, (token) => {
    chunkHandler?.(token)
  })
}

/**
 * 滚动聊天区域到底部
 */
function scrollToBottom() {
  if (chatAreaRef.value) {
    chatAreaRef.value.scrollTop = chatAreaRef.value.scrollHeight
  }
}

/**
 * 显示Toast通知
 * @param {string} type - 通知类型 (success/error/warning/info)
 * @param {string} message - 通知内容
 */
function showToast(type, message) {
  const id = Date.now() + Math.random()
  toasts.value.push({ id, type, message })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 3000)
}

/**
 * 启动气球庆祝动画
 */
function launchBalloons() {
  const colors = ['#fc8181', '#63b3ed', '#68d391', '#f6e05e', '#b794f4', '#f687b3']
  for (let i = 0; i < 15; i++) {
    const id = Date.now() + i
    const color = colors[Math.floor(Math.random() * colors.length)]
    const duration = (2.5 + Math.random() * 1.5) + 's'
    const left = Math.random() * 100 + '%'

    balloonList.value.push({
      id,
      style: {
        left,
        backgroundColor: color,
        animationDuration: duration,
      },
    })

    setTimeout(() => {
      balloonList.value = balloonList.value.filter(b => b.id !== id)
    }, 4000)
  }
}
</script>

<style>
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes slideIn {
  from { opacity: 0; transform: translateX(100%); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes floatUp {
  0% { transform: translateY(0) rotate(0deg); opacity: 0.8; }
  100% { transform: translateY(-120vh) rotate(20deg); opacity: 0; }
}
</style>
