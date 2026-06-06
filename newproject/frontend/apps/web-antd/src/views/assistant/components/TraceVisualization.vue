<template>
  <div class="trace-visualization">
    <!-- 链路概览头部 -->
    <div class="trace-overview">
      <div class="overview-item">
        <div class="overview-label">链路ID</div>
        <div class="overview-value mono">{{ trace.trace_id }}</div>
      </div>
      <div class="overview-item">
        <div class="overview-label">开始时间</div>
        <div class="overview-value">{{ formatTime(trace.start_time) }}</div>
      </div>
      <div class="overview-item">
        <div class="overview-label">耗时</div>
        <div class="overview-value">{{ duration }}ms</div>
      </div>
      <div class="overview-item">
        <div class="overview-label">步骤数</div>
        <div class="overview-value">{{ trace.steps?.length || 0 }}</div>
      </div>
    </div>

    <!-- 用户输入 -->
    <div class="user-prompt-section">
      <div class="section-label">
        <Icon icon="lucide:user" size="14" />
        用户输入
      </div>
      <div class="prompt-content">{{ trace.user_prompt }}</div>
    </div>

    <!-- 推理链路时间轴 -->
    <div class="timeline-section">
      <div class="section-label">
        <Icon icon="lucide:git-branch" size="14" />
        推理链路
      </div>

      <div class="timeline">
        <div
          v-for="(step, index) in trace.steps"
          :key="index"
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
              <pre v-if="step.data">{{ JSON.stringify(step.data, null, 2) }}</pre>
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
        <pre>{{ JSON.stringify(trace.final_result, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { Icon } from '@iconify/vue';
import type { Trace } from '#/api/core/aiops/agent';

interface Props {
  trace: Trace;
}

const props = defineProps<Props>();

const expandedSteps = ref<Set<number>>(new Set());

// 计算耗时
const duration = computed(() => {
  if (!props.trace.start_time || !props.trace.end_time) return 0;
  const start = new Date(props.trace.start_time).getTime();
  const end = new Date(props.trace.end_time).getTime();
  return end - start;
});

// 切换步骤展开状态
const toggleStep = (index: number) => {
  if (expandedSteps.value.has(index)) {
    expandedSteps.value.delete(index);
  } else {
    expandedSteps.value.add(index);
  }
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
      return data.system_info ? `采集系统状态: ${data.system_info.hostname || '未知主机'}` : '采集系统环境信息';
    case 'INTENT_ANALYSIS':
      return data.intent ? `识别意图: ${data.intent}` : '分析用户指令意图';
    case 'SAFETY_VALIDATION':
      if (data.is_safe === false) {
        return `安全拦截: ${data.risk_level || '高风险'} - ${data.reason || '检测到不安全操作'}`;
      }
      return data.is_safe ? '安全校验通过' : '执行安全风险评估';
    case 'TOOL_EXECUTION':
      return data.tools ? `调用工具: ${data.tools.join(', ')}` : '执行运维工具';
    case 'FINAL_DECISION':
      return data.decision || '生成最终响应';
    default:
      return '处理中...';
  }
};

// 格式化时间
const formatTime = (timestamp?: string) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3,
  });
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
}

.overview-value.mono {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 11px;
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-name {
  font-size: 14px;
  font-weight: 600;
  color: #262626;
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
}

/* 滚动条 */
.trace-visualization::-webkit-scrollbar {
  width: 6px;
}

.trace-visualization::-webkit-scrollbar-thumb {
  background: #d9d9d9;
  border-radius: 3px;
}
</style>
