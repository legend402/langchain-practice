const API_BASE = 'http://127.0.0.1:4030'

/**
 * 构建完整的请求 URL
 * @param {string} path - 接口路径，例如 '/chat'
 * @returns {string} 完整 URL
 */
function buildUrl(path) {
  return `${API_BASE}${path}`
}

/**
 * 通用请求方法，封装 fetch 调用，统一处理响应解析和错误
 * @param {string} path - 接口路径
 * @param {Object} options - 请求配置
 * @param {string} [options.method='GET'] - 请求方法
 * @param {Object} [options.headers] - 请求头
 * @param {Object|FormData} [options.body] - 请求体
 * @param {boolean} [options.rawResponse=false] - 是否返回原始 Response 对象而不解析 JSON
 * @returns {Promise<Object|Response>} 默认返回解析后的 JSON 数据，rawResponse 为 true 时返回原始 Response
 */
async function request(path, options = {}) {
  const {
    method = 'GET',
    headers = {},
    body = undefined,
    rawResponse = false,
  } = options

  const config = {
    method,
    headers,
    body,
  }

  if (body && !(body instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json'
    config.body = JSON.stringify(body)
  }

  const response = await fetch(buildUrl(path), config)

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status} ${response.statusText}`)
  }

  if (rawResponse) {
    return response
  }

  return response.json()
}

/**
 * GET 请求
 * @param {string} path - 接口路径
 * @param {Object} [options] - 额外配置（同 request 的 options，不含 method/body）
 * @returns {Promise<Object>} 解析后的 JSON 数据
 */
function get(path, options = {}) {
  return request(path, { ...options, method: 'GET' })
}

/**
 * POST JSON 请求
 * @param {string} path - 接口路径
 * @param {Object} data - 请求体数据
 * @param {Object} [options] - 额外配置
 * @returns {Promise<Object>} 解析后的 JSON 数据
 */
function post(path, data, options = {}) {
  return request(path, { ...options, method: 'POST', body: data })
}

/**
 * 上传文件（FormData）
 * @param {string} path - 接口路径
 * @param {File} file - 要上传的文件
 * @param {string} [fieldName='file'] - FormData 中文件字段的名称
 * @returns {Promise<Object>} 解析后的 JSON 数据
 */
function upload(path, file, fieldName = 'file') {
  const formData = new FormData()
  formData.append(fieldName, file)
  return request(path, { method: 'POST', body: formData })
}

/**
 * SSE 流式请求，逐块读取服务端推送的 data 行并回调
 * @param {string} path - 接口路径
 * @param {Object} data - 请求体数据
 * @param {Function} onChunk - 每条 SSE 数据的回调，参数为解析后的对象
 * @param {Function} [onDone] - 流结束时的回调
 * @param {string} [options.tokenField='token'] - 从 SSE JSON 中提取的字段名
 * @returns {Promise<void>}
 */
async function stream(path, data, onChunk, onDone, options = {}) {
  const { tokenField = 'token' } = options

  const response = await request(path, {
    method: 'POST',
    body: data,
    rawResponse: true,
  })

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const payload = line.slice(6)
        if (payload === '[DONE]') {
          onDone?.()
          return
        }
        try {
          const parsed = JSON.parse(payload)
          onChunk(parsed[tokenField], parsed)
        } catch {
          // 忽略非 JSON 行
        }
      }
    }
  }

  onDone?.()
}

export { request, get, post, upload, stream, API_BASE }
export default request
