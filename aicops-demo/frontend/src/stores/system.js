import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { systemApi, toolsApi, tracesApi, safetyApi } from '@/api'

export const useSystemStore = defineStore('system', () => {
  const systemStatus = ref(null)
  const processes = ref([])
  const disks = ref([])
  const tools = ref([])
  const traces = ref([])
  const safetyStats = ref(null)
  const safetyEvents = ref([])
  const loading = ref(false)

  const cpuUsage = computed(() => systemStatus.value?.cpu?.overall ?? 0)
  const memoryUsage = computed(() => systemStatus.value?.memory?.percent ?? 0)
  const memoryTotal = computed(() => {
    const total = systemStatus.value?.memory?.total ?? 0
    return (total / 1024 / 1024 / 1024).toFixed(2)
  })
  const memoryUsed = computed(() => {
    const used = systemStatus.value?.memory?.used ?? 0
    return (used / 1024 / 1024 / 1024).toFixed(2)
  })
  const processCount = computed(() => processes.value.length ?? 0)
  const diskCount = computed(() => disks.value.length ?? 0)

  const systemInfo = computed(() => systemStatus.value?.system_info ?? {})

  async function fetchSystemStatus() {
    loading.value = true
    try {
      const [statusRes, processesRes, disksRes] = await Promise.all([
        systemApi.getStatus(),
        systemApi.getProcesses(30),
        systemApi.getDisks(),
      ])
      systemStatus.value = statusRes.data
      processes.value = processesRes.data
      disks.value = disksRes.data
    } catch (error) {
      console.error('获取系统状态失败:', error)
    } finally {
      loading.value = false
    }
  }

  async function fetchTools() {
    try {
      const response = await toolsApi.list()
      tools.value = response.data || []
    } catch (error) {
      console.error('获取工具列表失败:', error)
    }
  }

  async function fetchTraces() {
    try {
      const response = await tracesApi.list()
      traces.value = response.traces || []
    } catch (error) {
      console.error('获取推理链路失败:', error)
    }
  }

  async function fetchSafetyStats() {
    try {
      const response = await safetyApi.getStats()
      safetyStats.value = response
    } catch (error) {
      console.error('获取安全统计失败:', error)
    }
  }

  async function fetchSafetyEvents(limit = 100) {
    try {
      const response = await safetyApi.getEvents(limit)
      const events = response.events || response || []
      safetyEvents.value = events
      return events
    } catch (error) {
      console.error('获取安全事件失败:', error)
      return []
    }
  }

  async function executeTool(toolName, params = {}) {
    try {
      const response = await toolsApi.execute(toolName, params)
      return response
    } catch (error) {
      console.error('执行工具失败:', error)
      throw error
    }
  }

  return {
    systemStatus,
    processes,
    disks,
    tools,
    traces,
    safetyStats,
    safetyEvents,
    loading,
    cpuUsage,
    memoryUsage,
    memoryTotal,
    memoryUsed,
    processCount,
    diskCount,
    systemInfo,
    fetchSystemStatus,
    fetchTools,
    fetchTraces,
    fetchSafetyStats,
    fetchSafetyEvents,
    executeTool,
  }
})
