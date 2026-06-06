<template>
  <div class="dashboard-view page-container">
    <div class="stats-grid">
      <div class="stat-card" v-for="stat in stats" :key="stat.label">
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

    <div class="charts-grid">
      <div class="card">
        <div class="card-header">
          <div class="title">
            <el-icon><Cpu /></el-icon>
            CPU 使用率
          </div>
          <el-tag :type="cpuStatusType" size="small">{{ cpuStatusText }}</el-tag>
        </div>
        <div class="chart-container">
          <div class="gauge-chart">
            <el-progress
              type="dashboard"
              :percentage="systemStore.cpuUsage"
              :color="getStatusColor(systemStore.cpuUsage)"
              :width="160"
            >
              <template #default="{ percentage }">
                <div class="gauge-content">
                  <span class="gauge-value">{{ percentage }}%</span>
                  <span class="gauge-label">CPU</span>
                </div>
              </template>
            </el-progress>
          </div>
          <div class="cpu-cores" v-if="cpuCores.length">
            <div v-for="(core, idx) in cpuCores" :key="idx" class="core-item">
              <span class="core-label">Core {{ idx }}</span>
              <el-progress
                :percentage="core"
                :stroke-width="6"
                :show-text="false"
                :color="getStatusColor(core)"
              />
              <span class="core-value">{{ core }}%</span>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="title">
            <el-icon><Coin /></el-icon>
            内存使用情况
          </div>
          <span class="memory-info">
            {{ systemStore.memoryUsed }}GB / {{ systemStore.memoryTotal }}GB
          </span>
        </div>
        <div class="chart-container">
          <div class="gauge-chart">
            <el-progress
              type="dashboard"
              :percentage="systemStore.memoryUsage"
              :color="getStatusColor(systemStore.memoryUsage)"
              :width="160"
            >
              <template #default="{ percentage }">
                <div class="gauge-content">
                  <span class="gauge-value">{{ percentage }}%</span>
                  <span class="gauge-label">内存</span>
                </div>
              </template>
            </el-progress>
          </div>
          <div class="memory-details">
            <div class="detail-item">
              <span class="detail-label">总计</span>
              <span class="detail-value">{{ systemStore.memoryTotal }} GB</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">已使用</span>
              <span class="detail-value">{{ systemStore.memoryUsed }} GB</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">使用率</span>
              <span class="detail-value">{{ systemStore.memoryUsage }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="title">
          <el-icon><Coin /></el-icon>
          磁盘使用情况
        </div>
        <el-button :icon="Refresh" text @click="refreshData">刷新</el-button>
      </div>
      <el-table :data="systemStore.disks" stripe style="width: 100%">
        <el-table-column prop="device" label="设备" width="180" />
        <el-table-column prop="mountpoint" label="挂载点" width="180" />
        <el-table-column prop="fstype" label="文件系统" width="120" />
        <el-table-column label="总容量" width="120">
          <template #default="{ row }">
            {{ formatBytes(row.total) }}
          </template>
        </el-table-column>
        <el-table-column label="已使用" width="120">
          <template #default="{ row }">
            {{ formatBytes(row.used) }}
          </template>
        </el-table-column>
        <el-table-column label="可用" width="120">
          <template #default="{ row }">
            {{ formatBytes(row.free) }}
          </template>
        </el-table-column>
        <el-table-column label="使用率" min-width="200">
          <template #default="{ row }">
            <el-progress
              :percentage="row.percent"
              :color="getStatusColor(row.percent)"
              :stroke-width="10"
            />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="title">
          <el-icon><List /></el-icon>
          进程列表 (Top 20)
        </div>
        <el-button :icon="Refresh" text @click="refreshData">刷新</el-button>
      </div>
      <el-table :data="systemStore.processes" stripe style="width: 100%" max-height="400">
        <el-table-column prop="pid" label="PID" width="80" />
        <el-table-column prop="name" label="进程名" width="180" />
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column label="CPU %" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.cpu_percent)" size="small">
              {{ row.cpu_percent }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="内存" width="120">
          <template #default="{ row }">
            {{ formatBytes(row.memory_rss) }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useSystemStore } from '@/stores/system'
import { useWebSocket } from '@/utils/websocket'
import {
  Cpu,
  Coin,
  List,
  Refresh,
  Monitor,
  Document,
  Connection,
} from '@element-plus/icons-vue'

const systemStore = useSystemStore()
const { data: wsData, connected: wsConnected } = useWebSocket()

// WebSocket 实时数据更新
watch(wsData, (msg) => {
  if (msg?.type === 'system_status' && msg.data) {
    systemStore.systemStatus = msg.data
  }
})

const stats = computed(() => [
  {
    label: 'CPU 使用率',
    value: `${systemStore.cpuUsage}%`,
    icon: 'Cpu',
    color: '#409eff',
    bgColor: 'rgba(64, 158, 255, 0.1)',
  },
  {
    label: '内存使用率',
    value: `${systemStore.memoryUsage}%`,
    icon: 'Coin',
    color: '#67c23a',
    bgColor: 'rgba(103, 194, 58, 0.1)',
  },
  {
    label: '进程数',
    value: systemStore.processCount,
    icon: 'Document',
    color: '#e6a23c',
    bgColor: 'rgba(230, 162, 60, 0.1)',
  },
  {
    label: '磁盘数',
    value: systemStore.diskCount,
    icon: 'Connection',
    color: '#f56c6c',
    bgColor: 'rgba(245, 108, 108, 0.1)',
  },
])

const cpuCores = computed(() => {
  return systemStore.systemStatus?.cpu?.per_core || []
})

const cpuStatusType = computed(() => {
  if (systemStore.cpuUsage < 60) return 'success'
  if (systemStore.cpuUsage < 80) return 'warning'
  return 'danger'
})

const cpuStatusText = computed(() => {
  if (systemStore.cpuUsage < 60) return '正常'
  if (systemStore.cpuUsage < 80) return '较高'
  return '过高'
})

function getStatusColor(value) {
  if (value < 60) return '#67c23a'
  if (value < 80) return '#e6a23c'
  return '#f56c6c'
}

function getStatusType(value) {
  if (value < 50) return 'success'
  if (value < 80) return 'warning'
  return 'danger'
}

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let idx = 0
  let size = bytes
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024
    idx++
  }
  return `${size.toFixed(2)} ${units[idx]}`
}

async function refreshData() {
  await systemStore.fetchSystemStatus()
}

onMounted(() => {
  systemStore.fetchSystemStatus()
})
</script>

<style lang="scss" scoped>
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

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.chart-container {
  display: flex;
  align-items: center;
  gap: 32px;
}

.gauge-chart {
  flex-shrink: 0;
}

.gauge-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.gauge-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a1f36;
}

.gauge-label {
  font-size: 12px;
  color: #909399;
}

.cpu-cores {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.core-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.core-label {
  font-size: 12px;
  color: #606266;
  width: 48px;
}

.core-value {
  font-size: 12px;
  color: #606266;
  width: 40px;
  text-align: right;
}

.memory-details {
  flex: 1;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #ebeef5;

  &:last-child {
    border-bottom: none;
  }
}

.detail-label {
  font-size: 13px;
  color: #606266;
}

.detail-value {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.memory-info {
  font-size: 13px;
  color: #606266;
}
</style>
