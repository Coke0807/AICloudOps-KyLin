<template>
  <div class="query-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon">
            <Icon icon="lucide:message-square" size="48" color="#1890ff" />
          </div>
          <div class="header-text">
            <h1 class="page-title">智能问答</h1>
            <p class="page-subtitle">基于MCP协议的安全智能运维助手</p>
          </div>
        </div>
        <div class="header-actions">
          <a-space>
            <a-button @click="clearSession" type="default">
              <Icon icon="lucide:trash-2" size="16" color="#8c8c8c" />
              清空会话
            </a-button>
            <a-button @click="goToSessionManage" type="primary">
              <Icon icon="lucide:users" size="16" color="#ffffff" />
              会话管理
            </a-button>
          </a-space>
        </div>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="page-content">
      <a-row :gutter="24">
        <!-- 聊天区域 -->
        <a-col :span="16">
          <div class="content-card">
            <div class="card-header">
              <div class="header-title">
                <Icon icon="lucide:message-circle" size="18" color="#1890ff" />
                对话
              </div>
            </div>

            <div class="card-content">
              <!-- 聊天历史 -->
              <div class="chat-history" ref="chatHistoryRef">
                <div v-if="chatHistory.length === 0" class="empty-state">
                  <Icon icon="lucide:message-circle" size="48" color="#bfbfbf" />
                  <p>开始您的第一次对话吧！</p>
                  <div class="quick-actions">
                    <a-button v-for="(q, idx) in quickQuestions" :key="idx" type="default" class="quick-action-btn" @click="askQuickQuestion(q)">
                      {{ q }}
                    </a-button>
                  </div>
                </div>

                <div v-for="(message, index) in chatHistory" :key="index" class="message-item">
                  <!-- 用户消息 -->
                  <div v-if="message.role === 'user'" class="user-message">
                    <div class="message-content">
                      <div class="message-text">{{ message.content }}</div>
                      <div class="message-time">{{ formatTime(message.timestamp) }}</div>
                    </div>
                    <a-avatar class="message-avatar" style="background-color: #1890ff;">
                      <Icon icon="lucide:user" size="16" />
                    </a-avatar>
                  </div>

                  <!-- 助手消息 -->
                  <div v-else class="assistant-message">
                    <a-avatar class="message-avatar" style="background-color: #52c41a;">
                      <Icon icon="lucide:bot" size="16" />
                    </a-avatar>
                    <div class="message-content">
                      <!-- 思考过程 -->
                      <div v-if="message.reasoning" class="reasoning-block">
                        <div class="reasoning-header" @click="message._expanded = !message._expanded">
                          <Icon icon="lucide:brain" size="14" />
                          <span>思考过程</span>
                          <Icon :icon="message._expanded ? 'lucide:chevron-up' : 'lucide:chevron-down'" size="14" />
                        </div>
                        <div v-show="message._expanded" class="reasoning-content">
                          {{ message.reasoning }}
                        </div>
                      </div>

                      <!-- 工具调用状态 -->
                      <div v-if="message.toolStatus" class="tool-status">
                        <a-spin size="small" />
                        <span>{{ message.toolStatus }}</span>
                      </div>

                      <!-- 消息内容 -->
                      <div class="message-text" v-html="formatMarkdown(message.content)"></div>
                      <div class="message-time">{{ formatTime(message.timestamp) }}</div>

                      <!-- 安全报告 -->
                      <div v-if="message.safetyReport" class="safety-report">
                        <a-divider style="margin: 8px 0;" />
                        <div class="safety-header">
                          <Icon icon="lucide:shield" size="14" :color="message.safetyReport.is_safe ? '#52c41a' : '#ff4d4f'" />
                          <span :style="{ color: message.safetyReport.is_safe ? '#52c41a' : '#ff4d4f' }">
                            {{ message.safetyReport.is_safe ? '安全校验通过' : '安全拦截' }}
                          </span>
                          <a-tag :color="getRiskColor(message.safetyReport.overall_risk)" size="small">
                            {{ message.safetyReport.overall_risk || 'safe' }}
                          </a-tag>
                        </div>
                      </div>

                      <!-- 推理链路 -->
                      <div v-if="message.traceId" class="trace-link">
                        <a-button type="link" size="small" @click="viewTrace(message.traceId)">
                          <Icon icon="lucide:git-branch" size="14" />
                          查看推理链路
                        </a-button>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 加载中状态 -->
                <div v-if="isLoading" class="loading-message">
                  <a-avatar class="message-avatar" style="background-color: #52c41a;">
                    <Icon icon="lucide:bot" size="16" />
                  </a-avatar>
                  <div class="message-content">
                    <a-spin size="small" />
                    <span class="loading-text">{{ loadingText }}</span>
                  </div>
                </div>
              </div>

              <!-- 输入区域 -->
              <div class="chat-input">
                <a-input-search
                  v-model:value="questionInput"
                  placeholder="请输入您的运维问题..."
                  enter-button="发送"
                  size="large"
                  :loading="isLoading"
                  :disabled="isLoading"
                  @search="sendMessage"
                  @keydown.enter.prevent="sendMessage"
                >
                  <template #enterButton>
                    <a-button type="primary" :loading="isLoading">
                      <Icon icon="lucide:send" size="16" />
                    </a-button>
                  </template>
                </a-input-search>
              </div>
            </div>
          </div>
        </a-col>

        <!-- 侧边栏 -->
        <a-col :span="8">
          <!-- 系统信息 -->
          <div class="content-card sidebar-card">
            <div class="card-header">
              <div class="header-title">
                <Icon icon="lucide:monitor" size="18" color="#1890ff" />
                系统概览
              </div>
            </div>
            <div class="card-content">
              <div class="system-overview">
                <div class="kylin-logo">
                  <img src="https://www.kylinos.cn/static/images/logo.png" alt="Kylin OS" class="logo-img" />
                  <span class="os-name">银河麒麟高级服务器操作系统V11</span>
                </div>
                <a-divider />
                <div class="info-grid">
                  <div class="info-row">
                    <span class="info-label">版本号</span>
                    <span class="info-value">V11 (2503)</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">计算机名</span>
                    <span class="info-value">win000k10309</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">内核</span>
                    <span class="info-value kernel-value">linux 6.6.0-32.7.v2505.ky11.loongarch64</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">CPU</span>
                    <span class="info-value">Loongson-3A5000</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">内存</span>
                    <span class="info-value">12GB ({{ systemMemoryAvailable }}可用)</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">桌面</span>
                    <span class="info-value">UKUI</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">用户名</span>
                    <span class="info-value">vmuser</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 历史会话 -->
          <div class="content-card sidebar-card">
            <div class="card-header">
              <div class="header-title">
                <Icon icon="lucide:history" size="18" color="#1890ff" />
                历史会话
              </div>
              <a-button type="link" size="small" @click="fetchSessions">
                <Icon icon="lucide:refresh-cw" size="14" />
              </a-button>
            </div>
            <div class="card-content">
              <div v-if="sessions.length === 0" class="empty-sessions">
                <Icon icon="lucide:inbox" size="32" color="#bfbfbf" />
                <p>暂无历史会话</p>
              </div>
              <div v-else class="session-list">
                <div
                  v-for="session in sessions.slice(0, 10)"
                  :key="session.id"
                  class="session-item"
                  :class="{ active: currentSessionId === session.id }"
                  @click="loadSession(session.id)"
                >
                  <div class="session-row">
                    <Icon icon="lucide:message-circle" size="14" :color="currentSessionId === session.id ? '#1890ff' : '#8c8c8c'" />
                    <span class="session-title">{{ session.title || '未命名会话' }}</span>
                  </div>
                  <div class="session-meta">
                    <span class="msg-count">{{ session.message_count || 0 }} 条消息</span>
                    <span class="session-time">{{ formatDate(session.updated_at) }}</span>
                  </div>
                </div>
                <div v-if="sessions.length > 10" class="more-sessions">
                  <a-button type="link" size="small" @click="goToSessionManage">
                    查看全部 {{ sessions.length }} 个会话
                  </a-button>
                </div>
              </div>
            </div>
          </div>

          <!-- 安全统计 -->
          <div class="content-card sidebar-card" v-if="safetyStats.total_checks > 0">
            <div class="card-header">
              <div class="header-title">
                <Icon icon="lucide:shield-check" size="18" color="#1890ff" />
                安全统计
              </div>
            </div>
            <div class="card-content">
              <div class="safety-stats">
                <div class="stat-row">
                  <span class="stat-label">总检查数</span>
                  <span class="stat-value">{{ safetyStats.total_checks }}</span>
                </div>
                <div class="stat-row">
                  <span class="stat-label">拦截次数</span>
                  <span class="stat-value" style="color: #ff4d4f;">{{ safetyStats.blocked_count }}</span>
                </div>
                <div class="stat-row">
                  <span class="stat-label">拦截率</span>
                  <span class="stat-value">{{ (safetyStats.block_rate * 100).toFixed(1) }}%</span>
                </div>
              </div>
            </div>
          </div>
        </a-col>
      </a-row>
    </div>

    <!-- 推理链路弹窗 -->
    <a-modal
      v-model:open="traceModalVisible"
      title="推理链路详情"
      width="900px"
      :footer="null"
    >
      <TraceVisualization v-if="currentTrace" :trace="currentTrace" />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, reactive } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { message } from 'ant-design-vue';
import { Icon } from '@iconify/vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import {
  agentStream,
  getSystemStatus,
  getSafetyStats,
  getTrace,
  getSessions,
  getSessionMessages,
  deleteSession,
} from '#/api/core/aiops/agent';
import type { ChatMessage, Session, SafetyReport, Trace } from '#/api/core/aiops/agent';
import TraceVisualization from './components/TraceVisualization.vue';

const router = useRouter();
const route = useRoute();

// 响应式数据
const questionInput = ref('');
const isLoading = ref(false);
const currentSessionId = ref('');
const chatHistoryRef = ref<HTMLElement>();
const loadingText = ref('正在思考中...');
const systemStatus = ref('normal');
const systemStatusText = ref('运行正常');
const systemMemoryAvailable = ref('8.1GB');

// 聊天历史
const chatHistory = ref<ChatMessage[]>([]);

// 会话列表
const sessions = ref<Session[]>([]);

// 安全统计
const safetyStats = reactive({
  total_checks: 0,
  blocked_count: 0,
  passed_count: 0,
  block_rate: 0,
  risk_distribution: {} as Record<string, number>,
});

// 推理链路弹窗
const traceModalVisible = ref(false);
const currentTrace = ref<Trace | null>(null);

// 快捷问题
const quickQuestions = ref([
  '查看系统状态',
  '检查磁盘使用情况',
  '查看运行中的进程',
  '检查网络连接状态',
]);

// 获取风险颜色
const getRiskColor = (risk?: string) => {
  if (!risk) return 'green';
  const r = risk.toLowerCase();
  if (r === 'critical' || r === 'high') return 'red';
  if (r === 'medium') return 'orange';
  if (r === 'low') return 'blue';
  return 'green';
};

// 获取步骤样式
const getStepClass = (step: string) => {
  const map: Record<string, string> = {
    INIT: 'init',
    ENVIRONMENT_SENSE: 'sense',
    INTENT_ANALYSIS: 'analysis',
    SAFETY_VALIDATION: 'safety',
    TOOL_EXECUTION: 'tool',
    FINAL_DECISION: 'decision',
  };
  return map[step] || 'default';
};

// 获取步骤名称
const getStepName = (step: string) => {
  const map: Record<string, string> = {
    INIT: '接收指令',
    ENVIRONMENT_SENSE: '环境感知',
    INTENT_ANALYSIS: '意图分析',
    SAFETY_VALIDATION: '安全校验',
    TOOL_EXECUTION: '工具执行',
    FINAL_DECISION: '最终决策',
  };
  return map[step] || step;
};

// 查看推理链路
const viewTrace = async (traceId: string) => {
  try {
    const res = await getTrace(traceId);
    currentTrace.value = res.trace;
    traceModalVisible.value = true;
  } catch (e) {
    message.error('获取推理链路失败');
  }
};

// 发送消息（流式）
const sendMessage = async () => {
  if (!questionInput.value.trim() || isLoading.value) {
    return;
  }

  const question = questionInput.value.trim();
  questionInput.value = '';

  // 添加用户消息到历史
  const userMessage: ChatMessage = {
    id: Date.now(),
    role: 'user',
    content: question,
    timestamp: new Date().toISOString(),
  };
  chatHistory.value.push(userMessage);

  await nextTick();
  scrollToBottom();

  isLoading.value = true;
  loadingText.value = '正在分析...';

  // 创建AI占位消息
  const aiMessage: ChatMessage & { _expanded?: boolean } = {
    id: Date.now() + 1,
    role: 'assistant',
    content: '',
    timestamp: new Date().toISOString(),
    _expanded: false,
  };
  chatHistory.value.push(aiMessage);

  try {
    const response = await agentStream({
      prompt: question,
      session_id: currentSessionId.value || null,
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    if (!reader) {
      throw new Error('无法读取流式响应');
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data: ')) continue;
        const data = trimmed.slice(6);
        if (data === '[DONE]') {
          isLoading.value = false;
          break;
        }

        try {
          const chunk = JSON.parse(data);

          if (chunk.content) {
            aiMessage.content += chunk.content;
          }
          if (chunk.reasoning) {
            if (!aiMessage.reasoning) aiMessage.reasoning = '';
            aiMessage.reasoning += chunk.reasoning;
          }
          if (chunk.status === 'tool_calls' && chunk.tools) {
            aiMessage.toolStatus = `正在执行工具: ${chunk.tools.join(', ')}`;
            loadingText.value = `执行工具: ${chunk.tools.join(', ')}`;
          }
          if (chunk.done) {
            isLoading.value = false;
          }
          if (chunk.session_id) {
            currentSessionId.value = chunk.session_id;
          }
          if (chunk.trace_id) {
            aiMessage.traceId = chunk.trace_id;
          }
          if (chunk.safety_report) {
            aiMessage.safetyReport = chunk.safety_report as SafetyReport;
          }
          if (chunk.error) {
            aiMessage.content += `\n\n[错误] ${chunk.error}`;
            isLoading.value = false;
          }

          await nextTick();
          scrollToBottom();
        } catch {
          // 忽略解析错误
        }
      }
    }

    // 清除工具状态
    aiMessage.toolStatus = undefined;
    isLoading.value = false;

    // 刷新安全统计
    await fetchSafetyStats();
    // 刷新会话列表
    await fetchSessions();

  } catch (error: any) {
    isLoading.value = false;
    aiMessage.content = `请求失败: ${error.message || '未知错误'}`;
    message.error(`发送失败: ${error.message}`);
  }

  await nextTick();
  scrollToBottom();
};

// 快捷问题
const askQuickQuestion = (question: string) => {
  questionInput.value = question;
  sendMessage();
};

// 清空会话
const clearSession = () => {
  chatHistory.value = [];
  currentSessionId.value = '';
  message.success('会话已清空');
};

// 跳转到会话管理
const goToSessionManage = () => {
  router.push('/assistant/session');
};

// 格式化时间
const formatTime = (timestamp?: string) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  });
};

// 格式化日期（用于会话列表）
const formatDate = (timestamp?: string) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
  });
};

// 格式化Markdown
const formatMarkdown = (content?: string) => {
  if (!content) return '';
  const html = marked(content);
  return DOMPurify.sanitize(html as string);
};

// 滚动到底部
const scrollToBottom = () => {
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight;
  }
};

// 获取系统状态
const fetchSystemStatus = async () => {
  try {
    const res = await getSystemStatus();
    const data = res.data;
    if (data.memory) {
      const total = data.memory.total || 12884901888;
      const available = data.memory.available || 0;
      const availGB = (available / 1024 / 1024 / 1024).toFixed(1);
      const totalGB = (total / 1024 / 1024 / 1024).toFixed(0);
      systemMemoryAvailable.value = `${availGB}GB`;
    }
  } catch (e) {
    // 使用默认值
  }
};

// 获取安全统计
const fetchSafetyStats = async () => {
  try {
    const res = await getSafetyStats();
    Object.assign(safetyStats, res);
  } catch (e) {
    // 忽略错误
  }
};

// 获取会话列表
const fetchSessions = async () => {
  try {
    const res = await getSessions();
    sessions.value = res.sessions || [];
  } catch (e) {
    // 忽略错误
  }
};

// 加载会话消息
const loadSession = async (sessionId: string) => {
  try {
    const res = await getSessionMessages(sessionId);
    chatHistory.value = res.messages.map((msg: any) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      timestamp: msg.timestamp,
      safetyReport: msg.safety_report,
      traceId: msg.trace_id,
    }));
    currentSessionId.value = sessionId;
  } catch (e) {
    message.error('加载会话失败');
  }
};

// 页面初始化
onMounted(() => {
  fetchSystemStatus();
  fetchSafetyStats();
  fetchSessions();

  // 如果URL带有session_id参数，自动加载该会话
  const sessionIdFromQuery = route.query.session_id as string;
  if (sessionIdFromQuery) {
    loadSession(sessionIdFromQuery);
  }
});
</script>

<style scoped>
.query-container {
  padding: 24px;
  background-color: var(--ant-background-color-light, #fafafa);
  min-height: 100vh;
}

/* 页面头部 */
.query-container .page-header {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
}

.query-container .header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.query-container .header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.query-container .header-icon {
  font-size: 32px;
  color: #1890ff;
}

.query-container .header-text {
  display: flex;
  flex-direction: column;
}

.query-container .page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #262626;
  line-height: 1.2;
}

.query-container .page-subtitle {
  color: #8c8c8c;
  margin: 0;
  font-size: 14px;
  margin-top: 4px;
}

.query-container .header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* 内容区域 */
.page-content {
  .content-card {
    background: var(--bg-color-white, #ffffff);
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    height: calc(100vh - 200px);
  }

  .sidebar-card {
    height: auto;
    margin-bottom: 24px;
    min-height: auto;

    &:last-child {
      margin-bottom: 0;
    }
  }

  .card-header {
    padding: 16px 24px;
    border-bottom: 1px solid var(--border-color, #f0f0f0);
    background: var(--bg-color-light, #fafafa);
  }

  .header-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 500;
    color: var(--text-color-primary, #262626);
  }

  .card-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .chat-history {
    flex: 1;
    padding: 16px 24px;
    overflow-y: auto;

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 300px;
      color: var(--text-color-tertiary, #bfbfbf);

      p {
        margin: 16px 0 0 0;
        font-size: 14px;
      }

      .quick-actions {
        margin-top: 16px;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: center;
      }

      .quick-action-btn {
        font-size: 13px;
      }
    }

    .message-item {
      margin-bottom: 24px;

      &:last-child {
        margin-bottom: 0;
      }
    }

    .user-message {
      display: flex;
      justify-content: flex-end;
      align-items: flex-start;
      gap: 12px;

      .message-content {
        max-width: 70%;

        .message-text {
          background: var(--primary-color, #1890ff);
          color: #ffffff;
          padding: 12px 16px;
          border-radius: 16px;
          border-bottom-right-radius: 4px;
          word-wrap: break-word;
          font-size: 14px;
          line-height: 1.5;
        }

        .message-time {
          text-align: right;
          font-size: 12px;
          color: var(--text-color-tertiary, #bfbfbf);
          margin-top: 4px;
        }
      }
    }

    .assistant-message {
      display: flex;
      justify-content: flex-start;
      align-items: flex-start;
      gap: 12px;

      .message-content {
        max-width: 70%;

        .reasoning-block {
          margin-bottom: 8px;
          border: 1px solid #e8e8e8;
          border-radius: 8px;
          overflow: hidden;
          background: #fafafa;

          .reasoning-header {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 8px 12px;
            font-size: 12px;
            color: #8c8c8c;
            cursor: pointer;
            user-select: none;

            &:hover {
              background: #f0f0f0;
            }
          }

          .reasoning-content {
            padding: 8px 12px;
            font-size: 13px;
            color: #595959;
            line-height: 1.6;
            white-space: pre-wrap;
            border-top: 1px solid #e8e8e8;
          }
        }

        .tool-status {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          margin-bottom: 8px;
          background: #e6f7ff;
          border-radius: 8px;
          font-size: 13px;
          color: #1890ff;
        }

        .message-text {
          background: var(--bg-color-light, #fafafa);
          color: var(--text-color-primary, #262626);
          padding: 12px 16px;
          border-radius: 16px;
          border-bottom-left-radius: 4px;
          word-wrap: break-word;
          font-size: 14px;
          line-height: 1.5;
          border: 1px solid var(--border-color, #f0f0f0);

          :deep(h1),
          :deep(h2),
          :deep(h3),
          :deep(h4),
          :deep(h5),
          :deep(h6) {
            margin: 8px 0 4px 0;
            font-weight: 600;
          }

          :deep(p) {
            margin: 8px 0;
            line-height: 1.6;
          }

          :deep(ul),
          :deep(ol) {
            margin: 8px 0;
            padding-left: 20px;
          }

          :deep(code) {
            background: #f5f5f5;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: monospace;
          }

          :deep(pre) {
            background: #f5f5f5;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 8px 0;
          }
        }

        .message-time {
          font-size: 12px;
          color: var(--text-color-tertiary, #bfbfbf);
          margin-top: 4px;
        }

        .safety-report {
          .safety-header {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
          }
        }

        .trace-link {
          margin-top: 4px;
        }
      }
    }

    .loading-message {
      display: flex;
      justify-content: flex-start;
      align-items: center;
      gap: 12px;

      .message-content {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .loading-text {
        color: var(--text-color-secondary, #8c8c8c);
        font-size: 14px;
      }
    }
  }

  .chat-input {
    padding: 16px 24px;
    background: var(--bg-color-light, #fafafa);
    border-top: 1px solid var(--border-color, #f0f0f0);
  }
}

/* 侧边栏样式 */
.sidebar-card .card-content {
  padding: 16px 24px;
}

.system-overview {
  .kylin-logo {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;

    .logo-img {
      width: 40px;
      height: 40px;
    }

    .os-name {
      font-size: 14px;
      font-weight: 600;
      color: #262626;
    }
  }

  .info-grid {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #f0f0f0;

    &:last-child {
      border-bottom: none;
    }
  }

  .info-label {
    font-size: 13px;
    color: #8c8c8c;
  }

  .info-value {
    font-size: 13px;
    color: #262626;
    font-weight: 500;
    text-align: right;
    max-width: 60%;
    word-break: break-all;
  }

  .kernel-value {
    font-size: 11px;
    font-family: monospace;
  }
}

.info-item {
  margin-bottom: 16px;

  &:last-child {
    margin-bottom: 0;
  }
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-color-secondary, #8c8c8c);
  margin-bottom: 4px;
}

.form-value {
  font-size: 13px;
  color: var(--text-color-primary, #262626);
  word-break: break-all;
}

.safety-stats {
  .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;

    &:last-child {
      border-bottom: none;
    }
  }

  .stat-label {
    font-size: 13px;
    color: #8c8c8c;
  }

  .stat-value {
    font-size: 14px;
    font-weight: 600;
    color: #262626;
  }
}

/* 会话列表 */
.empty-sessions {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
  color: #bfbfbf;

  p {
    margin: 8px 0 0 0;
    font-size: 13px;
  }
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;

  &:hover {
    background: #f5f5f5;
  }

  &.active {
    background: #e6f7ff;
    border-color: #91d5ff;
  }
}

.session-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.session-title {
  font-size: 13px;
  font-weight: 500;
  color: #262626;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #8c8c8c;
  padding-left: 22px;
}

.msg-count {
  color: #52c41a;
}

.session-time {
  color: #bfbfbf;
}

.more-sessions {
  text-align: center;
  padding: 8px 0;
}



/* 响应式调整 */
@media (max-width: 1200px) {
  .page-content {
    :deep(.ant-col:first-child) {
      width: 100% !important;
      flex: 0 0 100% !important;
      max-width: 100% !important;
    }

    :deep(.ant-col:last-child) {
      display: none;
    }
  }
}

/* 滚动条样式 */
.chat-history::-webkit-scrollbar {
  width: 6px;
}

.chat-history::-webkit-scrollbar-track {
  background: var(--bg-color-light, #fafafa);
  border-radius: 3px;
}

.chat-history::-webkit-scrollbar-thumb {
  background: var(--border-color-dark, #d9d9d9);
  border-radius: 3px;
}

.chat-history::-webkit-scrollbar-thumb:hover {
  background: var(--text-color-tertiary, #bfbfbf);
}
</style>
