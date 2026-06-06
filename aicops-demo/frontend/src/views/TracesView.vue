<template>
  <div class="traces-view page-container">
    <div class="traces-header">
      <div class="header-info">
        <h3>推理链路溯源</h3>
        <p>完整记录 Agent 的推理决策过程，支持异常回溯和审计</p>
      </div>
      <el-button :icon="Refresh" @click="refreshTraces">刷新</el-button>
    </div>

    <div class="traces-content">
      <div class="traces-list">
        <div
          v-for="trace in systemStore.traces"
          :key="trace.trace_id"
          class="trace-item"
          :class="{ active: selectedTrace?.trace_id === trace.trace_id }"
          @click="selectTrace(trace)"
        >
          <div class="trace-header">
            <el-tag :type="getStatusType(trace.final_result?.status)" size="small">
              {{ trace.final_result?.status || 'unknown' }}
            </el-tag>
            <span class="trace-id">{{ trace.trace_id.substring(0, 8) }}...</span>
          </div>
          <div class="trace-prompt">{{ trace.user_prompt }}</div>
          <div class="trace-meta">
            <span class="trace-time">{{ formatTime(trace.start_time) }}</span>
            <span v-if="getTotalDuration(trace)" class="trace-duration">
              {{ getTotalDuration(trace) }}
            </span>
          </div>
        </div>
      </div>

      <div class="trace-detail" v-if="selectedTrace">
        <div class="detail-header">
          <div class="detail-header-left">
            <h4>推理链路详情</h4>
            <el-tag :type="getStatusType(selectedTrace.final_result?.status)">
              {{ selectedTrace.final_result?.status }}
            </el-tag>
          </div>
          <div class="detail-header-right">
            <span class="total-duration-label">推理耗时</span>
            <span class="total-duration-value">{{ getTotalDuration(selectedTrace) || '--' }}</span>
          </div>
        </div>

        <div class="timeline">
          <div
            v-for="(step, idx) in selectedTrace.steps"
            :key="idx"
            class="timeline-item"
          >
            <div class="timeline-dot" :class="getStepClass(step.step)" />
            <div class="timeline-content">
              <div class="step-header">
                <div class="step-header-left">
                  <el-icon class="step-icon" :color="getStepIconColor(step.step)">
                    <component :is="getStepIcon(step.step)" />
                  </el-icon>
                  <span class="step-name">{{ getStepName(step.step) }}</span>
                  <el-tag
                    v-if="step.step === 'SAFETY_VALIDATION'"
                    :type="step.data?.decision === 'blocked' ? 'danger' : 'success'"
                    size="small"
                  >
                    {{ step.data?.decision === 'blocked' ? '已拦截' : '已通过' }}
                  </el-tag>
                  <el-tag
                    v-if="step.step === 'TOOL_EXECUTION'"
                    :type="step.data?.success !== false ? 'success' : 'danger'"
                    size="small"
                  >
                    {{ step.data?.tool_name || '工具调用' }}
                  </el-tag>
                </div>
                <div class="step-header-right">
                  <span
                    v-if="idx > 0 && getStepDuration(selectedTrace.steps[idx - 1], step)"
                    class="step-duration"
                  >
                    +{{ getStepDuration(selectedTrace.steps[idx - 1], step) }}
                  </span>
                  <span class="step-time">{{ formatTime(step.timestamp) }}</span>
                </div>
              </div>

              <div class="step-data">
                <div v-if="step.step === 'ENVIRONMENT_SENSE'" class="env-sense-summary">
                  <div class="env-metrics" v-if="step.data?.cpu_percent !== undefined || step.data?.memory_percent !== undefined">
                    <div class="env-metric" v-if="step.data?.cpu_percent !== undefined">
                      <span class="metric-label">CPU</span>
                      <el-progress
                        :percentage="step.data.cpu_percent"
                        :stroke-width="8"
                        :color="getStatusColor(step.data.cpu_percent)"
                      />
                    </div>
                    <div class="env-metric" v-if="step.data?.memory_percent !== undefined">
                      <span class="metric-label">内存</span>
                      <el-progress
                        :percentage="step.data.memory_percent"
                        :stroke-width="8"
                        :color="getStatusColor(step.data.memory_percent)"
                      />
                    </div>
                  </div>
                  <div v-if="step.data?.findings?.length" class="env-findings">
                    <div v-for="(finding, fi) in step.data.findings" :key="fi" class="finding-item">
                      <el-icon :color="finding.severity === 'high' ? '#f56c6c' : '#e6a23c'">
                        <Warning />
                      </el-icon>
                      <span>{{ finding.message || finding }}</span>
                    </div>
                  </div>
                  <pre v-if="hasExtraData(step.data, ['cpu_percent', 'memory_percent', 'findings'])" class="raw-data">{{ formatExtraData(step.data, ['cpu_percent', 'memory_percent', 'findings']) }}</pre>
                </div>

                <div v-else-if="step.step === 'SAFETY_VALIDATION'" class="safety-summary">
                  <div class="safety-row" v-if="step.data?.risk_level">
                    <span class="safety-label">风险等级</span>
                    <el-tag
                      :type="getRiskTagType(step.data.risk_level)"
                      size="small"
                    >
                      {{ step.data.risk_level }}
                    </el-tag>
                  </div>
                  <div class="safety-row" v-if="step.data?.decision">
                    <span class="safety-label">决策结果</span>
                    <el-tag
                      :type="step.data.decision === 'blocked' ? 'danger' : 'success'"
                      size="small"
                    >
                      {{ step.data.decision === 'blocked' ? '拦截' : '通过' }}
                    </el-tag>
                  </div>
                  <div v-if="step.data?.reasons?.length" class="safety-reasons">
                    <div class="safety-label">拦截原因</div>
                    <ul>
                      <li v-for="(reason, ri) in step.data.reasons" :key="ri">{{ reason }}</li>
                    </ul>
                  </div>
                  <pre v-if="hasExtraData(step.data, ['risk_level', 'decision', 'reasons'])" class="raw-data">{{ formatExtraData(step.data, ['risk_level', 'decision', 'reasons']) }}</pre>
                </div>

                <div v-else-if="step.step === 'TOOL_EXECUTION'" class="tool-summary">
                  <div class="tool-row">
                    <span class="tool-label">工具名称</span>
                    <span class="tool-value">{{ step.data?.tool_name || '--' }}</span>
                  </div>
                  <div class="tool-row" v-if="step.data?.params">
                    <span class="tool-label">调用参数</span>
                    <code class="tool-params">{{ summarizeParams(step.data.params) }}</code>
                  </div>
                  <div class="tool-row" v-if="step.data?.result !== undefined">
                    <span class="tool-label">执行结果</span>
                    <span class="tool-value" :class="step.data?.success !== false ? 'text-success' : 'text-danger'">
                      {{ step.data?.success !== false ? '成功' : '失败' }}
                    </span>
                  </div>
                  <pre v-if="hasExtraData(step.data, ['tool_name', 'params', 'result', 'success'])" class="raw-data">{{ formatExtraData(step.data, ['tool_name', 'params', 'result', 'success']) }}</pre>
                </div>

                <div v-else-if="step.step === 'FINAL_DECISION'" class="final-summary">
                  <div class="final-answer" v-if="step.data?.answer">
                    <div class="final-label">回答摘要</div>
                    <div class="final-text">{{ truncateText(step.data.answer, 200) }}</div>
                  </div>
                  <div class="final-row" v-if="step.data?.status">
                    <span class="final-label">状态</span>
                    <el-tag :type="getStatusType(step.data.status)" size="small">
                      {{ step.data.status }}
                    </el-tag>
                  </div>
                  <pre v-if="hasExtraData(step.data, ['answer', 'status'])" class="raw-data">{{ formatExtraData(step.data, ['answer', 'status']) }}</pre>
                </div>

                <pre v-else class="raw-data">{{ JSON.stringify(step.data, null, 2) }}</pre>
              </div>
            </div>
          </div>
        </div>

        <div class="final-result" v-if="selectedTrace.final_result">
          <h4>最终结果</h4>
          <pre>{{ JSON.stringify(selectedTrace.final_result, null, 2) }}</pre>
        </div>
      </div>

      <div v-else class="empty-detail">
        <el-empty description="请选择一条推理链路查看详情" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import {
  Refresh,
  Warning,
  Monitor,
  Aim,
  UserFilled,
  SetUp,
  Select,
  Document,
  Loading,
} from '@element-plus/icons-vue'

const systemStore = useSystemStore()
const selectedTrace = ref(null)

function getStatusType(status) {
  const typeMap = {
    success: 'success',
    blocked: 'danger',
    error: 'warning',
  }
  return typeMap[status] || 'info'
}

function getStepClass(step) {
  const classMap = {
    INIT: 'init',
    ENVIRONMENT_SENSE: 'sense',
    INTENT_ANALYSIS: 'analysis',
    SAFETY_VALIDATION: 'safety',
    TOOL_EXECUTION: 'tool',
    FINAL_DECISION: 'decision',
    TOOL_CALL: 'tool',
    SAFETY_BLOCKED: 'safety-blocked',
    MULTI_STEP: 'multi',
  }
  return classMap[step] || 'default'
}

function getStepIcon(step) {
  const iconMap = {
    INIT: Document,
    ENVIRONMENT_SENSE: Monitor,
    INTENT_ANALYSIS: Aim,
    SAFETY_VALIDATION: UserFilled,
    TOOL_EXECUTION: SetUp,
    FINAL_DECISION: Select,
    TOOL_CALL: SetUp,
    SAFETY_BLOCKED: UserFilled,
    MULTI_STEP: Loading,
  }
  return iconMap[step] || Document
}

function getStepIconColor(step) {
  const colorMap = {
    INIT: '#909399',
    ENVIRONMENT_SENSE: '#409eff',
    INTENT_ANALYSIS: '#e6a23c',
    SAFETY_VALIDATION: '#f56c6c',
    TOOL_EXECUTION: '#67c23a',
    FINAL_DECISION: '#6366f1',
    TOOL_CALL: '#67c23a',
    SAFETY_BLOCKED: '#f56c6c',
    MULTI_STEP: '#409eff',
  }
  return colorMap[step] || '#909399'
}

function getStepName(step) {
  const nameMap = {
    INIT: '接收指令',
    ENVIRONMENT_SENSE: '环境感知',
    INTENT_ANALYSIS: '意图分析',
    SAFETY_VALIDATION: '安全校验',
    TOOL_EXECUTION: '工具执行',
    FINAL_DECISION: '最终决策',
    TOOL_CALL: '工具调用',
    SAFETY_BLOCKED: '安全拦截',
    MULTI_STEP: '多步推理',
  }
  return nameMap[step] || step
}

function getRiskTagType(level) {
  if (!level) return 'info'
  const l = String(level).toLowerCase()
  if (l === 'high' || l === 'critical') return 'danger'
  if (l === 'medium') return 'warning'
  if (l === 'low') return 'info'
  return 'success'
}

function getStatusColor(value) {
  if (value < 60) return '#67c23a'
  if (value < 80) return '#e6a23c'
  return '#f56c6c'
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('zh-CN')
}

function getStepDuration(prevStep, currentStep) {
  if (!prevStep?.timestamp || !currentStep?.timestamp) return ''
  const diff = new Date(currentStep.timestamp) - new Date(prevStep.timestamp)
  if (diff < 1000) return `${diff}ms`
  return `${(diff / 1000).toFixed(1)}s`
}

function getTotalDuration(trace) {
  if (!trace?.steps?.length || trace.steps.length < 2) return ''
  const first = trace.steps[0]
  const last = trace.steps[trace.steps.length - 1]
  if (!first?.timestamp || !last?.timestamp) return ''
  const diff = new Date(last.timestamp) - new Date(first.timestamp)
  if (diff < 1000) return `${diff}ms`
  return `${(diff / 1000).toFixed(1)}s`
}

function summarizeParams(params) {
  if (!params) return '--'
  if (typeof params === 'string') return params
  const entries = Object.entries(params)
  if (entries.length === 0) return '{}'
  return entries.map(([k, v]) => `${k}=${v}`).join(', ')
}

function truncateText(text, maxLen) {
  if (!text) return ''
  if (text.length <= maxLen) return text
  return text.substring(0, maxLen) + '...'
}

function hasExtraData(data, excludeKeys) {
  if (!data) return false
  const extraKeys = Object.keys(data).filter(k => !excludeKeys.includes(k))
  return extraKeys.length > 0
}

function formatExtraData(data, excludeKeys) {
  if (!data) return ''
  const filtered = {}
  for (const [k, v] of Object.entries(data)) {
    if (!excludeKeys.includes(k)) {
      filtered[k] = v
    }
  }
  return JSON.stringify(filtered, null, 2)
}

function selectTrace(trace) {
  selectedTrace.value = trace
}

async function refreshTraces() {
  await systemStore.fetchTraces()
}

onMounted(() => {
  systemStore.fetchTraces()
})
</script>

<style lang="scss" scoped>
.traces-header {
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

.traces-content {
  display: flex;
  gap: 20px;
  height: calc(100vh - 200px);
}

.traces-list {
  width: 320px;
  background: #fff;
  border-radius: 12px;
  overflow-y: auto;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.trace-item {
  padding: 16px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: #f5f7fa;
  }

  &.active {
    background: #ecf5ff;
    border-left: 3px solid #409eff;
  }
}

.trace-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.trace-id {
  font-size: 12px;
  color: #909399;
  font-family: monospace;
}

.trace-prompt {
  font-size: 13px;
  color: #303133;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trace-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.trace-time {
  font-size: 11px;
  color: #909399;
}

.trace-duration {
  font-size: 11px;
  color: #6366f1;
  font-weight: 500;
  background: rgba(99, 102, 241, 0.08);
  padding: 1px 6px;
  border-radius: 4px;
}

.trace-detail {
  flex: 1;
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  overflow-y: auto;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.detail-header-left {
  display: flex;
  align-items: center;
  gap: 12px;

  h4 {
    font-size: 16px;
    color: #1a1f36;
  }
}

.detail-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.total-duration-label {
  font-size: 13px;
  color: #909399;
}

.total-duration-value {
  font-size: 16px;
  font-weight: 700;
  color: #6366f1;
}

.timeline {
  position: relative;
  padding-left: 24px;

  &::before {
    content: '';
    position: absolute;
    left: 8px;
    top: 0;
    bottom: 0;
    width: 2px;
    background: #e4e7ed;
  }
}

.timeline-item {
  position: relative;
  margin-bottom: 20px;
}

.timeline-dot {
  position: absolute;
  left: -20px;
  top: 4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #409eff;
  border: 2px solid #fff;
  box-shadow: 0 0 0 2px #409eff;

  &.init { background: #909399; box-shadow: 0 0 0 2px #909399; }
  &.sense { background: #409eff; box-shadow: 0 0 0 2px #409eff; }
  &.analysis { background: #e6a23c; box-shadow: 0 0 0 2px #e6a23c; }
  &.safety { background: #f56c6c; box-shadow: 0 0 0 2px #f56c6c; }
  &.safety-blocked { background: #f56c6c; box-shadow: 0 0 0 2px #f56c6c; }
  &.tool { background: #67c23a; box-shadow: 0 0 0 2px #67c23a; }
  &.decision { background: #6366f1; box-shadow: 0 0 0 2px #6366f1; }
  &.multi { background: #409eff; box-shadow: 0 0 0 2px #409eff; }
}

.timeline-content {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
}

.step-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.step-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-icon {
  font-size: 16px;
}

.step-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.step-duration {
  font-size: 11px;
  color: #6366f1;
  font-weight: 500;
}

.step-time {
  font-size: 11px;
  color: #909399;
}

.step-data {
  .raw-data {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 12px;
    border-radius: 6px;
    font-size: 12px;
    overflow-x: auto;
    max-height: 200px;
    overflow-y: auto;
  }
}

.env-sense-summary {
  .env-metrics {
    display: flex;
    gap: 16px;
    margin-bottom: 8px;
  }

  .env-metric {
    flex: 1;

    .metric-label {
      font-size: 12px;
      color: #606266;
      font-weight: 500;
      display: block;
      margin-bottom: 4px;
    }
  }

  .env-findings {
    margin-bottom: 8px;
  }

  .finding-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: #606266;
    padding: 4px 0;
  }
}

.safety-summary {
  .safety-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }

  .safety-label {
    font-size: 12px;
    color: #606266;
    font-weight: 500;
    min-width: 60px;
  }

  .safety-reasons {
    margin-bottom: 8px;

    ul {
      margin: 4px 0 0 0;
      padding-left: 16px;
    }

    li {
      font-size: 13px;
      color: #606266;
      line-height: 1.8;
    }
  }
}

.tool-summary {
  .tool-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }

  .tool-label {
    font-size: 12px;
    color: #606266;
    font-weight: 500;
    min-width: 60px;
  }

  .tool-value {
    font-size: 13px;
    color: #303133;
  }

  .tool-params {
    font-size: 12px;
    background: rgba(0, 0, 0, 0.04);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
    color: #606266;
  }

  .text-success { color: #67c23a; }
  .text-danger { color: #f56c6c; }
}

.final-summary {
  .final-answer {
    margin-bottom: 8px;
  }

  .final-label {
    font-size: 12px;
    color: #606266;
    font-weight: 500;
    margin-bottom: 4px;
  }

  .final-text {
    font-size: 13px;
    color: #303133;
    line-height: 1.6;
    background: #fff;
    padding: 8px 12px;
    border-radius: 6px;
    border: 1px solid #ebeef5;
  }

  .final-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
}

.final-result {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #ebeef5;

  h4 {
    font-size: 14px;
    color: #303133;
    margin-bottom: 12px;
  }

  pre {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 16px;
    border-radius: 8px;
    font-size: 12px;
    overflow-x: auto;
    max-height: 300px;
    overflow-y: auto;
  }
}

.empty-detail {
  flex: 1;
  background: #fff;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}
</style>
