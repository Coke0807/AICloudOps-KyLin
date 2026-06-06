<template>
  <div class="chat-view">
    <!-- 历史对话侧边栏 (ChatGPT style) -->
    <div class="chat-history-sidebar" :class="{ collapsed: isHistoryCollapsed }">
      <div class="sidebar-toggle-btn" @click="isHistoryCollapsed = !isHistoryCollapsed">
        <el-icon>
          <component :is="isHistoryCollapsed ? 'DArrowRight' : 'DArrowLeft'" />
        </el-icon>
      </div>

      <div class="sidebar-content" v-show="!isHistoryCollapsed">
        <div class="sidebar-header">
          <el-button type="primary" class="new-chat-btn" @click="handleNewChat" plain>
            <el-icon><Plus /></el-icon>
            <span>新建对话</span>
          </el-button>
        </div>
        
        <div class="history-list">
          <div 
            v-for="session in chatStore.sessions" 
            :key="session.id"
            class="history-item"
            :class="{ active: chatStore.currentSessionId === session.id }"
            @click="selectSession(session.id)"
          >
            <el-icon class="item-icon"><ChatDotRound /></el-icon>
            <span class="item-title" :title="session.title">{{ session.title || '对话记录' }}</span>
            <el-button
              class="delete-btn"
              type="danger"
              link
              :icon="Delete"
              @click.stop="handleDeleteSession(session.id)"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="chat-main">
      <div class="messages-container" ref="messagesRef">
        <div v-if="!chatStore.hasMessages" class="welcome-screen">
          <div class="welcome-icon">
            <el-icon :size="64" color="#409eff">
              <Cpu />
            </el-icon>
          </div>
          <h2>AICloudOps 智能运维助手</h2>
          <p>我是您的AI运维助手，可以帮助您监控系统状态、排查故障、执行运维操作。</p>

          <div class="quick-actions">
            <div
              v-for="action in quickActions"
              :key="action.text"
              class="action-card"
              @click="handleQuickAction(action.text)"
            >
              <el-icon :size="24" :color="action.color">
                <component :is="action.icon" />
              </el-icon>
              <span>{{ action.label }}</span>
            </div>
          </div>
        </div>

        <template v-else>
          <div
            v-for="msg in chatStore.messages"
            :key="msg.id"
            class="message-wrapper"
            :class="msg.role"
          >
            <div class="message-avatar">
              <el-avatar :size="36" :class="msg.role">
                <el-icon v-if="msg.role === 'user'"><User /></el-icon>
                <el-icon v-else><Cpu /></el-icon>
              </el-avatar>
            </div>
            <div class="message-content">
              <div class="message-bubble" :class="{ error: msg.isError }">
                <div v-if="msg.reasoning" class="reasoning-block">
                  <div class="reasoning-header" @click="msg._reasoningExpanded = !msg._reasoningExpanded">
                    <el-icon><SetUp /></el-icon>
                    <span>{{ msg.isThinking ? '正在思考...' : '思考过程' }}</span>
                    <el-icon class="reasoning-toggle" :class="{ expanded: msg._reasoningExpanded }">
                      <ArrowDown />
                    </el-icon>
                  </div>
                  <div v-show="msg._reasoningExpanded" class="reasoning-content">
                    {{ msg.reasoning }}
                  </div>
                </div>
                <div v-if="msg.toolStatus" class="tool-status">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>{{ msg.toolStatus }}</span>
                </div>
                <div v-if="msg.isStreaming && !msg.content && !msg.reasoning" class="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
                <div v-if="msg.isThinking && !msg.content" class="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
                <div v-if="msg.content" class="message-text" v-html="formatMessage(msg.content)" />
              </div>
              <div v-if="msg.safetyReport" class="safety-report">
                <el-tag :type="msg.safetyReport.is_safe ? 'success' : 'danger'" size="small">
                  {{ msg.safetyReport.is_safe ? '安全' : '风险拦截' }}
                </el-tag>
              </div>
              <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
            </div>
          </div>
        </template>
      </div>

      <div class="input-area">
        <div class="input-wrapper">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="输入您的运维问题，例如：查看系统状态、检查磁盘使用情况..."
            @keydown.enter.exact.prevent="handleSend"
            :disabled="chatStore.loading"
          />
          <div class="input-actions">
            <el-tooltip content="清空对话" placement="top">
              <el-button :icon="Delete" circle text @click="handleClear" />
            </el-tooltip>
            <el-button
              type="primary"
              :icon="Promotion"
              :loading="chatStore.loading"
              @click="handleSend"
            >
              发送
            </el-button>
          </div>
        </div>
        <div class="input-hint">
          按 Enter 发送，Shift + Enter 换行
        </div>
      </div>
    </div>

    <div class="chat-sidebar">
      <div class="sidebar-section">
        <div class="section-title">
          <el-icon><Monitor /></el-icon>
          <span>系统概览</span>
        </div>
        <div class="status-cards">
          <div class="status-card">
            <div class="status-value" :class="getStatusClass(systemStore.cpuUsage)">
              {{ systemStore.cpuUsage }}%
            </div>
            <div class="status-label">CPU 使用率</div>
            <el-progress
              :percentage="systemStore.cpuUsage"
              :stroke-width="4"
              :show-text="false"
              :color="getStatusColor(systemStore.cpuUsage)"
            />
          </div>
          <div class="status-card">
            <div class="status-value" :class="getStatusClass(systemStore.memoryUsage)">
              {{ systemStore.memoryUsage }}%
            </div>
            <div class="status-label">内存使用率</div>
            <el-progress
              :percentage="systemStore.memoryUsage"
              :stroke-width="4"
              :show-text="false"
              :color="getStatusColor(systemStore.memoryUsage)"
            />
          </div>
        </div>
      </div>

      <div class="sidebar-section">
        <div class="section-title">
          <el-icon><SetUp /></el-icon>
          <span>快捷工具</span>
        </div>
        <div class="tool-list">
          <div
            v-for="tool in quickTools"
            :key="tool.name"
            class="tool-item"
            @click="handleToolClick(tool)"
          >
            <el-icon :color="tool.color"><component :is="tool.icon" /></el-icon>
            <span>{{ tool.label }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSystemStore } from '@/stores/system'
import { renderMarkdown } from '@/utils/markdown'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  Cpu,
  User,
  Delete,
  Promotion,
  Monitor,
  SetUp,
  DataLine,
  Document,
  Connection,
  Warning,
  ArrowDown,
  Loading,
  Plus,
  DArrowRight,
  DArrowLeft,
  ChatDotRound,
} from '@element-plus/icons-vue'

const chatStore = useChatStore()
const systemStore = useSystemStore()

const inputText = ref('')
const messagesRef = ref(null)
const isHistoryCollapsed = ref(false)

async function selectSession(sessionId) {
  if (chatStore.loading) return
  await chatStore.loadSession(sessionId)
  await nextTick()
  scrollToBottom()
}

function handleNewChat() {
  if (chatStore.loading) return
  chatStore.clearMessages()
}

async function handleDeleteSession(sessionId) {
  try {
    await ElMessageBox.confirm('确定要删除这条对话记录吗？', '确认删除', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await chatStore.deleteSession(sessionId)
    ElMessage.success('删除成功')
    if (chatStore.currentSessionId === sessionId) {
      chatStore.clearMessages()
    }
  } catch (e) {
    // 取消
  }
}

const quickActions = [
  { text: '查看系统状态', label: '系统状态', icon: 'Monitor', color: '#409eff' },
  { text: '检查磁盘使用情况', label: '磁盘检查', icon: 'DataLine', color: '#67c23a' },
  { text: '查看运行中的进程', label: '进程列表', icon: 'Document', color: '#e6a23c' },
  { text: '检查网络连接状态', label: '网络状态', icon: 'Connection', color: '#f56c6c' },
]

const quickTools = [
  { name: 'get_system_status', label: '系统状态', icon: 'Monitor', color: '#409eff' },
  { name: 'get_process_list', label: '进程列表', icon: 'Document', color: '#67c23a' },
  { name: 'get_disk_usage', label: '磁盘信息', icon: 'DataLine', color: '#e6a23c' },
  { name: 'get_memory_usage', label: '内存分析', icon: 'Coin', color: '#6366f1' },
  { name: 'get_network_connections', label: '网络连接', icon: 'Connection', color: '#f56c6c' },
  { name: 'get_service_status', label: '服务状态', icon: 'List', color: '#409eff' },
  { name: 'query_journal', label: '日志查询', icon: 'Document', color: '#909399' },
]

function getStatusClass(value) {
  if (value < 60) return 'success'
  if (value < 80) return 'warning'
  return 'danger'
}

function getStatusColor(value) {
  if (value < 60) return '#67c23a'
  if (value < 80) return '#e6a23c'
  return '#f56c6c'
}

function formatMessage(content) {
  if (!content) return ''
  return renderMarkdown(content)
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text) return

  inputText.value = ''
  await chatStore.sendStreamMessage(text)
  await chatStore.loadHistory()

  await nextTick()
  scrollToBottom()
}

function handleQuickAction(text) {
  inputText.value = text
  handleSend()
}

async function handleToolClick(tool) {
  const text = `执行 ${tool.label}`
  inputText.value = text
  await handleSend()
}

function handleClear() {
  chatStore.clearMessages()
}

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

watch(() => chatStore.messages.length, () => {
  nextTick(scrollToBottom)
})

onMounted(() => {
  systemStore.fetchSystemStatus()
  chatStore.loadHistory()
})
</script>

<style lang="scss" scoped>
.chat-view {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.chat-history-sidebar {
  position: relative;
  width: 240px;
  height: 100%;
  background-color: #f8f9fc;
  border-right: 1px solid #eef2f6;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;

  &.collapsed {
    width: 0;
    border-right: none;
    
    .sidebar-toggle-btn {
      left: 0;
      border-radius: 0 8px 8px 0;
      border-left: none;
      box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
    }
  }
}

.sidebar-toggle-btn {
  position: absolute;
  top: 50%;
  right: -16px;
  transform: translateY(-50%);
  width: 16px;
  height: 48px;
  background-color: #fff;
  border: 1px solid #eef2f6;
  border-left: none;
  border-radius: 0 8px 8px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 5;
  transition: all 0.2s ease;
  color: #909399;

  &:hover {
    color: #409eff;
    background-color: #f0f7ff;
    width: 20px;
    right: -20px;
  }
}

.sidebar-content {
  width: 240px;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #eef2f6;
  
  .new-chat-btn {
    width: 100%;
    border-radius: 8px;
    height: 36px;
    font-weight: 500;
    transition: all 0.2s ease;
    
    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
    }
  }
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;

  &::-webkit-scrollbar {
    width: 4px;
  }
  &::-webkit-scrollbar-thumb {
    background: #e4e7ed;
    border-radius: 2px;
  }
}

.history-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  gap: 8px;
  
  .item-icon {
    font-size: 16px;
    color: #909399;
    flex-shrink: 0;
  }

  .item-title {
    font-size: 13px;
    color: #606266;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }

  .delete-btn {
    opacity: 0;
    transition: opacity 0.2s ease;
    padding: 0;
    height: auto;
    font-size: 14px;
    color: #909399;

    &:hover {
      color: #f56c6c;
    }
  }

  &:hover {
    background-color: #ecf5ff;
    
    .item-icon {
      color: #409eff;
    }
    .item-title {
      color: #409eff;
    }
    .delete-btn {
      opacity: 1;
    }
  }

  &.active {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.1), rgba(99, 102, 241, 0.05));
    border-left: 3px solid #409eff;
    padding-left: 9px;
    
    .item-icon {
      color: #409eff;
    }
    .item-title {
      color: #1a1f36;
      font-weight: 500;
    }
    .delete-btn {
      opacity: 1;
    }
  }
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.welcome-screen {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;

  h2 {
    margin-top: 16px;
    font-size: 24px;
    color: #1a1f36;
  }

  p {
    margin-top: 8px;
    color: #606266;
    font-size: 14px;
  }
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 32px;
  max-width: 400px;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  }

  span {
    font-size: 13px;
    color: #606266;
  }
}

.message-wrapper {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;

  &.user {
    flex-direction: row-reverse;

    .message-content {
      align-items: flex-end;
    }

    .message-bubble {
      background: linear-gradient(135deg, #409eff, #6366f1);
      color: #fff;
    }
  }

  &.assistant {
    .message-bubble {
      background: #fff;
      color: #303133;
    }
  }
}

.message-avatar {
  .el-avatar {
    &.user {
      background: linear-gradient(135deg, #409eff, #6366f1);
    }

    &.assistant {
      background: linear-gradient(135deg, #67c23a, #059669);
    }
  }
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: 70%;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  &.error {
    background: #fef0f0;
    color: #f56c6c;
  }

  :deep(pre.hljs) {
    background: #f6f8fa;
    border-radius: 8px;
    padding: 12px;
    overflow-x: auto;
    margin: 8px 0;

    code {
      background: none;
      padding: 0;
      font-size: 13px;
    }
  }

  :deep(code) {
    background: rgba(0, 0, 0, 0.06);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 13px;
  }

  :deep(table) {
    border-collapse: collapse;
    margin: 8px 0;
    width: 100%;

    th, td {
      border: 1px solid #ebeef5;
      padding: 6px 10px;
      text-align: left;
      font-size: 13px;
    }

    th {
      background: #f5f7fa;
      font-weight: 600;
    }
  }

  :deep(ul), :deep(ol) {
    padding-left: 20px;
    margin: 4px 0;
  }

  :deep(blockquote) {
    border-left: 3px solid #409eff;
    margin: 8px 0;
    padding: 4px 12px;
    color: #606266;
    background: #f5f7fa;
    border-radius: 0 4px 4px 0;
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;

  span {
    width: 8px;
    height: 8px;
    background: #909399;
    border-radius: 50%;
    animation: typing 1.4s infinite both;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes typing {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.6; }
  40% { transform: scale(1); opacity: 1; }
}

.reasoning-block {
  margin-bottom: 8px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  background: #fafbfc;
}

.reasoning-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: #909399;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;

  &:hover {
    background: #f0f2f5;
  }
}

.reasoning-toggle {
  margin-left: auto;
  transition: transform 0.2s;

  &.expanded {
    transform: rotate(180deg);
  }
}

.reasoning-content {
  padding: 0 12px 10px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  white-space: pre-wrap;
  border-top: 1px solid #ebeef5;
}

.tool-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #409eff;
  background: #ecf5ff;
  border-radius: 6px;
}

.safety-report-blocked {
  margin-top: 8px;
  background: #fef0f0;
  border: 1px solid #fbc4c4;
  border-radius: 8px;
  padding: 12px;
}

.safety-blocked-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.safety-blocked-title {
  font-size: 14px;
  font-weight: 600;
  color: #f56c6c;
}

.safety-blocked-detail {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  font-size: 13px;
}

.safety-blocked-label {
  color: #909399;
  min-width: 56px;
}

.safety-blocked-reason {
  color: #606266;
}

.safety-report-passed {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #67c23a;
}

.message-time {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}

.input-area {
  padding: 16px 24px;
  background: #fff;
  border-top: 1px solid #ebeef5;
}

.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;

  :deep(.el-textarea__inner) {
    border-radius: 12px;
    padding: 12px 16px;
    resize: none;
  }
}

.input-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.input-hint {
  font-size: 11px;
  color: #909399;
  margin-top: 8px;
  text-align: center;
}

.chat-sidebar {
  width: 280px;
  background: #fff;
  border-left: 1px solid #ebeef5;
  padding: 20px;
  overflow-y: auto;
}

.sidebar-section {
  margin-bottom: 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

.status-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-card {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;

  .status-value {
    font-size: 24px;
    font-weight: 700;

    &.success { color: #67c23a; }
    &.warning { color: #e6a23c; }
    &.danger { color: #f56c6c; }
  }

  .status-label {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
    margin-bottom: 8px;
  }
}

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tool-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #f5f7fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
  color: #606266;

  &:hover {
    background: #ecf5ff;
    color: #409eff;
  }
}
</style>
