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
            <a-button @click="clearSession" type="default" class="header-action-btn">
              <template #icon>
                <Icon icon="lucide:trash-2" size="16" />
              </template>
              <span class="btn-text">清空</span>
            </a-button>
            <a-button @click="goToSessionManage" type="primary" class="header-action-btn primary">
              <template #icon>
                <Icon icon="lucide:users" size="16" />
              </template>
              <span class="btn-text">会话</span>
            </a-button>
          </a-space>
        </div>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="page-content">
      <a-row :gutter="24">
        <!-- 聊天区域 -->
        <a-col :span="16" class="chat-col">
          <div class="content-card">
            <div class="card-header">
              <div class="header-title">
                <Icon icon="lucide:message-circle" size="18" color="#1890ff" />
                对话
              </div>
            </div>

            <div class="card-content">
              <!-- 聊天历史 -->
              <div class="chat-history" ref="chatHistoryRef" @scroll="handleChatScroll" @wheel="handleChatWheel">
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

                      <!-- P8: 工具执行状态增强 -->
                      <div v-if="message.toolStatus" class="tool-status">
                        <a-spin size="small" />
                        <span>{{ message.toolStatus }}</span>
                      </div>
                      <div v-if="message.toolDetails && message.toolDetails.length > 0" class="tool-details">
                        <div
                          v-for="(tool, tIdx) in message.toolDetails"
                          :key="tIdx"
                          class="tool-detail-item"
                        >
                          <div
                            class="tool-detail-header"
                            :class="{ clickable: true }"
                            @click="toggleToolExpand(index, tIdx)"
                          >
                            <Icon
                              :icon="getToolIcon(tool.name)"
                              size="12"
                              :color="getToolStatus(tool).color"
                            />
                            <span class="tool-name">{{ tool.name }}</span>
                            <span class="tool-status-dot" :style="{ backgroundColor: getToolStatus(tool).color }"></span>
                            <a-tag :color="getToolStatus(tool).tagColor" size="small">
                              {{ getToolStatus(tool).label }}
                            </a-tag>
                            <Icon
                              :icon="isToolExpanded(index, tIdx) ? 'lucide:chevron-up' : 'lucide:chevron-down'"
                              size="14"
                              class="tool-chevron"
                              :class="{ rotated: isToolExpanded(index, tIdx) }"
                            />
                          </div>
                          <div v-show="isToolExpanded(index, tIdx)" class="tool-detail-body">
                            <div v-if="tool.args && Object.keys(tool.args).length > 0" class="tool-args">
                              <span class="detail-label">参数：</span>
                              <code>{{ JSON.stringify(tool.args) }}</code>
                            </div>
                            <div v-if="tool.result" class="tool-result">
                              <span class="detail-label">结果：</span>
                              <span class="result-summary">{{ summarizeResult(tool.result) }}</span>
                              <a-button
                                v-if="isResultTruncatable(tool.result)"
                                type="link"
                                size="small"
                                class="view-full-btn"
                                @click.stop="openToolResultModal(tool)"
                              >
                                查看完整结果
                              </a-button>
                            </div>
                          </div>
                        </div>
                      </div>

                      <!-- 消息内容 -->
                      <div class="message-text" v-html="formatMarkdown(message.content)"></div>
                      <div class="message-time">{{ formatTime(message.timestamp) }}</div>

                      <!-- T2: 提示词注入攻击专项告警 -->
                      <div
                        v-if="message.safetyReport && message.safetyReport.layers?.injection?.passed === false"
                        class="injection-alert"
                      >
                        <div class="injection-alert-content">
                          <Icon icon="lucide:bug" size="20" />
                          <span class="injection-alert-text">
                            ⚠️ 检测到提示词注入攻击（Prompt Injection），拒绝执行该恶意代码
                          </span>
                        </div>
                        <div v-if="message.safetyReport.layers?.injection?.patterns_found?.length" class="injection-patterns">
                          <span class="injection-patterns-label">命中规则：</span>
                          <a-tag v-for="(p, pi) in message.safetyReport.layers.injection.patterns_found" :key="pi" color="red" size="small">
                            {{ p }}
                          </a-tag>
                        </div>
                      </div>

                      <!-- T5: 安全拦截精简条 + Modal 查看详情 -->
                      <div v-if="message.safetyReport && !message.safetyReport.is_safe" class="danger-banner">
                        <div class="danger-banner-content">
                          <Icon icon="lucide:shield-alert" size="18" />
                          <span class="danger-banner-text">
                            【安全护栏拦截】检测到高危操作，已阻止执行
                          </span>
                          <a-tag color="red" size="small">
                            {{ (message.safetyReport.overall_risk || 'critical').toUpperCase() }}
                          </a-tag>
                          <a-button type="link" size="small" class="danger-detail-btn" @click="openSafetyDetailModal(message.safetyReport)">
                            <Icon icon="lucide:eye" size="14" />
                            查看详情
                          </a-button>
                        </div>
                      </div>

                      <!-- 安全报告详情（校验通过时） -->
                      <div v-if="message.safetyReport && message.safetyReport.is_safe" class="safety-report">
                        <a-divider style="margin: 8px 0;" />
                        <div class="safety-header">
                          <Icon icon="lucide:shield" size="14" color="#52c41a" />
                          <span style="color: #52c41a;">安全校验通过</span>
                          <a-tag :color="getRiskColor(message.safetyReport.overall_risk)" size="small">
                            {{ message.safetyReport.overall_risk || 'safe' }}
                          </a-tag>
                        </div>
                      </div>

                      <!-- P7: 推理链精简节点 + 完整链路入口 -->
                      <div v-if="message.traceId" class="reasoning-pipeline">
                        <div class="pipeline-steps">
                          <div
                            v-for="step in getReasoningSteps(message)"
                            :key="step.label"
                            class="pipeline-step"
                            :class="step.status"
                          >
                            <Icon :icon="step.icon" size="12" />
                            <span>{{ step.label }}</span>
                          </div>
                        </div>
                        <!-- 完整链路入口：从原本的 type="link" 升级为带图标的实体按钮，
                            在对话气泡内更醒目，避免被忽略。 -->
                        <a-button
                          type="primary"
                          ghost
                          size="small"
                          class="view-full-chain-btn"
                          :loading="viewTraceLoading[message.traceId]"
                          @click="viewTrace(message.traceId)"
                        >
                          <Icon icon="lucide:git-branch" size="14" style="margin-right: 4px;" />
                          <span>查看完整链路</span>
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
            <!-- 回到最新按钮：用户上滑浏览历史时出现 -->
            <button
              v-show="!isAtBottom && chatHistory.length > 0"
              class="scroll-to-bottom-btn"
              type="button"
              aria-label="回到最新消息"
              @click="resetScrollToBottom"
            >
              <Icon icon="lucide:arrow-down" size="16" />
              <span>回到最新</span>
            </button>
          </div>
        </a-col>

        <!-- 侧边栏 -->
        <a-col :span="8" class="sidebar-col">
          <!-- 系统信息 -->
          <div class="content-card sidebar-card system-overview-card">
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
                    <span class="info-value kernel-value">linux 6.6.0-32.7.v2025.ky11.loongarch64</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">CPU</span>
                    <span class="info-value">Loongson-3A5000</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">架构</span>
                    <span class="info-value"><a-tag color="purple" size="small">LoongArch</a-tag></span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">内存</span>
                    <span class="info-value">12GB</span>
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
          <div class="content-card sidebar-card history-card">
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
          <div class="content-card sidebar-card">
            <div class="card-header">
              <div class="header-title">
                <Icon icon="lucide:shield-check" size="18" color="#1890ff" />
                安全统计
              </div>
            </div>
            <div class="card-content">
              <div class="safety-stats">
                <div class="stat-block total">
                  <div class="stat-num">{{ safetyStats.total_checks }}</div>
                  <div class="stat-lbl">总检查数</div>
                </div>
                <div class="stat-block blocked">
                  <div class="stat-num">{{ safetyStats.blocked_count }}</div>
                  <div class="stat-lbl">已拦截</div>
                </div>
                <div class="stat-block passed">
                  <div class="stat-num">{{ safetyStats.passed_count }}</div>
                  <div class="stat-lbl">已通过</div>
                </div>
                <div class="stat-block rate">
                  <div class="stat-num">{{ formatBlockRate(safetyStats.block_rate) }}</div>
                  <div class="stat-lbl">拦截率</div>
                </div>
              </div>
            </div>
          </div>
        </a-col>
      </a-row>
    </div>

    <!-- P7: 推理链路详情 Modal（响应式 + 全链路状态处理）
         - 移动端：宽度 95%，全屏高度
         - 桌面端：最大宽度 960px，居中显示
         - 状态机：loading / error / empty / ready -->
    <a-modal
      v-model:open="traceModalVisible"
      :width="traceModalWidth"
      :footer="null"
      :destroy-on-close="true"
      :mask-closable="!viewTraceLoadingGlobal"
      :keyboard="true"
      centered
      wrap-class-name="trace-modal-wrap"
      @cancel="handleTraceModalClose"
    >
      <template #title>
        <div class="trace-modal-title">
          <Icon icon="lucide:git-branch" size="18" color="#722ed1" style="margin-right: 8px;" />
          <span>推理链路详情</span>
          <a-tag
            v-if="currentTrace"
            color="purple"
            size="small"
            style="margin-left: 8px;"
          >
            {{ currentTrace.steps?.length || 0 }} 步
          </a-tag>
        </div>
      </template>

      <!-- 工具栏：跳转全链路页 + 展开全部 / 收起全部 -->
      <div v-if="currentTrace && !viewTraceLoadingGlobal && !traceLoadError" class="trace-modal-toolbar">
        <a-button
          type="link"
          size="small"
          class="open-full-page-link"
          @click="openInReasoningPage(currentTrace.trace_id)"
        >
          <Icon icon="lucide:external-link" size="12" style="margin-right: 2px;" />
          在新页面打开
        </a-button>
      </div>

      <!-- 加载中 -->
      <div v-if="viewTraceLoadingGlobal" class="trace-modal-state trace-modal-loading">
        <a-spin size="large" />
        <p>正在加载完整链路数据…</p>
      </div>

      <!-- 错误：404 / 网络异常 / 解析失败 -->
      <div v-else-if="traceLoadError" class="trace-modal-state trace-modal-error">
        <Icon icon="lucide:alert-triangle" size="56" color="#ff4d4f" />
        <p class="error-title">{{ traceLoadError.title }}</p>
        <p class="error-desc">{{ traceLoadError.desc }}</p>
        <div class="error-actions">
          <a-button type="primary" @click="retryLoadTrace">
            <Icon icon="lucide:rotate-cw" size="14" style="margin-right: 4px;" />
            重试
          </a-button>
          <a-button @click="traceModalVisible = false">关闭</a-button>
        </div>
      </div>

      <!-- 空：链路存在但无步骤（异常流） -->
      <div v-else-if="currentTrace && (!currentTrace.steps || currentTrace.steps.length === 0)" class="trace-modal-state trace-modal-empty">
        <Icon icon="lucide:git-branch" size="56" color="#bfbfbf" />
        <p class="empty-title">该链路暂无步骤记录</p>
        <p class="empty-desc">链路可能已被清理或正在收集中</p>
      </div>

      <!-- 正常：渲染可视化 -->
      <TraceVisualization
        v-else-if="currentTrace"
        :trace="currentTrace"
      />
    </a-modal>

    <!-- T5: 安全护栏详情 Modal -->
    <a-modal
      v-model:open="safetyDetailModalVisible"
      title="触发安全护栏校验"
      :width="640"
      :footer="null"
      centered
    >
      <template v-if="currentSafetyReport">
        <div class="safety-modal-subtitle">
          <a-tag :color="getRiskColor(currentSafetyReport.overall_risk)" size="small">
            {{ (currentSafetyReport.overall_risk || 'unknown').toUpperCase() }}
          </a-tag>
        </div>
        <a-table
          :columns="safetyLayerColumns"
          :data-source="getSafetyLayerData(currentSafetyReport)"
          :pagination="false"
          size="small"
          row-key="key"
          bordered
          :row-class-name="(_record: any, index: number) => getSafetyLayerData(currentSafetyReport!)[index]?.passed ? '' : 'layer-row-failed'"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'layer'">
              <span>{{ record.icon }} {{ record.layer }}</span>
            </template>
            <template v-if="column.dataIndex === 'result'">
              <a-tag :color="record.passed ? 'green' : 'red'" size="small">
                {{ record.passed ? '通过' : '失败' }}
              </a-tag>
            </template>
            <template v-if="column.dataIndex === 'details'">
              <span :class="{ 'detail-failed': !record.passed }">{{ record.details }}</span>
            </template>
          </template>
        </a-table>
      </template>
    </a-modal>

    <!-- P8: 工具结果完整查看 Modal -->
    <a-modal
      v-model:open="toolResultModalVisible"
      :title="`工具执行结果 — ${currentToolResult?.name || ''}`"
      :width="720"
      :footer="null"
      centered
    >
      <template v-if="currentToolResult">
        <div v-if="currentToolResult.args && Object.keys(currentToolResult.args).length > 0" class="tool-modal-section">
          <div class="tool-modal-label">参数</div>
          <pre class="tool-modal-code">{{ JSON.stringify(currentToolResult.args, null, 2) }}</pre>
        </div>
        <div class="tool-modal-section">
          <div class="tool-modal-label">结果</div>
          <pre class="tool-modal-code">{{ typeof currentToolResult.result === 'string' ? currentToolResult.result : JSON.stringify(currentToolResult.result, null, 2) }}</pre>
        </div>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onBeforeUnmount, reactive } from 'vue';
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
import { requestClientAIOps } from '#/api/request';
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

// 智能滚动：仅在用户已停留在底部时才自动滚动
// - isAtBottom: 用户当前是否在底部（距离底部 80px 以内视为在底部）
// - 用户主动上滑浏览历史时，自动滚动会被暂停，避免"抢鼠标"
const isAtBottom = ref(true);
const SCROLL_BOTTOM_THRESHOLD = 80;

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

// P7: 推理链路详情 Modal 状态
// - traceModalVisible: Modal 是否可见
// - viewTraceLoadingGlobal: 全局加载态（控制弹窗内 spinner）
// - viewTraceLoading: 按 traceId 记录每个入口按钮的独立 loading
// - traceLoadError: 错误对象 { title, desc }，null 表示无错误
// - pendingTraceId: 等待加载的 traceId（用于重试）
// - lastTraceId: 当前打开的 traceId（用于重试）
const traceModalVisible = ref(false);
const viewTraceLoadingGlobal = ref(false);
const viewTraceLoading = ref<Record<string, boolean>>({});
const traceLoadError = ref<{ title: string; desc: string } | null>(null);
const pendingTraceId = ref<string | null>(null);
const currentTrace = ref<Trace | null>(null);

// 响应式：基于 window.innerWidth 动态计算 Modal 宽度
// - < 576px (xs): 100% - 16px
// - 576-992px (sm/md): 90%
// - ≥ 992px (lg+): 960px
const traceModalWidth = ref(960);
const updateTraceModalWidth = () => {
  const w = window.innerWidth;
  if (w < 576) traceModalWidth.value = Math.max(320, w - 16);
  else if (w < 992) traceModalWidth.value = Math.round(w * 0.9);
  else traceModalWidth.value = 960;
};

// P7: 打开推理链路详情（带状态机）
const viewTrace = async (traceId: string) => {
  if (!traceId) {
    message.warning('链路 ID 为空，无法加载');
    return;
  }
  // 若已在打开同一个链路，仅聚焦弹窗，不重复请求
  if (traceModalVisible.value && currentTrace.value?.trace_id === traceId && !traceLoadError.value) {
    return;
  }

  // 重置状态
  traceLoadError.value = null;
  currentTrace.value = null;
  pendingTraceId.value = traceId;
  traceModalVisible.value = true;
  viewTraceLoadingGlobal.value = true;
  viewTraceLoading.value[traceId] = true;

  try {
    const res = await getTrace(traceId);
    // 数据防御：后端可能返回 trace: null
    if (!res || !res.trace) {
      throw new Error('EMPTY_RESPONSE');
    }
    currentTrace.value = res.trace;
  } catch (e: any) {
    // 根据状态码/错误信息细分提示
    const status = e?.response?.status;
    if (status === 404 || /not found|资源不存在|404/i.test(String(e?.message || e))) {
      traceLoadError.value = {
        title: '未找到该推理链路',
        desc: `链路 ${truncateText(traceId, 12)} 不存在或已被清理。可前往"推理链路"页查看历史记录。`,
      };
    } else if (status >= 500) {
      traceLoadError.value = {
        title: '服务暂时不可用',
        desc: `后端返回 ${status}，请稍后重试或联系管理员。`,
      };
    } else if (e?.message === 'EMPTY_RESPONSE') {
      traceLoadError.value = {
        title: '响应数据为空',
        desc: '服务端返回为空，可能链路尚未写入完成。',
      };
    } else {
      traceLoadError.value = {
        title: '获取推理链路失败',
        desc: e?.message || '网络异常，请检查连接后重试。',
      };
    }
    // 同时在控制台保留详细错误，便于排查
    // eslint-disable-next-line no-console
    console.error('[viewTrace] failed', e);
    // 顶部通知（避免只靠弹窗内错误）
    message.error(traceLoadError.value.title);
  } finally {
    viewTraceLoadingGlobal.value = false;
    viewTraceLoading.value[traceId] = false;
  }
};

// 重试：使用最近一次失败的 traceId
const retryLoadTrace = () => {
  if (pendingTraceId.value) {
    viewTrace(pendingTraceId.value);
  }
};

// 关闭弹窗：清理状态
const handleTraceModalClose = () => {
  if (viewTraceLoadingGlobal.value) {
    // 正在加载时不允许关闭（视觉上由 mask-closable 控制，这里做兜底）
    return;
  }
  traceModalVisible.value = false;
  // 延迟清理，避免 Modal 关闭动画期间闪烁
  setTimeout(() => {
    currentTrace.value = null;
    traceLoadError.value = null;
    pendingTraceId.value = null;
  }, 200);
};

// 跳转到"推理链路"页（带 trace_id 参数）
const openInReasoningPage = (traceId: string) => {
  router.push({ path: '/assistant/reasoning', query: { trace_id: traceId } });
};

// 文本截断辅助
const truncateText = (s: string, head: number): string => {
  if (!s) return '';
  return s.length > head * 2 + 3 ? `${s.slice(0, head)}…${s.slice(-4)}` : s;
};

// T5: 安全护栏详情 Modal
const safetyDetailModalVisible = ref(false);
const currentSafetyReport = ref<SafetyReport | null>(null);

// P8: 工具详情展开状态（key: `${msgIdx}-${toolIdx}`）
const toolExpanded = reactive<Record<string, boolean>>({});

// P8: 工具结果完整查看 Modal
const toolResultModalVisible = ref(false);
const currentToolResult = ref<{ name: string; args?: any; result: any } | null>(null);

const safetyLayerColumns = [
  { title: '安全层', dataIndex: 'layer', width: 140 },
  { title: '结果', dataIndex: 'result', width: 80, align: 'center' as const },
  { title: '详情', dataIndex: 'details' },
];

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

// T5: 打开安全护栏详情 Modal
const openSafetyDetailModal = (report: SafetyReport) => {
  currentSafetyReport.value = report;
  safetyDetailModalVisible.value = true;
};

// T5: 将 safetyReport.layers 转换为表格数据源
const getSafetyLayerData = (report: SafetyReport) => {
  if (!report?.layers) return [];
  const { layers } = report;

  const items: Array<{
    key: string;
    icon: string;
    layer: string;
    passed: boolean;
    details: string;
  }> = [];

  // 🧹 输入清洗
  if (layers.sanitizer) {
    items.push({
      key: 'sanitizer',
      icon: '🧹',
      layer: '输入清洗',
      passed: layers.sanitizer.passed,
      details: layers.sanitizer.passed
        ? '未发现异常'
        : (layers.sanitizer.modifications || []).join('；'),
    });
  }

  // 🎯 意图分类
  if (layers.intent) {
    const kw = layers.intent.matched_keywords;
    const kwStr = kw
      ? Object.entries(kw).map(([k, v]) => `${k}: ${(v as string[]).join(',')}`).join('；')
      : '';
    items.push({
      key: 'intent',
      icon: '🎯',
      layer: '意图分类',
      passed: layers.intent.passed,
      details: layers.intent.passed
        ? `意图: ${layers.intent.intent || '—'}`
        : `意图: ${layers.intent.intent || '—'}${kwStr ? `，关键词: ${kwStr}` : ''}`,
    });
  }

  // 📊 风险评分
  if (layers.risk_scorer) {
    items.push({
      key: 'risk_scorer',
      icon: '📊',
      layer: '风险评分',
      passed: layers.risk_scorer.passed,
      details: layers.risk_scorer.passed
        ? `评分: ${layers.risk_scorer.score ?? '—'}`
        : `评分: ${layers.risk_scorer.score ?? '—'}，原因: ${(layers.risk_scorer.reasons || []).join('；')}`,
    });
  }

  // 🔒 参数校验
  if (layers.param_validator) {
    items.push({
      key: 'param_validator',
      icon: '🔒',
      layer: '参数校验',
      passed: layers.param_validator.passed,
      details: layers.param_validator.passed
        ? '参数合法'
        : (layers.param_validator.violations || []).join('；'),
    });
  }

  // 🛡️ 注入检测
  if (layers.injection) {
    items.push({
      key: 'injection',
      icon: '🛡️',
      layer: '注入检测',
      passed: layers.injection.passed,
      details: layers.injection.passed
        ? '未检测到注入'
        : (layers.injection.patterns_found || []).join('；'),
    });
  }

  return items;
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

// P7: 获取推理链精简步骤
const getReasoningSteps = (msg: ChatMessage) => {
  const steps = [
    { label: '接收指令', icon: 'lucide:terminal', status: 'done' },
    { label: '环境感知', icon: 'lucide:radar', status: msg.reasoning ? 'done' : 'pending' },
    { label: '意图分析', icon: 'lucide:brain', status: msg.reasoning ? 'done' : 'pending' },
  ];
  if (msg.safetyReport && !msg.safetyReport.is_safe) {
    steps.push({ label: '安全拦截', icon: 'lucide:shield-alert', status: 'blocked' });
  } else if (msg.toolDetails && msg.toolDetails.length > 0) {
    steps.push({ label: '工具执行', icon: 'lucide:wrench', status: 'done' });
    steps.push({ label: '生成报告', icon: 'lucide:file-text', status: 'done' });
  } else if (msg.content) {
    steps.push({ label: '生成回复', icon: 'lucide:file-text', status: 'done' });
  } else {
    steps.push({ label: '处理中', icon: 'lucide:loader', status: 'pending' });
  }
  return steps;
};

// P8: 工具结果摘要
const summarizeResult = (result: any): string => {
  if (!result) return '';
  if (typeof result === 'string') return result.length > 120 ? result.slice(0, 120) + '...' : result;
  const str = JSON.stringify(result);
  return str.length > 120 ? str.slice(0, 120) + '...' : str;
};

// P8: 判断结果是否可截断（即有"查看完整结果"的意义）
const isResultTruncatable = (result: any): boolean => {
  if (!result) return false;
  if (typeof result === 'string') return result.length > 120;
  return JSON.stringify(result).length > 120;
};

// P8: 工具详情展开/折叠切换
const toggleToolExpand = (msgIdx: number, toolIdx: number) => {
  const key = `${msgIdx}-${toolIdx}`;
  toolExpanded[key] = !toolExpanded[key];
};

// P8: 判断工具详情是否展开
const isToolExpanded = (msgIdx: number, toolIdx: number): boolean => {
  return !!toolExpanded[`${msgIdx}-${toolIdx}`];
};

// P8: 按工具名称返回分类图标
const getToolIcon = (toolName: string): string => {
  const systemTools = ['get_system_status', 'get_process_list', 'get_process_detail', 'get_memory_usage', 'get_memory_top_consumers', 'get_system_uptime'];
  const diskTools = ['get_disk_usage', 'get_large_files', 'get_open_files'];
  const networkTools = ['get_network_connections', 'check_port_usage'];
  const logTools = ['query_journal', 'search_log_file'];
  const serviceTools = ['get_service_status', 'list_failed_services', 'check_failed_logins'];
  const securityTools = ['kill_process', 'run_safe_command', 'backup_config', 'rollback_operation'];

  if (systemTools.includes(toolName)) return 'lucide:activity';
  if (diskTools.includes(toolName)) return 'lucide:hard-drive';
  if (networkTools.includes(toolName)) return 'lucide:network';
  if (logTools.includes(toolName)) return 'lucide:scroll-text';
  if (serviceTools.includes(toolName)) return 'lucide:server';
  if (securityTools.includes(toolName)) return 'lucide:shield';
  return 'lucide:wrench';
};

// P8: 根据工具执行结果返回状态信息
interface ToolStatusInfo { color: string; tagColor: string; label: string }

const getToolStatus = (tool: { error?: string; result?: any; sandbox?: boolean }): ToolStatusInfo => {
  if (tool.error) return { color: '#ff4d4f', tagColor: 'red', label: '执行失败' };
  if (tool.result && typeof tool.result === 'object' && 'error' in tool.result)
    return { color: '#ff4d4f', tagColor: 'red', label: '安全拦截' };
  if (tool.sandbox) return { color: '#722ed1', tagColor: 'purple', label: '沙箱执行' };
  return { color: '#52c41a', tagColor: 'green', label: '执行成功' };
};

// P8: 打开工具结果完整查看 Modal
const openToolResultModal = (tool: { name: string; args?: any; result: any }) => {
  currentToolResult.value = { name: tool.name, args: tool.args, result: tool.result };
  toolResultModalVisible.value = true;
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

  // 用户发送了新消息 → 期待看到回答，所以重置为"在底部"状态
  isAtBottom.value = true;
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
          // P8: 收集工具执行详情
          if (chunk.tool_details && Array.isArray(chunk.tool_details)) {
            if (!aiMessage.toolDetails) aiMessage.toolDetails = [];
            aiMessage.toolDetails.push(...chunk.tool_details);
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

          // 智能滚动：仅在用户已停留在底部时滚动
          // 这样用户上滑浏览历史时不会被强制拉回底部
          await scrollToBottomIfAtBottom();
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

  // 流结束后：根据用户停留位置决定是否滚到底部
  await scrollToBottomIfAtBottom();
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

// 智能滚动：仅在用户已停留在底部时才跟随滚动到新内容
const scrollToBottomIfAtBottom = async () => {
  await nextTick();
  if (isAtBottom.value) {
    scrollToBottom();
  }
};

// 检测用户滚动位置：用于决定是否开启"自动跟随"
const handleChatScroll = () => {
  if (!chatHistoryRef.value) return;
  const el = chatHistoryRef.value;
  const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
  isAtBottom.value = distanceToBottom <= SCROLL_BOTTOM_THRESHOLD;
};

// 滚轮事件兜底：某些浏览器/触摸板上 scroll 事件不触发时，用 wheel 事件强制刷新位置
const handleChatWheel = () => {
  // 用 setTimeout 让浏览器先完成滚动，再读取新位置
  setTimeout(handleChatScroll, 0);
};

// 加载历史会话时强制重置到底部（避免加载后 isAtBottom 状态异常）
const resetScrollToBottom = async () => {
  isAtBottom.value = true;
  await nextTick();
  scrollToBottom();
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

// 安全拦截率格式化：0~1 的小数 → 0.0% ~ 100.0%
const formatBlockRate = (rate: number | undefined | null): string => {
  if (rate === undefined || rate === null || Number.isNaN(rate)) return '0.0%';
  const pct = rate * 100;
  const rounded = Math.round(pct * 10) / 10;
  return `${rounded.toFixed(1)}%`;
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
    // 加载历史会话：强制滚到底部（最新消息）
    await resetScrollToBottom();
  } catch (e) {
    message.error('加载会话失败');
  }
};

// 页面初始化
onMounted(() => {
  fetchSystemStatus();
  fetchSafetyStats();
  fetchSessions();

  // 响应式：监听窗口尺寸变化，动态调整 trace Modal 宽度
  updateTraceModalWidth();
  window.addEventListener('resize', updateTraceModalWidth, { passive: true });

  // 如果URL带有session_id参数，自动加载该会话
  const sessionIdFromQuery = route.query.session_id as string;
  if (sessionIdFromQuery) {
    loadSession(sessionIdFromQuery);
  }
});

// 页面销毁前：移除 resize 监听，防止内存泄漏
onBeforeUnmount(() => {
  window.removeEventListener('resize', updateTraceModalWidth);
});
</script>

<style scoped>
.query-container {
  padding: 24px;
  background-color: var(--ant-background-color-light, #fafafa);
  /* 关键修复：
   * - 不能用 height: 100vh，因为页面在 Vben 布局的 header (50px) + sidebar header (38px) 下方
   * - 用 calc(100vh - 88px) 让容器高度正好等于"视口高度 - Vben 头部偏移"
   * - 配合 flex 布局让 chat-history 独立滚动 */
  height: calc(100vh - 88px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
}

/* 页面头部 */
.query-container .page-header {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
  /* 关键修复：防止 page-header 在 flex 容器中被压缩 */
  flex-shrink: 0;
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
  flex-shrink: 0;
}

.query-container .header-action-btn {
  height: 40px;
  padding: 0 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
  transition: all 0.2s ease;
}

.query-container .header-action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.query-container .header-action-btn.primary {
  background: linear-gradient(135deg, #1890ff, #096dd9);
  border: none;
}

.query-container .header-action-btn .btn-text {
  margin-left: 2px;
}

/* 内容区域 */
.page-content {
  /* 关键修复：flex:1 + min-height:0 让子元素可滚动 */
  flex: 1;
  min-height: 0;
  overflow: hidden;

  /* 关键修复：让 Ant Design Row/Col 填满父容器，使 .content-card 的 height:100% 生效 */
  :deep(.ant-row) {
    height: 100%;
    flex-wrap: nowrap;
  }
  :deep(.ant-col) {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .content-card {
    background: var(--bg-color-white, #ffffff);
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    /* 关键修复：填满 page-content 剩余空间，而非依赖 calc 计算 */
    height: 100%;
    /* 让"回到最新"按钮可相对此容器绝对定位 */
    position: relative;
  }

  /* 侧边栏专用：垂直 flex 容器，多卡片堆叠时整体可滚动 */
  :deep(.sidebar-col) {
    height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
    /* 自定义滚动条样式 */
    scrollbar-width: thin;
    scrollbar-color: #d9d9d9 transparent;
    /* 防止滚轮事件冒泡到父级，避免"抢鼠标" */
    overscroll-behavior: contain;
    scroll-behavior: smooth;
  }
  :deep(.sidebar-col::-webkit-scrollbar) {
    width: 6px;
  }
  :deep(.sidebar-col::-webkit-scrollbar-track) {
    background: transparent;
  }
  :deep(.sidebar-col::-webkit-scrollbar-thumb) {
    background: #d9d9d9;
    border-radius: 3px;
  }
  :deep(.sidebar-col::-webkit-scrollbar-thumb:hover) {
    background: #bfbfbf;
  }

  .sidebar-card {
    height: auto;
    margin-bottom: 12px;
    min-height: auto;
    /* 关键：取消 height:100%，让卡片在 flex 列中按内容自适应 */
    flex: 0 0 auto;

    &:last-child {
      margin-bottom: 0;
    }
  }

  /* 系统概览卡片：紧凑布局，关键信息一目了然 */
  .sidebar-card.system-overview-card .card-content {
    flex: 0 0 auto;
    padding: 12px 16px;
  }
  .sidebar-card.system-overview-card .system-overview {
    .kylin-logo {
      margin-bottom: 8px;
    }
    .os-name {
      font-size: 13px;
    }
    .logo-img {
      height: 24px;
    }
    :deep(.ant-divider) {
      margin: 10px 0;
    }
    .info-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px 12px;
    }
    .info-row {
      padding: 2px 0;
    }
    .info-label {
      font-size: 12px;
    }
    .info-value {
      font-size: 12px;
    }
  }

  /* 历史会话卡片：固定最大高度，内部滚动 */
  .sidebar-card.history-card {
    flex: 1 1 auto;
    min-height: 0; /* 关键：让 flex 子项可收缩 */
    overflow: hidden;
  }
  .sidebar-card.history-card .card-content {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .sidebar-card.history-card .session-list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-right: 4px;
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
    /* 关键修复：min-height:0 让 flex 子项可正确收缩产生滚动 */
    min-height: 0;
    padding: 16px 24px;
    overflow-y: auto;
    /* 平滑滚动 */
    scroll-behavior: smooth;
    /* 防止 wheel 事件被父级抢走（确保鼠标滚轮在本区域内自由滚动） */
    overscroll-behavior: contain;

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

        /* T2: 提示词注入攻击专项告警 */
        .injection-alert {
          margin: 8px 0 4px;
          padding: 10px 14px;
          background: linear-gradient(135deg, #fff1f0 0%, #ffa39e 100%);
          border: 2px solid #cf1322;
          border-radius: 8px;
          animation: injection-pulse 1s ease-in-out infinite;

          .injection-alert-content {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #a8071a;
            font-weight: 600;
            font-size: 13px;

            .injection-alert-text {
              flex: 1;
            }
          }

          .injection-patterns {
            margin-top: 6px;
            padding-top: 6px;
            border-top: 1px dashed rgba(207, 19, 34, 0.3);
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px;

            .injection-patterns-label {
              font-size: 11px;
              color: #a8071a;
            }
          }
        }

        /* P5: 安全拦截危险警告条 */
        .danger-banner {
          margin: 8px 0 4px;
          padding: 10px 14px;
          background: linear-gradient(135deg, #fff2f0 0%, #ffccc7 100%);
          border: 2px solid #ff4d4f;
          border-radius: 8px;
          animation: danger-pulse 0.8s ease-in-out 2;

          .danger-banner-content {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #cf1322;
            font-weight: 600;
            font-size: 13px;

            .danger-banner-text {
              flex: 1;
            }
          }
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

        /* P7: 推理链精简节点（流水线样式） */
        .reasoning-pipeline {
          margin-top: 8px;
          padding: 8px 12px;
          background: #f6ffed;
          border: 1px solid #b7eb8f;
          border-radius: 8px;

          .pipeline-steps {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 6px;
          }

          .pipeline-step {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
            background: #f0f0f0;
            color: #8c8c8c;

            &.done {
              background: #e6f7ff;
              color: #1890ff;
            }

            &.blocked {
              background: #fff2f0;
              color: #ff4d4f;
              font-weight: 600;
            }

            &.pending {
              background: #fffbe6;
              color: #faad14;
            }
          }
        }

        /* P8: 工具执行详情（增强版：折叠/图标/状态/全量查看） */
        .tool-details {
          margin: 8px 0;

          .tool-detail-item {
            border: 1px solid #d9d9d9;
            border-radius: 8px;
            margin-bottom: 6px;
            overflow: hidden;
            background: #fafafa;
            transition: border-color 0.2s;

            &:hover {
              border-color: #91d5ff;
            }

            .tool-detail-header {
              display: flex;
              align-items: center;
              gap: 6px;
              padding: 6px 10px;
              background: #f0f5ff;
              border-bottom: 1px solid #d9d9d9;
              user-select: none;
              transition: background 0.15s;

              &.clickable {
                cursor: pointer;

                &:hover {
                  background: #e6f0ff;
                }
              }

              .tool-name {
                font-size: 12px;
                font-weight: 600;
                color: #262626;
                font-family: monospace;
              }

              .tool-status-dot {
                width: 6px;
                height: 6px;
                border-radius: 50%;
                flex-shrink: 0;
              }

              .tool-chevron {
                margin-left: auto;
                transition: transform 0.25s ease;
                color: #8c8c8c;

                &.rotated {
                  transform: rotate(180deg);
                }
              }
            }

            .tool-detail-body {
              padding: 6px 10px;
              font-size: 11px;

              .tool-args,
              .tool-result {
                margin-bottom: 4px;

                &:last-child {
                  margin-bottom: 0;
                }

                .detail-label {
                  color: #8c8c8c;
                  margin-right: 4px;
                }

                code {
                  background: #f5f5f5;
                  padding: 1px 4px;
                  border-radius: 3px;
                  font-size: 11px;
                }

                .result-summary {
                  color: #52c41a;
                }

                .view-full-btn {
                  padding: 0 4px;
                  font-size: 11px;
                  height: auto;
                }
              }
            }
          }
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

  /* 回到最新按钮：浮在聊天区底部中央 */
  .scroll-to-bottom-btn {
    position: absolute;
    /* 位于 chat-input 上方 16px (chat-input 约 92px 高) */
    bottom: 108px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 10;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    font-size: 13px;
    color: #1890ff;
    background: #ffffff;
    border: 1px solid #91d5ff;
    border-radius: 16px;
    box-shadow: 0 4px 12px rgba(24, 144, 255, 0.2);
    cursor: pointer;
    transition: all 0.2s ease;
    user-select: none;
  }
  .scroll-to-bottom-btn:hover {
    background: #e6f7ff;
    transform: translateX(-50%) translateY(-2px);
    box-shadow: 0 6px 16px rgba(24, 144, 255, 0.3);
  }
  .scroll-to-bottom-btn:active {
    transform: translateX(-50%) translateY(0);
  }

  .chat-input {
    padding: 20px 24px;
    background: var(--bg-color-light, #fafafa);
    border-top: 1px solid var(--border-color, #f0f0f0);
    /* 关键修复：flex-shrink:0 防止输入框在空间不足时被压缩或消失 */
    flex-shrink: 0;
    position: relative;
    z-index: 2;

    :deep(.ant-input-affix-wrapper) {
      padding: 8px 16px;
      border-radius: 12px;
      font-size: 15px;
      min-height: 52px;
    }

    :deep(.ant-input) {
      font-size: 15px;
    }

    :deep(.ant-btn) {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
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

/* 安全统计 - 2x2 网格布局，关键数据一目了然 */
.safety-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 4px 0;

  .stat-block {
    padding: 12px 8px;
    border-radius: 8px;
    text-align: center;
    background: #fafafa;
    border: 1px solid #f0f0f0;
    transition: all 0.2s ease;

    .stat-num {
      font-size: 20px;
      font-weight: 700;
      line-height: 1.2;
      color: #262626;
    }
    .stat-lbl {
      font-size: 12px;
      color: #8c8c8c;
      margin-top: 4px;
    }
  }

  .stat-block.total {
    background: #e6f4ff;
    border-color: #91caff;
    .stat-num { color: #0958d9; }
  }
  .stat-block.blocked {
    background: #fff1f0;
    border-color: #ffa39e;
    .stat-num { color: #cf1322; }
  }
  .stat-block.passed {
    background: #f6ffed;
    border-color: #b7eb8f;
    .stat-num { color: #389e0d; }
  }
  .stat-block.rate {
    background: #fff7e6;
    border-color: #ffd591;
    .stat-num { color: #d46b08; }
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

/* ============================================================
 * P7 增强: "查看完整链路" 入口按钮 + Modal 状态样式
 * 设计原则：在对话气泡内显眼、状态清晰、响应式友好
 * ============================================================ */

/* 1. 对话气泡内的"查看完整链路"按钮 */
.view-full-chain-btn {
  display: inline-flex;
  align-items: center;
  font-weight: 500;
  border-radius: 16px;
  padding: 0 12px;
  height: 26px;
  font-size: 12px;
  transition: all 0.2s ease;
  margin-top: 4px;
}

.view-full-chain-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(114, 46, 209, 0.25);
}

/* 2. Modal 标题栏 */
.trace-modal-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

/* 2b. Modal body 工具栏（"在新页面打开"按钮） */
.trace-modal-toolbar {
  display: flex;
  justify-content: flex-end;
  padding: 4px 0 8px 0;
  border-bottom: 1px dashed #f0f0f0;
  margin-bottom: 8px;
}

.open-full-page-link {
  font-size: 12px;
  padding: 0 6px;
}

/* 3. Modal 通用状态容器（loading / error / empty） */
.trace-modal-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 56px 24px;
  min-height: 320px;
  color: #595959;
}

.trace-modal-state p {
  margin: 12px 0 0;
  font-size: 14px;
  line-height: 1.6;
}

.trace-modal-state .error-title,
.trace-modal-state .empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #262626;
  margin-top: 16px;
}

.trace-modal-state .error-desc,
.trace-modal-state .empty-desc {
  font-size: 13px;
  color: #8c8c8c;
  max-width: 420px;
}

.trace-modal-loading p {
  margin-top: 16px;
  color: #8c8c8c;
}

.trace-modal-error {
  background: linear-gradient(180deg, #fff5f5 0%, #fff 60%);
  border-radius: 8px;
}

.trace-modal-error .error-title {
  color: #ff4d4f;
}

.trace-modal-error .error-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.trace-modal-empty {
  background: #fafafa;
  border-radius: 8px;
}

/* 4. Modal 容器：移动端占据全宽并贴近视口 */
:deep(.trace-modal-wrap .ant-modal) {
  max-width: calc(100vw - 16px);
  margin: 8px;
}

:deep(.trace-modal-wrap .ant-modal-content) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.trace-modal-wrap .ant-modal-body) {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 16px 20px;
}

/* 5. 移动端：紧凑布局 */
@media (max-width: 576px) {
  .view-full-chain-btn {
    height: 24px;
    padding: 0 10px;
    font-size: 11px;
  }

  .open-full-page-link {
    display: none;
  }

  :deep(.trace-modal-wrap .ant-modal-body) {
    max-height: calc(100vh - 160px);
    padding: 12px 14px;
  }

  .trace-modal-state {
    padding: 40px 16px;
    min-height: 240px;
  }
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

/* P5: 安全拦截脉冲动画（2 次后停止） */
@keyframes danger-pulse {
  0% {
    border-color: #ff4d4f;
    box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.4);
  }
  50% {
    border-color: #ff7875;
    box-shadow: 0 0 12px 4px rgba(255, 77, 79, 0.2);
  }
  100% {
    border-color: #ff4d4f;
    box-shadow: 0 0 0 0 rgba(255, 77, 79, 0);
  }
}

/* T2: 提示词注入脉冲动画（持续循环） */
@keyframes injection-pulse {
  0% {
    border-color: #cf1322;
    box-shadow: 0 0 0 0 rgba(207, 19, 34, 0.5);
  }
  50% {
    border-color: #ff4d4f;
    box-shadow: 0 0 16px 6px rgba(207, 19, 34, 0.25);
  }
  100% {
    border-color: #cf1322;
    box-shadow: 0 0 0 0 rgba(207, 19, 34, 0);
  }
}

/* T5: 安全护栏详情 Modal 样式 */
.safety-modal-subtitle {
  margin-bottom: 12px;
}

:deep(.layer-row-failed) {
  background-color: #fff2f0 !important;

  &:hover > td {
    background-color: #fff2f0 !important;
  }
}

:deep(.detail-failed) {
  color: #cf1322;
  font-weight: 500;
}

/* P8: 工具结果 Modal 样式 */
.tool-modal-section {
  margin-bottom: 16px;

  &:last-child {
    margin-bottom: 0;
  }

  .tool-modal-label {
    font-size: 13px;
    font-weight: 600;
    color: #262626;
    margin-bottom: 8px;
  }

  .tool-modal-code {
    background: #f5f5f5;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 12px;
    line-height: 1.6;
    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 400px;
    overflow-y: auto;
    margin: 0;
    border: 1px solid #e8e8e8;
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
