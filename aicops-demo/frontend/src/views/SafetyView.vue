<template>
  <div class="safety-view page-container">
    <div class="safety-header">
      <div class="header-info">
        <h3>安全护栏</h3>
        <p>五层纵深防御体系运行状态与安全事件记录</p>
      </div>
      <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
    </div>

    <div class="guardrail-grid">
      <div
        v-for="layer in guardrailLayers"
        :key="layer.id"
        class="guardrail-card"
      >
        <div class="guardrail-icon" :style="{ background: layer.bgColor }">
          <el-icon :size="24" :color="layer.color">
            <component :is="layer.icon" />
          </el-icon>
        </div>
        <div class="guardrail-info">
          <div class="guardrail-title">
            <span class="layer-id">{{ layer.id }}</span>
            <span class="layer-name">{{ layer.name }}</span>
          </div>
          <div class="guardrail-class">{{ layer.className }}</div>
          <el-tag :type="layer.statusType" size="small">{{ layer.statusText }}</el-tag>
          <div class="guardrail-desc">{{ layer.desc }}</div>
        </div>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card" v-for="stat in safetyStats" :key="stat.label">
        <div class="stat-icon" :style="{ background: stat.bgColor }">
          <el-icon :size="24" :color="stat.color">
            <component :is="stat.icon" />
          </el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="title">
          <el-icon><List /></el-icon>
          安全事件记录
        </div>
      </div>
      <el-table
        v-loading="eventsLoading"
        :data="events"
        stripe
        style="width: 100%"
        max-height="480"
      >
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="user_input" label="用户输入" min-width="200" show-overflow-tooltip />
        <el-table-column prop="risk_level" label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag :type="getRiskTagType(row.risk_level)" size="small">
              {{ getRiskLabel(row.risk_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_layer" label="触发层" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.trigger_layer }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="拦截原因" min-width="240" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!eventsLoading && events.length === 0" description="暂无安全事件" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import {
  Refresh,
  Filter,
  Aim,
  Warning,
  Lock,
  UserFilled,
  DataLine,
  CircleClose,
  WarningFilled,
  List,
} from '@element-plus/icons-vue'

const systemStore = useSystemStore()

const eventsLoading = ref(false)
const events = ref([])

const guardrailLayers = [
  {
    id: 'L1',
    name: '输入净化',
    className: 'InputSanitizer',
    icon: Filter,
    color: '#409eff',
    bgColor: 'rgba(64, 158, 255, 0.1)',
    statusType: 'success',
    statusText: '运行中',
    desc: '过滤用户输入中的恶意字符与特殊编码',
  },
  {
    id: 'L2',
    name: '意图分类',
    className: 'IntentClassifier',
    icon: Aim,
    color: '#67c23a',
    bgColor: 'rgba(103, 194, 58, 0.1)',
    statusType: 'success',
    statusText: '运行中',
    desc: '识别用户意图类别，拦截高风险操作请求',
  },
  {
    id: 'L3',
    name: '风险评分',
    className: 'RiskScorer',
    icon: Warning,
    color: '#e6a23c',
    bgColor: 'rgba(230, 162, 60, 0.1)',
    statusType: 'success',
    statusText: '运行中',
    desc: '基于多维度评分模型评估请求风险等级',
  },
  {
    id: 'L4',
    name: '参数校验',
    className: 'ParameterValidator',
    icon: Lock,
    color: '#f56c6c',
    bgColor: 'rgba(245, 108, 108, 0.1)',
    statusType: 'success',
    statusText: '运行中',
    desc: '校验工具调用参数的合法性与边界条件',
  },
  {
    id: 'L5',
    name: '注入检测',
    className: 'InjectionDetector',
    icon: UserFilled,
    color: '#6366f1',
    bgColor: 'rgba(99, 102, 241, 0.1)',
    statusType: 'success',
    statusText: '运行中',
    desc: '检测 Prompt Injection 与间接注入攻击',
  },
]

const safetyStats = computed(() => {
  const stats = systemStore.safetyStats || {}
  return [
    {
      label: '总检查次数',
      value: stats.total_checks ?? 0,
      icon: DataLine,
      color: '#409eff',
      bgColor: 'rgba(64, 158, 255, 0.1)',
    },
    {
      label: '拦截次数',
      value: stats.blocked_count ?? 0,
      icon: CircleClose,
      color: '#f56c6c',
      bgColor: 'rgba(245, 108, 108, 0.1)',
    },
    {
      label: '高危拦截',
      value: stats.high_risk_blocked ?? 0,
      icon: WarningFilled,
      color: '#e6a23c',
      bgColor: 'rgba(230, 162, 60, 0.1)',
    },
    {
      label: '拦截率(%)',
      value: stats.block_rate ?? '0',
      icon: UserFilled,
      color: '#6366f1',
      bgColor: 'rgba(99, 102, 241, 0.1)',
    },
  ]
})

function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('zh-CN')
}

function getRiskTagType(level) {
  const map = {
    safe: 'success',
    low: 'info',
    medium: 'warning',
    high: 'danger',
    critical: 'danger',
  }
  return map[level] || 'info'
}

function getRiskLabel(level) {
  const map = {
    safe: '安全',
    low: '低',
    medium: '中',
    high: '高',
    critical: '严重',
  }
  return map[level] || level
}

function getStatusTagType(status) {
  const map = {
    blocked: 'danger',
    approved: 'success',
    confirmed: 'warning',
  }
  return map[status] || 'info'
}

function getStatusLabel(status) {
  const map = {
    blocked: '已拦截',
    approved: '已通过',
    confirmed: '已确认',
  }
  return map[status] || status
}

async function refreshAll() {
  await Promise.all([
    systemStore.fetchSafetyStats(),
    loadEvents(),
  ])
}

async function loadEvents() {
  eventsLoading.value = true
  try {
    const data = await systemStore.fetchSafetyEvents(100)
    events.value = data || []
  } catch {
    events.value = []
  } finally {
    eventsLoading.value = false
  }
}

onMounted(() => {
  refreshAll()
})
</script>

<style lang="scss" scoped>
.safety-header {
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

.guardrail-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.guardrail-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.guardrail-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.guardrail-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.guardrail-title {
  display: flex;
  align-items: center;
  gap: 6px;
}

.layer-id {
  font-size: 12px;
  font-weight: 700;
  color: #909399;
  background: #f0f2f5;
  padding: 1px 6px;
  border-radius: 4px;
}

.layer-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.guardrail-class {
  font-size: 12px;
  color: #909399;
  font-family: monospace;
}

.guardrail-desc {
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
  margin-top: 2px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1a1f36;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
</style>
