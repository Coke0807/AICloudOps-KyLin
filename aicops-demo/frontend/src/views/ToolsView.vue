<template>
  <div class="tools-view page-container">
    <div class="tools-header">
      <div class="header-info">
        <h3>MCP 运维工具集</h3>
        <p>基于 MCP 协议封装的运维工具插件，支持 Agent 自动调用</p>
      </div>
      <el-button :icon="Refresh" @click="refreshTools">刷新工具列表</el-button>
    </div>

    <div class="tools-grid">
      <div
        v-for="tool in systemStore.tools"
        :key="tool.name"
        class="tool-card"
        @click="handleToolClick(tool)"
      >
        <div class="tool-icon">
          <el-icon :size="32" :color="getToolColor(tool.name)">
            <component :is="getToolIcon(tool.name)" />
          </el-icon>
        </div>
        <div class="tool-info">
          <h4>{{ tool.name }}</h4>
          <p>{{ tool.description }}</p>
        </div>
        <div class="tool-meta">
          <el-tag size="small" :type="getToolTagType(tool.name)">
            {{ getToolCategory(tool.name) }}
          </el-tag>
        </div>
        <div class="tool-params" v-if="Object.keys(tool.params || {}).length">
          <div class="params-title">参数:</div>
          <div v-for="(desc, key) in tool.params" :key="key" class="param-item">
            <code>{{ key }}</code>
            <span>{{ desc }}</span>
          </div>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="`执行工具: ${selectedTool?.name}`"
      width="600px"
    >
      <div class="tool-execute-form">
        <div class="tool-description">
          <p>{{ selectedTool?.description }}</p>
        </div>

        <div v-if="hasParams" class="params-form">
          <div v-for="(desc, key) in selectedTool.params" :key="key" class="form-item">
            <label>{{ key }}</label>
            <el-input v-model="params[key]" :placeholder="desc" />
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="executing" @click="executeTool">
          执行
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="resultVisible"
      title="执行结果"
      width="700px"
    >
      <div class="result-content">
        <pre>{{ JSON.stringify(executeResult, null, 2) }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  Monitor,
  Document,
  DataLine,
  List,
  Connection,
  Setting,
  FirstAidKit,
  Cpu,
  Memo,
  Clock,
  Search,
  FolderOpened,
  Warning,
  Lock,
} from '@element-plus/icons-vue'

const systemStore = useSystemStore()

const dialogVisible = ref(false)
const resultVisible = ref(false)
const selectedTool = ref(null)
const params = ref({})
const executing = ref(false)
const executeResult = ref(null)

const hasParams = computed(() => {
  return selectedTool.value && Object.keys(selectedTool.value.params || {}).length > 0
})

function getToolIcon(name) {
  const iconMap = {
    get_system_status: Monitor,
    get_process_list: Document,
    get_process_detail: Cpu,
    get_open_files: FolderOpened,
    kill_process: Warning,
    get_network_connections: Connection,
    check_port_usage: Connection,
    get_disk_usage: DataLine,
    get_large_files: FolderOpened,
    get_memory_usage: Memo,
    get_memory_top_consumers: Memo,
    query_journal: Document,
    search_log_file: Search,
    get_service_status: Setting,
    list_failed_services: Warning,
    check_failed_logins: Lock,
    get_system_uptime: Clock,
    run_safe_command: FirstAidKit,
    list_available_tools: List,
  }
  return iconMap[name] || Setting
}

function getToolColor(name) {
  const colorMap = {
    get_system_status: '#409eff',
    get_process_list: '#67c23a',
    get_process_detail: '#67c23a',
    get_open_files: '#e6a23c',
    kill_process: '#f56c6c',
    get_network_connections: '#409eff',
    check_port_usage: '#409eff',
    get_disk_usage: '#e6a23c',
    get_large_files: '#e6a23c',
    get_memory_usage: '#409eff',
    get_memory_top_consumers: '#409eff',
    query_journal: '#909399',
    search_log_file: '#909399',
    get_service_status: '#67c23a',
    list_failed_services: '#f56c6c',
    check_failed_logins: '#f56c6c',
    get_system_uptime: '#409eff',
    run_safe_command: '#f56c6c',
    list_available_tools: '#909399',
  }
  return colorMap[name] || '#409eff'
}

function getToolCategory(name) {
  const categoryMap = {
    get_system_status: '监控',
    get_process_list: '进程',
    get_process_detail: '进程',
    get_open_files: '进程',
    kill_process: '进程',
    get_network_connections: '网络',
    check_port_usage: '网络',
    get_disk_usage: '存储',
    get_large_files: '存储',
    get_memory_usage: '内存',
    get_memory_top_consumers: '内存',
    query_journal: '日志',
    search_log_file: '日志',
    get_service_status: '服务',
    list_failed_services: '服务',
    check_failed_logins: '安全',
    get_system_uptime: '系统',
    run_safe_command: '命令',
    list_available_tools: '信息',
  }
  return categoryMap[name] || '工具'
}

function getToolTagType(name) {
  const typeMap = {
    get_system_status: '',
    get_process_list: 'success',
    get_process_detail: 'success',
    get_open_files: 'warning',
    kill_process: 'danger',
    get_network_connections: '',
    check_port_usage: '',
    get_disk_usage: 'warning',
    get_large_files: 'warning',
    get_memory_usage: '',
    get_memory_top_consumers: '',
    query_journal: 'info',
    search_log_file: 'info',
    get_service_status: 'success',
    list_failed_services: 'danger',
    check_failed_logins: 'danger',
    get_system_uptime: '',
    run_safe_command: 'danger',
    list_available_tools: 'info',
  }
  return typeMap[name] || ''
}

function handleToolClick(tool) {
  selectedTool.value = tool
  params.value = {}
  dialogVisible.value = true
}

async function executeTool() {
  if (!selectedTool.value) return

  executing.value = true
  try {
    const result = await systemStore.executeTool(selectedTool.value.name, params.value)
    executeResult.value = result
    dialogVisible.value = false
    resultVisible.value = true
    ElMessage.success('工具执行成功')
  } catch (error) {
    ElMessage.error(`执行失败: ${error.message}`)
  } finally {
    executing.value = false
  }
}

async function refreshTools() {
  await systemStore.fetchTools()
  ElMessage.success('工具列表已刷新')
}

onMounted(() => {
  systemStore.fetchTools()
})
</script>

<style lang="scss" scoped>
.tools-header {
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

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.tool-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    border-color: #409eff;
  }
}

.tool-icon {
  width: 56px;
  height: 56px;
  background: #f5f7fa;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.tool-info {
  h4 {
    font-size: 16px;
    color: #1a1f36;
    margin-bottom: 8px;
  }

  p {
    font-size: 13px;
    color: #606266;
    line-height: 1.5;
  }
}

.tool-meta {
  margin-top: 12px;
}

.tool-params {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;

  .params-title {
    font-size: 12px;
    color: #909399;
    margin-bottom: 8px;
  }

  .param-item {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;

    code {
      background: #f5f7fa;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
      color: #409eff;
    }

    span {
      font-size: 12px;
      color: #606266;
    }
  }
}

.tool-description {
  margin-bottom: 20px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;

  p {
    font-size: 14px;
    color: #606266;
    line-height: 1.6;
  }
}

.params-form {
  .form-item {
    margin-bottom: 16px;

    label {
      display: block;
      font-size: 13px;
      color: #606266;
      margin-bottom: 8px;
    }
  }
}

.result-content {
  pre {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.6;
    max-height: 400px;
    overflow-y: auto;
  }
}
</style>
