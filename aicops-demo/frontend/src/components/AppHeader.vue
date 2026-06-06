<template>
  <div class="app-header">
    <div class="header-left">
      <h2 class="page-title">{{ currentTitle }}</h2>
    </div>

    <div class="header-right">
      <el-tooltip content="刷新系统状态" placement="bottom">
        <el-button :icon="Refresh" circle @click="refreshStatus" :loading="loading" />
      </el-tooltip>

      <el-badge :value="alerts" :hidden="alerts === 0" class="alert-badge">
        <el-button :icon="Bell" circle />
      </el-badge>

      <el-dropdown trigger="click">
        <div class="user-info">
          <el-avatar :size="32" class="user-avatar">
            <el-icon><User /></el-icon>
          </el-avatar>
          <span class="user-name">运维管理员</span>
          <el-icon><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item :icon="Setting">系统设置</el-dropdown-item>
            <el-dropdown-item :icon="InfoFilled" divided>关于系统</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSystemStore } from '@/stores/system'
import {
  Refresh,
  Bell,
  User,
  ArrowDown,
  Setting,
  InfoFilled,
} from '@element-plus/icons-vue'

const route = useRoute()
const systemStore = useSystemStore()
const alerts = ref(0)

const loading = computed(() => systemStore.loading)

const currentTitle = computed(() => {
  const titles = {
    '/chat': '智能对话',
    '/dashboard': '系统监控',
    '/tools': '运维工具',
    '/safety': '安全护栏',
    '/traces': '推理溯源',
    '/history': '对话历史',
  }
  return titles[route.path] || 'AICloudOps'
})

async function refreshStatus() {
  await systemStore.fetchSystemStatus()
}
</script>

<style lang="scss" scoped>
.app-header {
  height: 64px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1f36;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.alert-badge {
  :deep(.el-badge__content) {
    font-size: 10px;
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background 0.2s;

  &:hover {
    background: #f5f7fa;
  }
}

.user-avatar {
  background: linear-gradient(135deg, #409eff, #67c23a);
}

.user-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}
</style>
