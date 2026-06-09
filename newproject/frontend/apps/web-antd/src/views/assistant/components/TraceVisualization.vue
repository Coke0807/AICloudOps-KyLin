<template>
  <div class="trace-visualization">
    <!-- 链路概览头部 -->
    <div class="trace-overview">
      <div class="overview-item">
        <div class="overview-label">链路ID</div>
        <div class="overview-value mono overview-trace-id" :title="trace.trace_id">
          <span class="trace-id-text">{{ shortTraceId }}</span>
          <a-tooltip :title="copied ? '已复制' : '复制完整 ID'">
            <button
              class="copy-btn"
              type="button"
              :aria-label="'复制链路 ID'"
              @click="copyTraceId"
            >
              <Icon :icon="copied ? 'lucide:check' : 'lucide:copy'" size="12" />
            </button>
          </a-tooltip>
        </div>
      </div>
      <div class="overview-item">
        <div class="overview-label">开始时间</div>
        <div class="overview-value">{{ formatTime(trace.start_time, true) }}</div>
      </div>
      <div class="overview-item">
        <div class="overview-label">耗时</div>
        <div class="overview-value">{{ formatDuration(duration) }}</div>
      </div>
      <div class="overview-item">
        <div class="overview-label">步骤数</div>
        <div class="overview-value">{{ trace.steps?.length || 0 }}</div>
      </div>
    </div>

    <!-- 顶部工具栏：展开/收起/复制 JSON -->
    <div v-if="trace.steps && trace.steps.length > 0" class="trace-toolbar">
      <a-space :size="6">
        <a-button size="small" @click="expandAll">
          <Icon icon="lucide:maximize-2" size="12" style="margin-right: 2px;" />
          展开全部
        </a-button>
        <a-button size="small" @click="collapseAll">
          <Icon icon="lucide:minimize-2" size="12" style="margin-right: 2px;" />
          收起全部
        </a-button>
        <a-button size="small" @click="copyAsJson">
          <Icon :icon="jsonCopied ? 'lucide:check' : 'lucide:clipboard'" size="12" style="margin-right: 2px;" />
          {{ jsonCopied ? '已复制' : '复制 JSON' }}
        </a-button>
      </a-space>
    </div>

    <!-- 用户输入 -->
    <div class="user-prompt-section">
      <div class="section-label">
        <Icon icon="lucide:user" size="14" />
        用户输入
      </div>
      <div class="prompt-content">{{ trace.user_prompt || '（无输入）' }}</div>
    </div>

    <!-- 推理链路时间轴 -->
    <div class="timeline-section">
      <div class="section-label">
        <Icon icon="lucide:git-branch" size="14" />
        推理链路
        <span class="step-counter">（{{ trace.steps?.length || 0 }} 个节点）</span>
      </div>

      <div class="timeline">
        <div
          v-for="(step, index) in trace.steps"
          :key="`${index}-${step.step}`"
          class="timeline-item"
          :class="{ expanded: expandedSteps.has(index) }"
        >
          <!-- 连接线 -->
          <div v-if="index > 0" class="timeline-connector" />

          <!-- 节点 -->
          <div class="timeline-node" :class="getNodeClass(step.step)">
            <div class="node-icon">
              <Icon :icon="getStepIcon(step.step)" size="18" />
            </div>
            <div class="node-badge">{{ index + 1 }}</div>
          </div>

          <!-- 内容卡片 -->
          <div class="timeline-card" @click="toggleStep(index)">
            <div class="card-header">
              <div class="header-left">
                <span class="step-name">{{ getStepName(step.step) }}</span>
                <a-tag :color="getStepColor(step.step)" size="small">
                  {{ step.step }}
                </a-tag>
              </div>
              <div class="header-right">
                <span class="step-time">{{ formatTime(step.timestamp) }}</span>
                <Icon
                  :icon="expandedSteps.has(index) ? 'lucide:chevron-up' : 'lucide:chevron-down'"
                  size="14"
                  class="expand-icon"
                />
              </div>
            </div>

            <div class="card-summary">
              {{ getStepSummary(step) }}
            </div>

            <!-- 展开详情 -->
            <div v-show="expandedSteps.has(index)" class="card-detail">
              <a-divider style="margin: 8px 0;" />
              <div v-if="step.data" class="detail-content">
                <!-- 工具步骤：分块展示，提高可读性 -->
                <template v-if="step.step === 'TOOL_EXECUTION'">
                  <div v-if="step.data.tool" class="detail-row">
                    <span class="detail-key">工具</span>
                    <span class="detail-value">{{ step.data.tool }}</span>
                  </div>
                  <div v-if="step.data.params !== undefined" class="detail-row">
                    <span class="detail-key">参数</span>
                    <pre class="detail-code">{{ stringify(step.data.params) }}</pre>
                  </div>
                  <div v-if="step.data.result !== undefined" class="detail-row">
                    <span class="detail-key">结果</span>
                    <pre class="detail-code">{{ stringify(step.data.result) }}</pre>
                  </div>
                  <!-- 兜底：其余字段 -->
                  <div v-if="!step.data.tool && !step.data.params && !step.data.result" class="detail-row">
                    <pre class="detail-code">{{ stringify(step.data) }}</pre>
                  </div>
                </template>

                <!-- 安全校验步骤：清晰展示通过/拦截 -->
                <template v-else-if="step.step === 'SAFETY_VALIDATION'">
                  <div v-if="step.data.validation" class="detail-row">
                    <span class="detail-key">风险等级</span>
                    <a-tag :color="step.data.validation.is_safe ? 'green' : 'red'" size="small">
                      {{ step.data.validation.overall_risk || (step.data.validation.is_safe ? 'safe' : 'unsafe') }}
                    </a-tag>
                  </div>
                  <div v-if="step.data.validation?.layers" class="detail-row">
                    <span class="detail-key">校验层</span>
                    <pre class="detail-code">{{ stringify(step.data.validation.layers) }}</pre>
                  </div>
                  <div v-if="step.data.validation && !step.data.validation.layers" class="detail-row">
                    <pre class="detail-code">{{ stringify(step.data.validation) }}</pre>
                  </div>
                  <!-- 兜底：其他字段 -->
                  <div v-if="!step.data.validation" class="detail-row">
                    <pre class="detail-code">{{ stringify(step.data) }}</pre>
                  </div>
                </template>

                <!-- 环境感知：截断过大的 system snapshot -->
                <template v-else-if="step.step === 'ENVIRONMENT_SENSE' && step.data.snapshot">
                  <div class="detail-row">
                    <span class="detail-key">主机</span>
                    <span class="detail-value">{{ step.data.snapshot.system_info?.hostname || '-' }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-key">系统</span>
                    <span class="detail-value">{{ step.data.snapshot.system_info?.os || '-' }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-key">CPU 使用率</span>
                    <span class="detail-value">{{ step.data.snapshot.cpu?.percent ?? '-' }}%</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-key">内存使用率</span>
                    <span class="detail-value">{{ step.data.snapshot.memory?.percent ?? '-' }}%</span>
                  </div>
                  <a-collapse ghost>
                    <a-collapse-panel key="raw" header="查看完整数据">
                      <pre class="detail-code">{{ stringify(step.data.snapshot) }}</pre>
                    </a-collapse-panel>
                  </a-collapse>
                </template>

                <!-- 其它步骤：通用 JSON 展示 -->
                <template v-else>
                  <pre class="detail-code">{{ stringify(step.data) }}</pre>
                </template>
              </div>
              <div v-else class="no-data">无详细数据</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 最终结果 -->
    <div v-if="trace.final_result" class="final-result-section">
      <div class="section-label">
        <Icon icon="lucide:check-circle" size="14" />
        最终结果
      </div>
      <div class="result-content">
        <pre>{{ stringify(trace.final_result) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { message } from 'ant-design-vue';
import { Icon } from '@iconify/vue';
import type { Trace } from '#/api/core/aiops/agent';

interface Props {
  trace: Trace;
}

const props = defineProps<Props>();

const expandedSteps = ref<Set<number>>(new Set());
const copied = ref(false);
const jsonCopied = ref(false);

// 短 ID 展示：前 8 + 后 4
const shortTraceId = computed(() => {
  const id = props.trace.trace_id || '';
  if (!id) return '-';
  return id.length > 16 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id;
});

// 计算耗时
const duration = computed(() => {
  if (!props.trace.start_time || !props.trace.end_time) return 0;
  const start = new Date(props.trace.start_time).getTime();
  const end = new Date(props.trace.end_time).getTime();
  return Math.max(0, end - start);
});

// 安全序列化（避免循环引用；大对象会被截断展示在折叠面板中）
const stringify = (data: any, maxLen = 50_000): string => {
  if (data === undefined) return 'undefined';
  if (data === null) return 'null';
  try {
    const seen = new WeakSet();
    const replacer = (_key: string, value: any) => {
      if (typeof value === 'object' && value !== null) {
        if (seen.has(value)) return '[Circular]';
        seen.add(value);
      }
      return value;
    };
    const str = JSON.stringify(data, replacer, 2);
    if (str.length > maxLen) {
      return `${str.slice(0, maxLen)}\n\n…（已截断，共 ${str.length} 字符）`;
    }
    return str;
  } catch {
    return String(data);
  }
};

// 切换单个步骤展开
const toggleStep = (index: number) => {
  if (expandedSteps.value.has(index)) {
    expandedSteps.value.delete(index);
  } else {
    expandedSteps.value.add(index);
  }
  // 触发响应式更新
  expandedSteps.value = new Set(expandedSteps.value);
};

// 展开全部
const expandAll = () => {
  expandedSteps.value = new Set((props.trace.steps || []).map((_, i) => i));
};

// 收起全部
const collapseAll = () => {
  expandedSteps.value = new Set();
};

// 复制完整 trace_id（优先 Clipboard API，fallback 用 textarea + select）
const copyTraceId = async () => {
  if (!props.trace.trace_id) return;
  const text = props.trace.trace_id;
  try {
    await navigator.clipboard.writeText(text);
    copied.value = true;
    message.success('链路 ID 已复制');
  } catch {
    // Clipboard API 不可用（如非 HTTPS 环境），走 textarea 兜底
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      copied.value = true;
      message.success('链路 ID 已复制');
    } catch {
      message.error('复制失败，请手动选择');
    }
    document.body.removeChild(ta);
  }
  setTimeout(() => (copied.value = false), 1500);
};

// 复制完整 JSON
const copyAsJson = async () => {
  const json = stringify(props.trace, 1_000_000);
  try {
    await navigator.clipboard.writeText(json);
    jsonCopied.value = true;
    message.success('完整 JSON 已复制');
  } catch {
    const ta = document.createElement('textarea');
    ta.value = json;
    ta.style.cssText = 'position:fixed;left:-9999px;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      jsonCopied.value = true;
      message.success('完整 JSON 已复制');
    } catch {
      message.error('复制失败');
    }
    document.body.removeChild(ta);
  }
  setTimeout(() => (jsonCopied.value = false), 1500);
};

// 获取节点样式
const getNodeClass = (step: string) => {
  const map: Record<string, string> = {
    INIT: 'node-init',
    ENVIRONMENT_SENSE: 'node-sense',
    INTENT_ANALYSIS: 'node-analysis',
    SAFETY_VALIDATION: 'node-safety',
    TOOL_EXECUTION: 'node-tool',
    FINAL_DECISION: 'node-decision',
  };
  return map[step] || 'node-default';
};

// 获取步骤图标
const getStepIcon = (step: string) => {
  const map: Record<string, string> = {
    INIT: 'lucide:play-circle',
    ENVIRONMENT_SENSE: 'lucide:scan-eye',
    INTENT_ANALYSIS: 'lucide:brain',
    SAFETY_VALIDATION: 'lucide:shield-check',
    TOOL_EXECUTION: 'lucide:wrench',
    FINAL_DECISION: 'lucide:gavel',
  };
  return map[step] || 'lucide:circle-dot';
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

// 获取步骤颜色
const getStepColor = (step: string) => {
  const map: Record<string, string> = {
    INIT: 'default',
    ENVIRONMENT_SENSE: 'blue',
    INTENT_ANALYSIS: 'orange',
    SAFETY_VALIDATION: 'red',
    TOOL_EXECUTION: 'green',
    FINAL_DECISION: 'purple',
  };
  return map[step] || 'default';
};

// 获取步骤摘要
const getStepSummary = (step: { step: string; data?: Record<string, any> }) => {
  const data = step.data || {};
  switch (step.step) {
    case 'INIT':
      return '初始化推理链路，准备处理用户请求';
    case 'ENVIRONMENT_SENSE':
      return data.snapshot?.system_info
        ? `采集系统状态: ${data.snapshot.system_info.hostname || '未知主机'}`
        : '采集系统环境信息';
    case 'INTENT_ANALYSIS':
      if (data.analysis?.intent) return `识别意图: ${data.analysis.intent}`;
      if (data.intent) return `识别意图: ${data.intent}`;
      return '分析用户指令意图';
    case 'SAFETY_VALIDATION':
      if (data.validation?.is_safe === false || data.is_safe === false) {
        return `安全拦截: ${data.validation?.overall_risk || data.risk_level || '高风险'}`;
      }
      return '安全校验通过';
    case 'TOOL_EXECUTION':
      return data.tool ? `调用工具: ${data.tool}` : '执行运维工具';
    case 'FINAL_DECISION':
      return data.decision?.response || data.decision || '生成最终响应';
    default:
      return '处理中...';
  }
};

// 格式化时间（withDate=false 时仅显示时分秒毫秒）
const formatTime = (timestamp?: string, withDate = false) => {
  if (!timestamp) return '-';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '-';
  if (withDate) {
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3,
  });
};

// 友好时长格式化
const formatDuration = (ms: number): string => {
  if (!ms || ms < 0) return '0ms';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(2)}s`;
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return s === 0 ? `${m}m` : `${m}m ${s}s`;
};
</script>

<style scoped>
.trace-visualization {
  max-height: 65vh;
  overflow-y: auto;
  padding-right: 8px;
}

/* 概览 */
.trace-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}

.overview-item {
  text-align: center;
  min-width: 0;
}

.overview-label {
  font-size: 11px;
  color: #8c8c8c;
  margin-bottom: 4px;
}

.overview-value {
  font-size: 13px;
  font-weight: 500;
  color: #262626;
  word-break: break-all;
}

.overview-value.mono {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 11px;
}

.overview-trace-id {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  justify-content: center;
}

.trace-id-text {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.copy-btn {
  background: transparent;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 0 4px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #595959;
  transition: all 0.15s ease;
}

.copy-btn:hover {
  background: #fff;
  border-color: #722ed1;
  color: #722ed1;
}

/* 顶部工具栏 */
.trace-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
  padding: 4px 0;
  border-bottom: 1px dashed #f0f0f0;
}

.step-counter {
  font-weight: 400;
  color: #8c8c8c;
  font-size: 12px;
  margin-left: 2px;
}

/* 区块标签 */
.section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #262626;
  margin-bottom: 8px;
}

/* 用户输入 */
.user-prompt-section {
  margin-bottom: 16px;
}

.prompt-content {
  padding: 12px;
  background: #e6f7ff;
  border: 1px solid #91d5ff;
  border-radius: 8px;
  font-size: 14px;
  color: #262626;
  line-height: 1.5;
  word-break: break-word;
}

/* 时间轴 */
.timeline-section {
  margin-bottom: 16px;
}

.timeline {
  position: relative;
  padding-left: 40px;
}

.timeline-item {
  position: relative;
  margin-bottom: 16px;
}

.timeline-connector {
  position: absolute;
  left: -28px;
  top: -16px;
  width: 2px;
  height: 32px;
  background: #e8e8e8;
}

.timeline-node {
  position: absolute;
  left: -40px;
  top: 8px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  z-index: 2;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.node-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  color: #262626;
  font-size: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #d9d9d9;
  font-weight: 600;
}

/* 节点颜色 */
.node-init { background: #8c8c8c; }
.node-sense { background: #1890ff; }
.node-analysis { background: #faad14; }
.node-safety { background: #ff4d4f; }
.node-tool { background: #52c41a; }
.node-decision { background: #722ed1; }
.node-default { background: #bfbfbf; }

/* 卡片 */
.timeline-card {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.timeline-card:hover {
  border-color: #d9d9d9;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.timeline-item.expanded .timeline-card {
  border-color: #d3adf7;
  background: #fff;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  gap: 8px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-time {
  font-size: 11px;
  color: #8c8c8c;
  font-family: monospace;
}

.expand-icon {
  color: #8c8c8c;
  transition: transform 0.2s ease;
}

.card-summary {
  font-size: 13px;
  color: #595959;
  line-height: 1.5;
  word-break: break-word;
}

.card-detail {
  margin-top: 8px;
}

.card-detail pre {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
  margin: 0;
  line-height: 1.55;
  font-family: 'JetBrains Mono', 'Fira Code', Monaco, Menlo, monospace;
}

/* 分块化详情：键值对布局 */
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  background: #fafafa;
  border-radius: 6px;
  border-left: 2px solid #d9d9d9;
}

.detail-key {
  font-size: 11px;
  font-weight: 600;
  color: #8c8c8c;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  font-size: 13px;
  color: #262626;
  word-break: break-all;
}

.detail-row .detail-code {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 280px;
  overflow-y: auto;
  margin: 0;
  font-family: 'JetBrains Mono', 'Fira Code', Monaco, Menlo, monospace;
  line-height: 1.55;
}

.no-data {
  font-size: 12px;
  color: #bfbfbf;
  text-align: center;
  padding: 12px;
}

/* 最终结果 */
.final-result-section {
  margin-top: 16px;
}

.result-content pre {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  padding: 12px;
  border-radius: 8px;
  font-size: 13px;
  overflow-x: auto;
  margin: 0;
  word-break: break-word;
  font-family: 'JetBrains Mono', 'Fira Code', Monaco, Menlo, monospace;
  line-height: 1.55;
  max-height: 400px;
  overflow-y: auto;
}

/* 滚动条 */
.trace-visualization::-webkit-scrollbar {
  width: 6px;
}

.trace-visualization::-webkit-scrollbar-thumb {
  background: #d9d9d9;
  border-radius: 3px;
}

.trace-visualization::-webkit-scrollbar-thumb:hover {
  background: #bfbfbf;
}

/* ============================================================
 * 响应式适配
 * 设计目标：在不同屏幕尺寸下保持良好的可读性
 * ============================================================ */

/* 平板及以下：概览从 4 列变 2 列 */
@media (max-width: 768px) {
  .trace-overview {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    padding: 10px;
  }

  .trace-id-text {
    max-width: 80px;
  }

  .trace-toolbar {
    flex-wrap: wrap;
    gap: 4px;
  }
}

/* 手机：时间轴更紧凑 */
@media (max-width: 576px) {
  .trace-visualization {
    max-height: 70vh;
    padding-right: 4px;
  }

  .timeline {
    padding-left: 32px;
  }

  .timeline-node {
    left: -32px;
    width: 24px;
    height: 24px;
  }

  .timeline-connector {
    left: -20px;
  }

  .timeline-card {
    padding: 10px;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .step-name {
    font-size: 13px;
  }

  .card-summary {
    font-size: 12px;
  }

  .detail-row {
    padding: 6px 8px;
  }
}
</style>
