<template>
  <div class="chain-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon">
            <Icon icon="lucide:git-branch" size="32" color="#722ed1" />
          </div>
          <div class="header-text">
            <h1 class="page-title">推理链路</h1>
            <p class="page-subtitle">查看 AI 推理过程的完整链路记录</p>
          </div>
        </div>
        <div class="header-actions">
          <a-button type="primary" @click="fetchTraces" :loading="loading">
            <Icon icon="lucide:refresh-cw" size="16" style="margin-right: 6px;" />
            <span>刷新数据</span>
          </a-button>
        </div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <a-row :gutter="[24, 24]" class="stats-row">
      <a-col :xs="24" :sm="12" :lg="8">
        <div class="stat-card stat-traces">
          <div class="stat-icon-wrap">
            <Icon icon="lucide:git-branch" size="26" />
          </div>
          <div class="stat-info">
            <div class="stat-label">总链路数</div>
            <div class="stat-number">{{ traces.length }}</div>
          </div>
        </div>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="8">
        <div class="stat-card stat-steps">
          <div class="stat-icon-wrap">
            <Icon icon="lucide:check-circle" size="26" />
          </div>
          <div class="stat-info">
            <div class="stat-label">总步骤数</div>
            <div class="stat-number">{{ totalSteps }}</div>
          </div>
        </div>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="8">
        <div class="stat-card stat-duration">
          <div class="stat-icon-wrap">
            <Icon icon="lucide:clock" size="26" />
          </div>
          <div class="stat-info">
            <div class="stat-label">平均耗时</div>
            <div class="stat-number">{{ formatDuration(avgDurationMs) }}</div>
          </div>
        </div>
      </a-col>
    </a-row>

    <!-- 链路列表 -->
    <div class="content-card">
      <div class="card-header">
        <div class="header-title">
          <Icon icon="lucide:list" size="18" color="#722ed1" />
          链路列表
        </div>
      </div>

      <div class="card-content">
        <!-- 加载状态 -->
        <div v-if="loading" class="loading-state">
          <a-spin size="large" />
          <p>正在加载链路数据...</p>
        </div>

        <!-- 空状态 -->
        <div v-else-if="traces.length === 0" class="empty-state">
          <Icon icon="lucide:git-branch" size="64" color="#bfbfbf" />
          <p class="empty-title">暂无推理链路</p>
          <p class="empty-desc">开始一次智能问答后，推理链路将自动记录在这里</p>
        </div>

        <!-- 链路卡片列表 -->
        <div v-else class="trace-list">
          <div
            v-for="trace in traces"
            :key="trace.trace_id"
            class="trace-card"
          >
            <div class="trace-card-header">
              <div class="trace-id-section">
                <Icon icon="lucide:hash" size="14" color="#8c8c8c" />
                <span class="trace-id">{{ truncateId(trace.trace_id) }}</span>
              </div>
              <a-button
                type="primary"
                size="small"
                class="trace-action-btn"
                @click.stop="openTraceDetail(trace)"
              >
                <Icon icon="lucide:eye" size="14" />
                <span>查看详情</span>
              </a-button>
            </div>

            <div class="trace-prompt">
              <Icon icon="lucide:message-square" size="14" color="#1890ff" style="margin-right: 4px; flex-shrink: 0;" />
              <span class="prompt-text">{{ truncatePrompt(trace.user_prompt) }}</span>
            </div>

            <div class="trace-card-footer">
              <div class="trace-meta">
                <span class="meta-item">
                  <Icon icon="lucide:calendar" size="12" />
                  {{ formatDateTime(trace.start_time) }}
                </span>
                <span class="meta-item">
                  <Icon icon="lucide:layers" size="12" />
                  {{ trace.steps?.length || 0 }} 步
                </span>
                <span class="meta-item">
                  <Icon icon="lucide:timer" size="12" />
                  {{ formatDuration(calcDuration(trace)) }}
                </span>
              </div>

              <!-- 步骤类型预览 -->
              <div class="step-badges">
                <span
                  v-for="(step, idx) in (trace.steps || []).slice(0, 5)"
                  :key="idx"
                  class="step-badge"
                  :class="getStepBadgeClass(step.step)"
                >
                  {{ getStepName(step.step) }}
                </span>
                <span v-if="(trace.steps || []).length > 5" class="step-badge step-badge-more">
                  +{{ trace.steps.length - 5 }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 推理链路详情弹窗（响应式 + 状态机） -->
    <a-modal
      v-model:open="detailModalVisible"
      title="推理链路详情"
      :width="960"
      :footer="null"
      :destroyOnClose="true"
      :mask-closable="!detailLoading"
      centered
      wrap-class-name="chain-detail-modal-wrap"
      @cancel="handleDetailClose"
    >
      <!-- 加载态 -->
      <div v-if="detailLoading" class="chain-state chain-loading">
        <a-spin size="large" />
        <p>正在加载完整链路数据…</p>
      </div>

      <!-- 错误态 -->
      <div v-else-if="detailError" class="chain-state chain-error">
        <Icon icon="lucide:alert-triangle" size="56" color="#ff4d4f" />
        <p class="state-title">{{ detailError.title }}</p>
        <p class="state-desc">{{ detailError.desc }}</p>
        <div class="chain-error-actions">
          <a-button type="primary" @click="retryDetailLoad">
            <Icon icon="lucide:rotate-cw" size="14" style="margin-right: 4px;" />
            重试
          </a-button>
          <a-button @click="detailModalVisible = false">关闭</a-button>
        </div>
      </div>

      <!-- 空态 -->
      <div v-else-if="currentTrace && (!currentTrace.steps || currentTrace.steps.length === 0)" class="chain-state chain-empty">
        <Icon icon="lucide:git-branch" size="56" color="#bfbfbf" />
        <p class="state-title">该链路暂无步骤记录</p>
        <p class="state-desc">链路可能已被清理或正在收集中</p>
      </div>

      <!-- 正常：渲染可视化 -->
      <TraceVisualization
        v-else-if="currentTrace"
        :trace="currentTrace"
      />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import { Icon } from '@iconify/vue';
import { getTraces, getTrace } from '#/api/core/aiops/agent';
import type { Trace } from '#/api/core/aiops/agent';
import TraceVisualization from './components/TraceVisualization.vue';

const route = useRoute();
const router = useRouter();

// 响应式数据
const loading = ref(false);
const traces = ref<Trace[]>([]);
const detailModalVisible = ref(false);
const currentTrace = ref<Trace | null>(null);
// 详情加载态：避免 Modal 已开但数据未到
const detailLoading = ref(false);
// 详情错误态
const detailError = ref<{ title: string; desc: string } | null>(null);
// 最近一次加载的 traceId（用于重试）
const pendingDetailTraceId = ref<string | null>(null);

// 统计：总步骤数
const totalSteps = computed(() =>
  traces.value.reduce((sum, t) => sum + (t.steps?.length || 0), 0),
);

// 统计：平均耗时（毫秒数）
const avgDurationMs = computed(() => {
  if (traces.value.length === 0) return 0;
  const total = traces.value.reduce((sum, t) => sum + calcDuration(t), 0);
  return Math.round(total / traces.value.length);
});

// 计算单条链路耗时（ms）
const calcDuration = (trace: Trace): number => {
  if (!trace.start_time || !trace.end_time) return 0;
  return new Date(trace.end_time).getTime() - new Date(trace.start_time).getTime();
};

// 友好时长格式化：
//   < 1s  -> "800ms"
//   < 60s -> "10.6s"
//   >= 60s -> "1m 23s"
function formatDuration(ms: number): string {
  if (!ms || ms < 0) return '0ms';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) {
    const s = ms / 1000;
    return `${s.toFixed(1)}s`;
  }
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return s === 0 ? `${m}m` : `${m}m ${s}s`;
}

// 截断 ID 显示
const truncateId = (id: string): string => {
  if (!id) return '-';
  return id.length > 20 ? `${id.slice(0, 8)}...${id.slice(-4)}` : id;
};

// 截断过长的用户输入
const truncatePrompt = (prompt?: string): string => {
  if (!prompt) return '无输入';
  return prompt.length > 120 ? `${prompt.slice(0, 120)}...` : prompt;
};

// 格式化日期时间
const formatDateTime = (timestamp?: string): string => {
  if (!timestamp) return '-';
  const date = new Date(timestamp);
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

// 步骤名称映射
const getStepName = (step: string): string => {
  const map: Record<string, string> = {
    INIT: '初始化',
    ENVIRONMENT_SENSE: '环境感知',
    INTENT_ANALYSIS: '意图分析',
    SAFETY_VALIDATION: '安全校验',
    TOOL_EXECUTION: '工具执行',
    FINAL_DECISION: '最终决策',
  };
  return map[step] || step;
};

// 步骤徽章样式
const getStepBadgeClass = (step: string): string => {
  const map: Record<string, string> = {
    INIT: 'badge-init',
    ENVIRONMENT_SENSE: 'badge-sense',
    INTENT_ANALYSIS: 'badge-analysis',
    SAFETY_VALIDATION: 'badge-safety',
    TOOL_EXECUTION: 'badge-tool',
    FINAL_DECISION: 'badge-decision',
  };
  return map[step] || 'badge-default';
};

// 获取链路列表
const fetchTraces = async () => {
  loading.value = true;
  try {
    const res = await getTraces(50);
    traces.value = res.traces || [];
  } catch (e: any) {
    message.error(`获取推理链路失败: ${e.message}`);
  } finally {
    loading.value = false;
  }
};

// 打开链路详情（支持列表触发与深链接触发）
const openTraceDetail = async (trace: Trace | null, traceId?: string) => {
  // 重置状态
  detailError.value = null;
  detailLoading.value = true;
  detailModalVisible.value = true;
  // 记录当前 traceId 供重试使用
  pendingDetailTraceId.value = traceId || trace?.trace_id || null;

  try {
    if (trace) {
      // 来自列表：已有完整数据
      currentTrace.value = trace;
    } else if (traceId) {
      // 来自深链接：按 ID 拉取
      const res = await getTrace(traceId);
      if (!res || !res.trace) {
        throw new Error('EMPTY_RESPONSE');
      }
      currentTrace.value = res.trace;
    } else {
      throw new Error('MISSING_TRACE');
    }
  } catch (e: any) {
    const status = e?.response?.status;
    if (status === 404) {
      detailError.value = {
        title: '未找到该推理链路',
        desc: `链路 ${traceId || trace?.trace_id || ''} 不存在或已被清理。`,
      };
    } else {
      detailError.value = {
        title: '加载链路详情失败',
        desc: e?.message || '网络异常，请重试。',
      };
    }
    // eslint-disable-next-line no-console
    console.error('[openTraceDetail] failed', e);
  } finally {
    detailLoading.value = false;
  }
};

// 处理 URL 中的 ?trace_id=xxx 深链接
const handleDeepLink = async (traceId: string) => {
  if (!traceId) return;
  // 先尝试从已加载的列表中匹配；命中则直接打开
  const found = traces.value.find((t) => t.trace_id === traceId);
  if (found) {
    openTraceDetail(found);
  } else {
    openTraceDetail(null, traceId);
  }
};

// 重试加载详情
const retryDetailLoad = () => {
  if (pendingDetailTraceId.value) {
    openTraceDetail(null, pendingDetailTraceId.value);
  }
};

// 关闭详情：清理状态（延迟以避开关闭动画）
const handleDetailClose = () => {
  if (detailLoading.value) return;
  detailModalVisible.value = false;
  setTimeout(() => {
    currentTrace.value = null;
    detailError.value = null;
    // 同步清除 URL 上的 trace_id，避免刷新再次打开
    if (route.query.trace_id) {
      const rest = { ...route.query };
      delete (rest as Record<string, unknown>).trace_id;
      router.replace({ path: route.path, query: rest });
    }
  }, 200);
};

// 页面初始化
onMounted(async () => {
  await fetchTraces();
  // 检查深链接：?trace_id=xxx
  const deepLinkId = route.query.trace_id as string | undefined;
  if (deepLinkId) {
    handleDeepLink(deepLinkId);
  }
});

// 监听 route.query.trace_id 变化（用户在页面内切换）
watch(
  () => route.query.trace_id,
  (newId) => {
    if (typeof newId === 'string' && newId) {
      handleDeepLink(newId);
    }
  },
);
</script>

<style scoped>
.chain-container {
  padding: 24px;
  background-color: #fafafa;
  min-height: 100vh;
}

/* 页面头部 */
.chain-container .page-header {
  background: #fff;
  border-radius: 12px;
  padding: 16px 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
}

.chain-container .header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.chain-container .header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.chain-container .header-icon {
  font-size: 32px;
  color: #722ed1;
}

.chain-container .header-text {
  display: flex;
  flex-direction: column;
}

.chain-container .page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #262626;
  line-height: 1.2;
}

.chain-container .page-subtitle {
  color: #8c8c8c;
  margin: 0;
  font-size: 12px;
  margin-top: 4px;
}

.chain-container .header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-shrink: 0;
}

/* 头部按钮美化 */
.chain-container .header-actions :deep(.ant-btn) {
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
}
.chain-container .header-actions :deep(.ant-btn:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
}

/* 统计卡片 */
.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.stat-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  flex-shrink: 0;
}

.stat-traces .stat-icon-wrap {
  background: linear-gradient(135deg, #722ed1, #b37feb);
  color: #fff;
}

.stat-steps .stat-icon-wrap {
  background: linear-gradient(135deg, #52c41a, #95de64);
  color: #fff;
}

.stat-duration .stat-icon-wrap {
  background: linear-gradient(135deg, #faad14, #ffc53d);
  color: #fff;
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 13px;
  color: #8c8c8c;
  margin-bottom: 4px;
  font-weight: 500;
}

.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: #262626;
  line-height: 1;
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
  font-size: 15px;
  font-weight: 600;
  color: #262626;
}

.card-content {
  padding: 24px;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #8c8c8c;
}

.loading-state p {
  margin: 16px 0 0 0;
  font-size: 14px;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #bfbfbf;
}

.empty-title {
  margin: 16px 0 0 0;
  font-size: 16px;
  color: #8c8c8c;
}

.empty-desc {
  margin: 8px 0 0 0;
  font-size: 13px;
  color: #bfbfbf;
}

/* 链路卡片列表 */
.trace-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.trace-card {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 16px 20px;
  transition: all 0.2s ease;
}

.trace-card:hover {
  border-color: #91d5ff;
  box-shadow: 0 2px 12px rgba(24, 144, 255, 0.1);
}

.trace-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  gap: 12px;
}

.trace-id-section {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
}

.trace-id {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  color: #595959;
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  min-width: 0;
}

/* 查看详情按钮：确保不被挤压、增强视觉 */
.trace-action-btn {
  flex-shrink: 0;
  border-radius: 6px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  box-shadow: 0 1px 2px rgba(114, 46, 209, 0.15);
  transition: all 0.2s ease;
}

.trace-action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(114, 46, 209, 0.25);
}

.trace-prompt {
  display: flex;
  align-items: flex-start;
  font-size: 14px;
  color: #262626;
  line-height: 1.6;
  margin-bottom: 12px;
  padding: 10px 14px;
  background: #fafafa;
  border-radius: 6px;
  border-left: 3px solid #722ed1;
}

.prompt-text {
  flex: 1;
}

.trace-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.trace-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #8c8c8c;
}

/* 步骤类型徽章 */
.step-badges {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.step-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  line-height: 18px;
}

.badge-init {
  background: #f5f5f5;
  color: #8c8c8c;
  border: 1px solid #d9d9d9;
}

.badge-sense {
  background: #e6f7ff;
  color: #1890ff;
  border: 1px solid #91d5ff;
}

.badge-analysis {
  background: #fff7e6;
  color: #d48806;
  border: 1px solid #ffd591;
}

.badge-safety {
  background: #fff1f0;
  color: #ff4d4f;
  border: 1px solid #ffa39e;
}

.badge-tool {
  background: #f6ffed;
  color: #389e0d;
  border: 1px solid #b7eb8f;
}

.badge-decision {
  background: #f9f0ff;
  color: #722ed1;
  border: 1px solid #d3adf7;
}

.badge-default {
  background: #f5f5f5;
  color: #595959;
  border: 1px solid #d9d9d9;
}

.step-badge-more {
  background: #f0f0f0;
  color: #8c8c8c;
  border: 1px solid #d9d9d9;
}

/* 响应式 */
@media (max-width: 768px) {
  .chain-container {
    padding: 16px;
  }

  .chain-container .page-header {
    padding: 20px;
    margin-bottom: 16px;
  }

  .chain-container .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .chain-container .header-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .stat-card {
    padding: 16px;
    gap: 14px;
  }

  .stat-icon-wrap {
    width: 44px;
    height: 44px;
  }

  .stat-number {
    font-size: 22px;
  }
}

/* ============================================================
 * 详情弹窗：状态机 + 响应式样式
 * ============================================================ */
.chain-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 64px 24px;
  min-height: 360px;
  color: #595959;
  border-radius: 8px;
}

.chain-state p {
  margin: 12px 0 0;
  font-size: 14px;
  line-height: 1.6;
}

.chain-state .state-title {
  font-size: 16px;
  font-weight: 600;
  color: #262626;
  margin-top: 16px;
}

.chain-state .state-desc {
  font-size: 13px;
  color: #8c8c8c;
  max-width: 420px;
  margin-bottom: 16px;
}

.chain-loading {
  background: #fafafa;
}

.chain-error {
  background: linear-gradient(180deg, #fff5f5 0%, #fff 60%);
}

.chain-error .state-title {
  color: #ff4d4f;
}

.chain-error-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.chain-empty {
  background: #fafafa;
}

/* Modal 容器：移动端贴近视口 */
:deep(.chain-detail-modal-wrap .ant-modal) {
  max-width: calc(100vw - 16px);
  margin: 8px;
}

:deep(.chain-detail-modal-wrap .ant-modal-content) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.chain-detail-modal-wrap .ant-modal-body) {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 16px 20px;
}

/* 平板及以下 */
@media (max-width: 768px) {
  :deep(.chain-detail-modal-wrap .ant-modal) {
    max-width: calc(100vw - 16px);
  }

  .chain-state {
    padding: 48px 16px;
    min-height: 280px;
  }
}

/* 手机 */
@media (max-width: 576px) {
  :deep(.chain-detail-modal-wrap .ant-modal-body) {
    max-height: calc(100vh - 160px);
    padding: 12px 14px;
  }

  .chain-state {
    padding: 36px 12px;
    min-height: 220px;
  }

  .chain-state .state-title {
    font-size: 14px;
  }

  .chain-state .state-desc {
    font-size: 12px;
  }
}
</style>
