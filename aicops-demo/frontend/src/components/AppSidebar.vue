<template>
  <div class="sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-logo">
      <el-icon :size="28" color="#409eff">
        <Cpu />
      </el-icon>
      <span v-show="!isCollapsed" class="logo-text">AICloudOps</span>
    </div>

    <el-menu
      :default-active="currentRoute"
      :collapse="isCollapsed"
      router
      class="sidebar-menu"
    >
      <el-menu-item
        v-for="item in menuItems"
        :key="item.path"
        :index="item.path"
      >
        <el-icon>
          <component :is="item.icon" />
        </el-icon>
        <template #title>{{ item.title }}</template>
      </el-menu-item>
    </el-menu>

    <div class="sidebar-footer">
      <el-button
        :icon="isCollapsed ? 'Expand' : 'Fold'"
        text
        @click="isCollapsed = !isCollapsed"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  ChatDotRound,
  Monitor,
  SetUp,
  Lock,
  List,
  Clock,
  Cpu,
} from '@element-plus/icons-vue'

const route = useRoute()
const isCollapsed = ref(false)

const currentRoute = computed(() => route.path)

const menuItems = [
  { path: '/chat', title: '智能对话', icon: 'ChatDotRound' },
  { path: '/dashboard', title: '系统监控', icon: 'Monitor' },
  { path: '/tools', title: '运维工具', icon: 'SetUp' },
  { path: '/safety', title: '安全护栏', icon: 'Lock' },
  { path: '/traces', title: '推理溯源', icon: 'List' },
  { path: '/history', title: '对话历史', icon: 'Clock' },
]
</script>

<style lang="scss" scoped>
.sidebar {
  width: 220px;
  height: 100vh;
  background: linear-gradient(180deg, #1a1f36 0%, #0d1225 100%);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;

  &.collapsed {
    width: 64px;
  }
}

.sidebar-logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
  background: linear-gradient(135deg, #409eff, #67c23a);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  background: transparent;
  padding: 12px 8px;

  :deep(.el-menu-item) {
    height: 48px;
    line-height: 48px;
    margin-bottom: 4px;
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.65);

    &:hover {
      background: rgba(64, 158, 255, 0.15);
      color: #fff;
    }

    &.is-active {
      background: linear-gradient(135deg, rgba(64, 158, 255, 0.3), rgba(103, 194, 58, 0.2));
      color: #fff;
      font-weight: 500;
    }

    .el-icon {
      font-size: 18px;
    }
  }

  :deep(.el-menu--collapse) {
    .el-menu-item {
      padding: 0 20px;
    }
  }
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  justify-content: center;

  .el-button {
    color: rgba(255, 255, 255, 0.65);

    &:hover {
      color: #fff;
    }
  }
}
</style>
