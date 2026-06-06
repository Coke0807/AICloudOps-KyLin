<template>
  <div class="history-view page-container">
    <div class="history-header">
      <div class="header-info">
        <h3>对话历史</h3>
        <p>查看和管理历史对话记录</p>
      </div>
      <el-button :icon="Refresh" @click="refreshHistory">刷新</el-button>
    </div>

    <div class="history-content">
      <div v-if="chatStore.sessions.length === 0" class="empty-state">
        <el-empty description="暂无对话历史">
          <el-button type="primary" @click="goToChat">开始对话</el-button>
        </el-empty>
      </div>

      <div v-else class="sessions-list">
        <div
          v-for="session in chatStore.sessions"
          :key="session.id"
          class="session-card"
          @click="loadSession(session.id)"
        >
          <div class="session-header">
            <div class="session-title">
              <el-icon><ChatDotRound /></el-icon>
              <span>{{ session.title || '对话记录' }}</span>
            </div>
            <div class="session-actions">
              <el-button
                :icon="Delete"
                type="danger"
                text
                size="small"
                @click.stop="handleDelete(session.id)"
              >
                删除
              </el-button>
            </div>
          </div>
          <div class="session-preview">
            {{ session.preview || '暂无内容' }}
          </div>
          <div class="session-meta">
            <span class="message-count">
              <el-icon><ChatLineRound /></el-icon>
              {{ session.message_count || 0 }} 条消息
            </span>
            <span class="session-time">
              {{ formatTime(session.created_at) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  Refresh,
  ChatDotRound,
  ChatLineRound,
  Delete,
} from '@element-plus/icons-vue'

const router = useRouter()
const chatStore = useChatStore()

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
}

async function refreshHistory() {
  await chatStore.loadHistory()
}

async function loadSession(sessionId) {
  await chatStore.loadSession(sessionId)
  router.push('/chat')
}

async function handleDelete(sessionId) {
  try {
    await ElMessageBox.confirm('确定要删除这条对话记录吗？', '确认删除', {
      type: 'warning',
    })
    await chatStore.deleteSession(sessionId)
    ElMessage.success('删除成功')
  } catch {
    // 取消操作
  }
}

function goToChat() {
  router.push('/chat')
}

onMounted(() => {
  chatStore.loadHistory()
})
</script>

<style lang="scss" scoped>
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;

  h3 {
    font-size: 20px;
    color: #1a1f36;
    margin-bottom: 4px;
  }

  p {
    font-size: 14px;
    color: #606266;
  }
}

.history-content {
  min-height: 400px;
}

.empty-state {
  height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sessions-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.session-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  }
}

.session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.session-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.session-preview {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.session-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
}

.message-count {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
