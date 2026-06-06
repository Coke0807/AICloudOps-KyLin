<template>
  <div class="session-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon">
            <Icon icon="lucide:users" size="48" color="#1890ff" />
          </div>
          <div class="header-text">
            <h1 class="page-title">会话管理</h1>
            <p class="page-subtitle">查看和管理智能助手的对话历史记录</p>
          </div>
        </div>
        <div class="header-actions">
          <a-space>
            <a-button type="default" @click="fetchSessions" :loading="loading">
              <Icon icon="lucide:refresh-cw" size="16" />
              刷新
            </a-button>
            <a-button type="primary" @click="createNewSession">
              <Icon icon="lucide:plus" size="16" />
              新建会话
            </a-button>
          </a-space>
        </div>
      </div>
    </div>

    <div class="session-content">
      <!-- 统计卡片 -->
      <a-row :gutter="16" class="stats-row">
        <a-col :span="6">
          <div class="stat-card">
            <div class="stat-icon" style="background: #e6f7ff;">
              <Icon icon="lucide:message-square" size="24" color="#1890ff" />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ sessions.length }}</div>
              <div class="stat-label">总会话数</div>
            </div>
          </div>
        </a-col>
        <a-col :span="6">
          <div class="stat-card">
            <div class="stat-icon" style="background: #f6ffed;">
              <Icon icon="lucide:check-circle" size="24" color="#52c41a" />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ totalMessages }}</div>
              <div class="stat-label">总消息数</div>
            </div>
          </div>
        </a-col>
        <a-col :span="6">
          <div class="stat-card">
            <div class="stat-icon" style="background: #fff7e6;">
              <Icon icon="lucide:shield" size="24" color="#fa8c16" />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ safeSessions }}</div>
              <div class="stat-label">安全会话</div>
            </div>
          </div>
        </a-col>
        <a-col :span="6">
          <div class="stat-card">
            <div class="stat-icon" style="background: #f9f0ff;">
              <Icon icon="lucide:clock" size="24" color="#722ed1" />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ todaySessions }}</div>
              <div class="stat-label">今日会话</div>
            </div>
          </div>
        </a-col>
      </a-row>

      <!-- 会话列表 -->
      <div class="content-card">
        <div class="card-header">
          <div class="header-title">
            <Icon icon="lucide:history" size="18" color="#1890ff" />
            会话列表
          </div>
          <div class="header-actions">
            <a-input-search
              v-model:value="searchKeyword"
              placeholder="搜索会话..."
              style="width: 240px"
              allow-clear
              @search="onSearch"
            />
          </div>
        </div>

        <div class="card-content">
          <a-table
            :data-source="filteredSessions"
            :columns="columns"
            :loading="loading"
            :pagination="pagination"
            row-key="id"
            size="middle"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'title'">
                <div class="session-title-cell">
                  <Icon icon="lucide:message-circle" size="16" color="#1890ff" />
                  <span class="title-text">{{ record.title || '未命名会话' }}</span>
                </div>
              </template>

              <template v-if="column.key === 'message_count'">
                <a-badge :count="record.message_count || 0" :number-style="{ backgroundColor: '#52c41a' }" />
              </template>

              <template v-if="column.key === 'preview'">
                <span class="preview-text">{{ record.preview || '无预览内容' }}</span>
              </template>

              <template v-if="column.key === 'time'">
                <div class="time-cell">
                  <div><Icon icon="lucide:calendar" size="12" /> {{ formatDate(record.created_at) }}</div>
                  <div class="update-time"><Icon icon="lucide:clock" size="12" /> {{ formatDate(record.updated_at) }}</div>
                </div>
              </template>

              <template v-if="column.key === 'action'">
                <a-space>
                  <a-button type="link" size="small" @click="viewSession(record)">
                    <Icon icon="lucide:eye" size="14" />
                    查看
                  </a-button>
                  <a-button type="link" size="small" @click="continueSession(record)">
                    <Icon icon="lucide:play" size="14" />
                    继续
                  </a-button>
                  <a-popconfirm
                    title="确定要删除此会话吗？"
                    ok-text="删除"
                    cancel-text="取消"
                    @confirm="removeSession(record.id)"
                  >
                    <a-button type="link" size="small" danger>
                      <Icon icon="lucide:trash-2" size="14" />
                      删除
                    </a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>

            <template #emptyText>
              <div class="empty-state">
                <Icon icon="lucide:inbox" size="48" color="#bfbfbf" />
                <p>暂无会话记录</p>
                <a-button type="primary" size="small" @click="createNewSession">
                  开始新会话
                </a-button>
              </div>
            </template>
          </a-table>
        </div>
      </div>
    </div>

    <!-- 会话详情弹窗 -->
    <a-modal
      v-model:open="detailModalVisible"
      title="会话详情"
      width="700px"
      :footer="null"
    >
      <div v-if="currentSession" class="session-detail">
        <div class="detail-header">
          <div class="detail-title">
            <Icon icon="lucide:message-square" size="20" color="#1890ff" />
            {{ currentSession.title || '未命名会话' }}
          </div>
          <div class="detail-meta">
            <span>ID: {{ currentSession.id }}</span>
            <a-divider type="vertical" />
            <span>{{ currentSession.message_count || 0 }} 条消息</span>
          </div>
        </div>

        <a-divider />

        <div class="messages-list" v-if="sessionMessages.length > 0">
          <div
            v-for="(msg, idx) in sessionMessages"
            :key="idx"
            class="detail-message"
            :class="msg.role"
          >
            <div class="message-header">
              <a-avatar
                :style="{ backgroundColor: msg.role === 'user' ? '#1890ff' : '#52c41a' }"
                size="small"
              >
                <Icon :icon="msg.role === 'user' ? 'lucide:user' : 'lucide:bot'" size="14" />
              </a-avatar>
              <span class="role-label">{{ msg.role === 'user' ? '用户' : '助手' }}</span>
              <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
            </div>
            <div class="message-body" v-html="formatMarkdown(msg.content)"></div>

            <!-- 安全报告 -->
            <div v-if="msg.safety_report" class="msg-safety">
              <a-divider style="margin: 8px 0;" />
              <div class="safety-header">
                <Icon
                  icon="lucide:shield"
                  size="14"
                  :color="msg.safety_report.is_safe ? '#52c41a' : '#ff4d4f'"
                />
                <span :style="{ color: msg.safety_report.is_safe ? '#52c41a' : '#ff4d4f' }">
                  {{ msg.safety_report.is_safe ? '安全校验通过' : '安全拦截' }}
                </span>
                <a-tag :color="getRiskColor(msg.safety_report.overall_risk)" size="small">
                  {{ msg.safety_report.overall_risk || 'safe' }}
                </a-tag>
              </div>
            </div>

            <!-- 推理链路 -->
            <div v-if="msg.trace_id" class="msg-trace">
              <a-button type="link" size="small" @click="viewTrace(msg.trace_id)">
                <Icon icon="lucide:git-branch" size="14" />
                查看推理链路
              </a-button>
            </div>
          </div>
        </div>

        <div v-else class="empty-messages">
          <Icon icon="lucide:message-circle" size="32" color="#bfbfbf" />
          <p>该会话暂无消息</p>
        </div>
      </div>
    </a-modal>

    <!-- 推理链路弹窗 -->
    <a-modal
      v-model:open="traceModalVisible"
      title="推理链路详情"
      width="800px"
      :footer="null"
    >
      <div v-if="currentTrace" class="trace-detail">
        <div class="trace-header">
          <span class="trace-id">链路ID: {{ currentTrace.trace_id }}</span>
          <span class="trace-time">{{ formatTime(currentTrace.start_time) }}</span>
        </div>
        <div class="trace-prompt">用户输入: {{ currentTrace.user_prompt }}</div>

        <div class="timeline">
          <div
            v-for="(step, idx) in currentTrace.steps"
            :key="idx"
            class="timeline-item"
          >
            <div class="timeline-dot" :class="getStepClass(step.step)" />
            <div class="timeline-content">
              <div class="step-header">
                <span class="step-name">{{ getStepName(step.step) }}</span>
                <span class="step-time">{{ formatTime(step.timestamp) }}</span>
              </div>
              <div class="step-data">
                <pre v-if="step.data">{{ JSON.stringify(step.data, null, 2) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import { Icon } from '@iconify/vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import {
  getSessions,
  getSessionMessages,
  deleteSession,
  getTrace,
} from '#/api/core/aiops/agent';
import type { Session, ChatMessage, Trace } from '#/api/core/aiops/agent';

const router = useRouter();

// 响应式数据
const loading = ref(false);
const sessions = ref<Session[]>([]);
const searchKeyword = ref('');
const detailModalVisible = ref(false);
const traceModalVisible = ref(false);
const currentSession = ref<Session | null>(null);
const sessionMessages = ref<ChatMessage[]>([]);
const currentTrace = ref<Trace | null>(null);

// 表格列定义
const columns = [
  {
    title: '会话标题',
    key: 'title',
    dataIndex: 'title',
    width: 200,
  },
  {
    title: '消息数',
    key: 'message_count',
    dataIndex: 'message_count',
    width: 100,
    align: 'center' as const,
  },
  {
    title: '预览',
    key: 'preview',
    dataIndex: 'preview',
    ellipsis: true,
  },
  {
    title: '时间',
    key: 'time',
    width: 220,
  },
  {
    title: '操作',
    key: 'action',
    width: 220,
    align: 'center' as const,
  },
];

// 分页配置
const pagination = {
  pageSize: 10,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
};

// 过滤后的会话列表
const filteredSessions = computed(() => {
  if (!searchKeyword.value.trim()) {
    return sessions.value;
  }
  const kw = searchKeyword.value.toLowerCase();
  return sessions.value.filter(
    (s) =>
      (s.title && s.title.toLowerCase().includes(kw)) ||
      (s.id && s.id.toLowerCase().includes(kw)) ||
      (s.preview && s.preview.toLowerCase().includes(kw))
  );
});

// 统计计算
const totalMessages = computed(() =>
  sessions.value.reduce((sum, s) => sum + (s.message_count || 0), 0)
);

const safeSessions = computed(() =>
  sessions.value.filter((s) => (s.message_count || 0) > 0).length
);

const todaySessions = computed(() => {
  const today = new Date().toDateString();
  return sessions.value.filter((s) => {
    if (!s.created_at) return false;
    return new Date(s.created_at).toDateString() === today;
  }).length;
});

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

// 格式化日期
const formatDate = (timestamp?: string) => {
  if (!timestamp) return '-';
  const date = new Date(timestamp);
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// 格式化时间
const formatTime = (timestamp?: string) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

// 格式化Markdown
const formatMarkdown = (content?: string) => {
  if (!content) return '';
  const html = marked(content);
  return DOMPurify.sanitize(html as string);
};

// 搜索
const onSearch = () => {
  // filteredSessions 是计算属性，自动响应
};

// 获取会话列表
const fetchSessions = async () => {
  loading.value = true;
  try {
    const res = await getSessions(100);
    sessions.value = res.sessions || [];
  } catch (e: any) {
    message.error(`获取会话列表失败: ${e.message}`);
  } finally {
    loading.value = false;
  }
};

// 查看会话详情
const viewSession = async (session: Session) => {
  currentSession.value = session;
  detailModalVisible.value = true;
  sessionMessages.value = [];

  try {
    const res = await getSessionMessages(session.id);
    sessionMessages.value = res.messages || [];
  } catch (e: any) {
    message.error(`加载会话消息失败: ${e.message}`);
  }
};

// 继续会话
const continueSession = (session: Session) => {
  router.push({
    path: '/assistant/query',
    query: { session_id: session.id },
  });
};

// 删除会话
const removeSession = async (sessionId: string) => {
  try {
    await deleteSession(sessionId);
    message.success('会话已删除');
    await fetchSessions();
  } catch (e: any) {
    message.error(`删除失败: ${e.message}`);
  }
};

// 新建会话
const createNewSession = () => {
  router.push('/assistant/query');
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

// 页面初始化
onMounted(() => {
  fetchSessions();
});
</script>

<style scoped>
.session-container {
  padding: 24px;
  background-color: var(--ant-background-color-light, #fafafa);
  min-height: 100vh;
}

/* 页面头部 */
.session-container .page-header {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
}

.session-container .header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.session-container .header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.session-container .header-icon {
  font-size: 32px;
  color: #1890ff;
}

.session-container .header-text {
  display: flex;
  flex-direction: column;
}

.session-container .page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #262626;
  line-height: 1.2;
}

.session-container .page-subtitle {
  color: #8c8c8c;
  margin: 0;
  font-size: 14px;
  margin-top: 4px;
}

.session-container .header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* 统计卡片 */
.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid #f0f0f0;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #262626;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #8c8c8c;
  margin-top: 4px;
}

/* 内容卡片 */
.content-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.card-header {
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
  color: #262626;
}

.card-content {
  padding: 0;
}

/* 表格样式 */
.session-title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-text {
  font-weight: 500;
  color: #262626;
}

.preview-text {
  color: #8c8c8c;
  font-size: 13px;
}

.time-cell {
  font-size: 12px;
  color: #8c8c8c;
}

.time-cell .update-time {
  margin-top: 2px;
  color: #bfbfbf;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
  color: #bfbfbf;
}

.empty-state p {
  margin: 12px 0;
}

/* 会话详情弹窗 */
.session-detail {
  max-height: 60vh;
  overflow-y: auto;
}

.detail-header {
  margin-bottom: 16px;
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #262626;
}

.detail-meta {
  margin-top: 8px;
  font-size: 12px;
  color: #8c8c8c;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-message {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;
}

.detail-message.user {
  background: #e6f7ff;
  border-color: #91d5ff;
}

.detail-message.assistant {
  background: #f6ffed;
  border-color: #b7eb8f;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.role-label {
  font-size: 13px;
  font-weight: 500;
  color: #262626;
}

.msg-time {
  font-size: 11px;
  color: #8c8c8c;
  margin-left: auto;
}

.message-body {
  font-size: 14px;
  line-height: 1.6;
  color: #262626;
}

.message-body :deep(p) {
  margin: 4px 0;
}

.message-body :deep(code) {
  background: #f5f5f5;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 12px;
}

.message-body :deep(pre) {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
}

.msg-safety {
  margin-top: 8px;
}

.safety-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.msg-trace {
  margin-top: 4px;
}

.empty-messages {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
  color: #bfbfbf;
}

/* 推理链路 */
.trace-detail {
  max-height: 60vh;
  overflow-y: auto;
}

.trace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.trace-id {
  font-size: 12px;
  color: #8c8c8c;
  font-family: monospace;
}

.trace-time {
  font-size: 12px;
  color: #8c8c8c;
}

.trace-prompt {
  font-size: 14px;
  color: #262626;
  margin-bottom: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}

.timeline {
  position: relative;
  padding-left: 24px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #e8e8e8;
}

.timeline-item {
  position: relative;
  margin-bottom: 16px;
}

.timeline-dot {
  position: absolute;
  left: -20px;
  top: 4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #1890ff;
  border: 2px solid #fff;
  box-shadow: 0 0 0 2px #1890ff;
}

.timeline-dot.init {
  background: #8c8c8c;
  box-shadow: 0 0 0 2px #8c8c8c;
}

.timeline-dot.sense {
  background: #1890ff;
  box-shadow: 0 0 0 2px #1890ff;
}

.timeline-dot.analysis {
  background: #faad14;
  box-shadow: 0 0 0 2px #faad14;
}

.timeline-dot.safety {
  background: #ff4d4f;
  box-shadow: 0 0 0 2px #ff4d4f;
}

.timeline-dot.tool {
  background: #52c41a;
  box-shadow: 0 0 0 2px #52c41a;
}

.timeline-dot.decision {
  background: #722ed1;
  box-shadow: 0 0 0 2px #722ed1;
}

.timeline-content {
  background: #fafafa;
  border-radius: 8px;
  padding: 12px;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.step-name {
  font-size: 14px;
  font-weight: 600;
  color: #262626;
}

.step-time {
  font-size: 11px;
  color: #8c8c8c;
}

.step-data pre {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 200px;
  overflow-y: auto;
  margin: 0;
}

/* 滚动条 */
.session-detail::-webkit-scrollbar,
.trace-detail::-webkit-scrollbar {
  width: 6px;
}

.session-detail::-webkit-scrollbar-thumb,
.trace-detail::-webkit-scrollbar-thumb {
  background: #d9d9d9;
  border-radius: 3px;
}
</style>
