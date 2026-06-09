<script lang="ts" setup>
import { computed } from 'vue';

import { preferences } from '@vben/preferences';

const appName = computed(() => preferences.app.name);
const logo = computed(() => preferences.logo.source);

const features = [
  {
    icon: 'shield',
    title: '五层安全防护体系',
    desc: '输入清洗 · 意图分类 · 风险评分 · 参数校验 · 注入检测',
  },
  {
    icon: 'tools',
    title: '20+ MCP 运维工具',
    desc: '进程/磁盘/网络/日志/服务全方位覆盖',
  },
  {
    icon: 'audit',
    title: '全链路审计追溯',
    desc: 'RBAC 角色控制 · 沙箱隔离 · 配置回滚',
  },
];

const archLayers = [
  { label: '用户浏览器', sub: 'Browser' },
  { label: 'API Server', sub: 'FastAPI + Uvicorn' },
  { label: 'Agent 推理引擎', sub: 'ReAct · Plan-Execute' },
  { label: '麒麟 V11 + LoongArch', sub: 'Kylin OS · 龙芯 3A5000' },
];
</script>

<template>
  <div class="auth-layout">
    <!-- 左侧品牌面板（桌面端可见） -->
    <aside class="brand-panel">
      <div class="brand-content">
        <!-- Logo & 标题 -->
        <div class="brand-header">
          <div class="logo-icon">
            <img v-if="logo" :alt="appName" :src="logo" class="logo-img" />
            <span v-else class="logo-text">AI</span>
          </div>
          <h1 class="brand-title">{{ appName || 'AICloudOps' }}</h1>
          <p class="brand-subtitle">安全智能运维 Agent 平台</p>
        </div>

        <!-- B/S 架构图 -->
        <div class="arch-diagram">
          <h3 class="arch-heading">系统架构</h3>
          <div class="arch-layers">
            <div
              v-for="(layer, idx) in archLayers"
              :key="idx"
              class="arch-layer"
            >
              <div class="arch-node">
                <span class="arch-badge">{{ idx + 1 }}</span>
                <div class="arch-text">
                  <span class="arch-label">{{ layer.label }}</span>
                  <span class="arch-sub">{{ layer.sub }}</span>
                </div>
              </div>
              <div v-if="idx < archLayers.length - 1" class="arch-connector">
                <svg width="16" height="20" viewBox="0 0 16 20" fill="none">
                  <path
                    d="M8 0v14M8 14l4-4M8 14l-4-4"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </div>
            </div>
          </div>
        </div>

        <!-- 核心卖点 -->
        <div class="features">
          <div
            v-for="(feat, idx) in features"
            :key="idx"
            class="feature-item"
          >
            <span class="feature-dot" />
            <div class="feature-text">
              <span class="feature-title">{{ feat.title }}</span>
              <span class="feature-desc">{{ feat.desc }}</span>
            </div>
          </div>
        </div>

        <!-- 底部标语 -->
        <p class="brand-footer">面向麒麟操作系统的安全智能运维 Agent</p>
      </div>

      <!-- 装饰性光晕 -->
      <div class="glow glow-1" />
      <div class="glow glow-2" />
    </aside>

    <!-- 右侧登录表单区域 -->
    <main class="auth-main">
      <!-- 头部 Logo（移动端可见） -->
      <div class="mobile-header">
        <img v-if="logo" :alt="appName" :src="logo" class="mobile-logo" />
        <span class="mobile-title">{{ appName || 'AICloudOps' }}</span>
      </div>

      <div class="auth-form-wrapper">
        <Transition appear mode="out-in" name="slide-right">
          <RouterView v-slot="{ Component, route }">
            <KeepAlive :include="['Login']">
              <component
                :is="Component"
                :key="route.fullPath"
                class="auth-form-content"
              />
            </KeepAlive>
          </RouterView>
        </Transition>
      </div>
    </main>
  </div>
</template>

<style scoped>
.auth-layout {
  display: flex;
  min-height: 100vh;
  width: 100%;
}

/* ───────────────────────────────────────────────
   左侧品牌面板
   ─────────────────────────────────────────────── */
.brand-panel {
  display: none;
}

/* 装饰性光晕 */
.glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}

.glow-1 {
  top: -20%;
  right: -15%;
  width: 450px;
  height: 450px;
  background: radial-gradient(
    circle,
    rgba(99, 102, 241, 0.18) 0%,
    transparent 70%
  );
}

.glow-2 {
  bottom: -15%;
  left: -10%;
  width: 350px;
  height: 350px;
  background: radial-gradient(
    circle,
    rgba(139, 92, 246, 0.12) 0%,
    transparent 70%
  );
}

.brand-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 32px;
  max-width: 380px;
  width: 100%;
}

/* ── Logo & 标题 ── */
.brand-header {
  text-align: center;
}

.logo-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 13px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  margin-bottom: 14px;
  box-shadow: 0 4px 24px rgba(99, 102, 241, 0.35);
  overflow: hidden;
}

.logo-img {
  width: 36px;
  height: 36px;
  object-fit: contain;
}

.logo-text {
  font-size: 18px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -1px;
}

.brand-title {
  font-size: 26px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 4px;
  letter-spacing: 0.5px;
}

.brand-subtitle {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
}

/* ── 架构图 ── */
.arch-diagram {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 18px 20px;
  backdrop-filter: blur(4px);
}

.arch-heading {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 3px;
  margin: 0 0 14px;
  text-align: center;
}

.arch-layers {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.arch-layer {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.arch-node {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 6px;
  transition: background 0.2s;
}

.arch-node:hover {
  background: rgba(255, 255, 255, 0.09);
}

.arch-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: rgba(99, 102, 241, 0.2);
  color: #a5b4fc;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.arch-text {
  display: flex;
  flex-direction: column;
}

.arch-label {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  line-height: 1.3;
}

.arch-sub {
  font-size: 11px;
  color: #64748b;
  line-height: 1.3;
}

.arch-connector {
  color: #6366f1;
  opacity: 0.5;
  padding: 1px 0;
}

/* ── 核心卖点 ── */
.features {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  transition: background 0.2s;
}

.feature-item:hover {
  background: rgba(255, 255, 255, 0.07);
}

.feature-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  flex-shrink: 0;
  margin-top: 5px;
}

.feature-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.feature-title {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
}

.feature-desc {
  font-size: 11px;
  color: #64748b;
  line-height: 1.5;
}

/* ── 底部标语 ── */
.brand-footer {
  text-align: center;
  font-size: 12px;
  color: #475569;
  margin: 0;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

/* ───────────────────────────────────────────────
   右侧表单区域
   ─────────────────────────────────────────────── */
.auth-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
  position: relative;
  background: hsl(var(--background));
  padding: 24px;
}

/* 移动端头部 Logo */
.mobile-header {
  display: flex;
  align-items: center;
  gap: 8px;
  position: absolute;
  top: 16px;
  left: 16px;
}

@media (min-width: 1024px) {
  .mobile-header {
    display: none;
  }
}

.mobile-logo {
  width: 32px;
  height: 32px;
  object-fit: contain;
}

.mobile-title {
  font-size: 16px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.auth-form-wrapper {
  width: 100%;
  max-width: 400px;
}

.auth-form-content {
  width: 100%;
}

/* ── 复用 Vben 原有的过渡动画 ── */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.25s ease-out;
}

.slide-right-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.slide-right-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* ── 暗色模式下表单区域背景微调 ── */
.dark .auth-main {
  background: hsl(var(--background-deep));
}
</style>
