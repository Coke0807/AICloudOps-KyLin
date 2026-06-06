<template>
  <el-config-provider :locale="zhCn">
    <div class="app-layout">
      <AppSidebar />
      <div class="app-main">
        <AppHeader />
        <div class="app-content">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </div>
    </div>
  </el-config-provider>
</template>

<script setup>
import { onMounted } from 'vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import AppSidebar from '@/components/AppSidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()

onMounted(() => {
  systemStore.fetchSystemStatus()
})
</script>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f0f2f5;
}

.app-content {
  flex: 1;
  overflow: hidden;
}
</style>
