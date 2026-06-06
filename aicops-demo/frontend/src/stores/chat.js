import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { agentApi, historyApi } from '@/api'

let _msgSeq = 0
/** 生成不重复的消息 ID，避免 Date.now() 同毫秒碰撞 */
function nextMsgId() {
  return `${Date.now()}-${++_msgSeq}`
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const loading = ref(false)
  const currentSessionId = ref(null)
  const sessions = ref([])

  const hasMessages = computed(() => messages.value.length > 0)

  async function sendMessage(content) {
    if (!content.trim() || loading.value) return

    const userMessage = {
      id: nextMsgId(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    }
    messages.value.push(userMessage)

    loading.value = true
    try {
      const response = await agentApi.process(content, currentSessionId.value)

      if (response.session_id) {
        currentSessionId.value = response.session_id
      }

      const assistantMessage = {
        id: nextMsgId(),
        role: 'assistant',
        content: response.response || response.final_result?.tool_result?.data || '处理完成',
        timestamp: new Date().toISOString(),
        traceId: response.trace_id,
        safetyReport: response.safety_report,
        toolResult: response.tool_result,
      }
      messages.value.push(assistantMessage)

      return response
    } catch (error) {
      const errorMessage = {
        id: nextMsgId(),
        role: 'assistant',
        content: `错误: ${error.message}`,
        timestamp: new Date().toISOString(),
        isError: true,
      }
      messages.value.push(errorMessage)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function sendStreamMessage(content) {
    if (!content.trim() || loading.value) return

    const userMessage = {
      id: nextMsgId(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    }
    messages.value.push(userMessage)

    const assistantMessage = {
      id: nextMsgId(),
      role: 'assistant',
      content: '',
      reasoning: '',
      isStreaming: true,
      isThinking: false,
      toolStatus: null,
      _reasoningExpanded: true,
      timestamp: new Date().toISOString(),
    }
    messages.value.push(assistantMessage)

    loading.value = true
    try {
      const stream = agentApi.stream(content, currentSessionId.value)
      for await (const chunk of stream) {
        if (chunk.session_id) {
          currentSessionId.value = chunk.session_id
        }
        if (chunk.reasoning) {
          assistantMessage.reasoning += chunk.reasoning
          assistantMessage.isThinking = true
        }
        if (chunk.content) {
          if (assistantMessage.isThinking) {
            assistantMessage.isThinking = false
          }
          assistantMessage.content += chunk.content
        }
        if (chunk.status === 'tool_calls') {
          assistantMessage.toolStatus = `正在调用工具: ${chunk.tools.join(', ')}...`
        }
        if (chunk.done) {
          assistantMessage.isStreaming = false
          assistantMessage.isThinking = false
          assistantMessage.toolStatus = null
          assistantMessage._reasoningExpanded = false
          assistantMessage.traceId = chunk.trace_id
          assistantMessage.safetyReport = chunk.safety_report
        }
      }
    } catch (error) {
      assistantMessage.content += `\n\n错误: ${error.message}`
      assistantMessage.isError = true
    } finally {
      loading.value = false
      assistantMessage.isStreaming = false
      assistantMessage.isThinking = false
      assistantMessage.toolStatus = null
    }
  }

  function clearMessages() {
    messages.value = []
    currentSessionId.value = null
  }

  async function loadHistory() {
    try {
      const response = await historyApi.list()
      sessions.value = response.sessions || []
    } catch (error) {
      console.error('加载历史记录失败:', error)
    }
  }

  async function loadSession(sessionId) {
    try {
      const response = await historyApi.get(sessionId)
      if (response.messages) {
        messages.value = response.messages
        currentSessionId.value = sessionId
      }
    } catch (error) {
      console.error('加载会话失败:', error)
    }
  }

  async function deleteSession(sessionId) {
    try {
      await historyApi.delete(sessionId)
      sessions.value = sessions.value.filter((s) => s.id !== sessionId)
      if (currentSessionId.value === sessionId) {
        clearMessages()
      }
    } catch (error) {
      console.error('删除会话失败:', error)
    }
  }

  return {
    messages,
    loading,
    currentSessionId,
    sessions,
    hasMessages,
    sendMessage,
    sendStreamMessage,
    clearMessages,
    loadHistory,
    loadSession,
    deleteSession,
  }
})
