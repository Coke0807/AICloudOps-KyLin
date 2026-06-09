<template>
  <div class="arch-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon">
            <Icon icon="lucide:layout-dashboard" size="48" color="#722ed1" />
          </div>
          <div class="header-text">
            <h1 class="page-title">系统架构</h1>
            <p class="page-subtitle">基于MCP协议的安全智能运维架构</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 架构图主体 -->
    <div class="arch-body">

      <!-- ======================== Layer 1: 大模型推理层 ======================== -->
      <div class="layer layer-llm">
        <div class="layer-header">
          <div class="layer-header-left">
            <Icon icon="lucide:brain" size="24" color="#722ed1" />
            <span class="layer-title">大模型推理层</span>
            <span class="layer-en">LLM Inference Layer</span>
          </div>
          <a-tag color="purple" class="layer-tag">核心引擎</a-tag>
        </div>
        <div class="layer-body">
          <a-row :gutter="20">
            <a-col :xs="24" :sm="12">
              <div class="llm-card model-card">
                <div class="llm-card-icon">
                  <Icon icon="lucide:cpu" size="32" color="#722ed1" />
                </div>
                <div class="llm-card-info">
                  <div class="llm-card-title">模型引擎</div>
                  <div class="llm-card-desc">
                    <a-tag color="purple">DeepSeek</a-tag>
                    <a-tag color="blue">Qwen</a-tag>
                  </div>
                  <div class="llm-card-sub">支持多种大语言模型切换，适配不同推理场景</div>
                </div>
              </div>
            </a-col>
            <a-col :xs="24" :sm="12">
              <div class="llm-card react-card">
                <div class="llm-card-icon">
                  <Icon icon="lucide:repeat-2" size="32" color="#722ed1" />
                </div>
                <div class="llm-card-info">
                  <div class="llm-card-title">ReAct 推理循环</div>
                  <div class="react-pipeline">
                    <span class="react-step">推理</span>
                    <span class="react-arrow">&rarr;</span>
                    <span class="react-step">行动</span>
                    <span class="react-arrow">&rarr;</span>
                    <span class="react-step">观察</span>
                    <span class="react-arrow">&rarr;</span>
                    <span class="react-step active">继续</span>
                  </div>
                  <div class="llm-card-sub">Reasoning-Acting 循环驱动多步决策</div>
                </div>
              </div>
            </a-col>
          </a-row>
        </div>
      </div>

      <!-- 流向箭头 -->
      <div class="flow-arrow">
        <div class="arrow-line"></div>
        <div class="arrow-head">&darr;</div>
        <span class="arrow-label">指令分发 / 工具调用请求</span>
      </div>

      <!-- ======================== Layer 2: MCP 插件层 ======================== -->
      <div class="layer layer-mcp">
        <div class="layer-header">
          <div class="layer-header-left">
            <Icon icon="lucide:puzzle" size="24" color="#1890ff" />
            <span class="layer-title">MCP 插件层</span>
            <span class="layer-en">MCP Plugin Layer</span>
          </div>
          <div class="layer-header-right">
            <a-tag color="blue" class="layer-tag">20 个工具</a-tag>
            <a-tag color="cyan" class="layer-tag">6 大类别</a-tag>
          </div>
        </div>
        <div class="layer-body">
          <a-row :gutter="[16, 16]">
            <a-col
              v-for="category in toolCategories"
              :key="category.name"
              :xs="24" :sm="12" :lg="8"
            >
              <div class="mcp-category" :style="{ borderColor: category.color }">
                <div class="mcp-category-header" :style="{ background: category.bg }">
                  <Icon :icon="category.icon" size="20" :color="category.color" />
                  <span class="mcp-category-title" :style="{ color: category.color }">{{ category.name }}</span>
                  <a-tag :color="category.tagColor" size="small">{{ category.tools.length }} 个</a-tag>
                </div>
                <div class="mcp-tools-list">
                  <div
                    v-for="tool in category.tools"
                    :key="tool"
                    class="mcp-tool-item"
                  >
                    <Icon icon="lucide:terminal" size="12" :color="category.color" />
                    <code class="tool-code">{{ tool }}</code>
                  </div>
                </div>
              </div>
            </a-col>
          </a-row>
        </div>
      </div>

      <!-- 流向箭头 -->
      <div class="flow-arrow">
        <div class="arrow-line"></div>
        <div class="arrow-head">&darr;</div>
        <span class="arrow-label">执行结果 / 安全校验请求</span>
      </div>

      <!-- ======================== Layer 3: 安全护栏核心 ======================== -->
      <div class="layer layer-safety">
        <div class="layer-header">
          <div class="layer-header-left">
            <Icon icon="lucide:shield" size="24" color="#fa541c" />
            <span class="layer-title">安全护栏核心</span>
            <span class="layer-en">Safety Guardrail Core</span>
          </div>
          <a-tag color="red" class="layer-tag">五层防御</a-tag>
        </div>
        <div class="layer-body">
          <!-- 五层防御流水线 -->
          <div class="safety-pipeline">
            <div
              v-for="(stage, idx) in safetyStages"
              :key="stage.name"
              class="pipeline-stage"
            >
              <div class="stage-connector" v-if="idx > 0">
                <div class="connector-line"></div>
              </div>
              <div class="stage-card" :style="{ borderColor: stage.color }">
                <div class="stage-icon-wrap" :style="{ background: stage.bg }">
                  <Icon :icon="stage.icon" size="28" :color="stage.color" />
                </div>
                <div class="stage-name">{{ stage.name }}</div>
                <div class="stage-class">{{ stage.className }}</div>
                <div class="stage-order">第{{ idx + 1 }}层</div>
              </div>
            </div>
          </div>

          <!-- 底层安全能力 -->
          <div class="safety-capabilities">
            <a-row :gutter="16">
              <a-col :xs="24" :sm="8" v-for="cap in safetyCapabilities" :key="cap.name">
                <div class="capability-card">
                  <Icon :icon="cap.icon" size="22" :color="cap.color" />
                  <div class="capability-info">
                    <div class="capability-name">{{ cap.name }}</div>
                    <div class="capability-desc">{{ cap.desc }}</div>
                  </div>
                </div>
              </a-col>
            </a-row>
          </div>
        </div>
      </div>

      <!-- 图例 -->
      <div class="arch-legend">
        <div class="legend-title">
          <Icon icon="lucide:info" size="16" color="#8c8c8c" />
          <span>架构模式说明</span>
        </div>
        <div class="legend-items">
          <div class="legend-item">
            <span class="legend-dot" style="background: #722ed1;"></span>
            <span class="legend-text"><strong>大模型推理层</strong> — 负责自然语言理解、任务规划与多步推理，基于 ReAct 循环驱动工具调用决策</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot" style="background: #1890ff;"></span>
            <span class="legend-text"><strong>MCP 插件层</strong> — 通过 Model Context Protocol 暴露 20 个标准化运维工具，覆盖系统监控、磁盘管理、网络诊断、日志分析、服务管理、安全运维六大域</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot" style="background: #fa541c;"></span>
            <span class="legend-text"><strong>安全护栏核心</strong> — 纵深防御体系：五层串行校验 + RBAC 角色权限 + 沙箱隔离执行 + 全链路审计追踪，确保每一次工具调用均可控、可审计、可回滚</span>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Icon } from '@iconify/vue';

// ── MCP 工具分类数据 ──
const toolCategories = ref([
  {
    name: '系统监控类',
    icon: 'lucide:monitor',
    color: '#1890ff',
    bg: '#e6f7ff',
    tagColor: 'blue',
    tools: [
      'get_system_status',
      'get_process_list',
      'get_process_detail',
      'get_memory_usage',
      'get_memory_top_consumers',
      'get_system_uptime',
    ],
  },
  {
    name: '磁盘与文件类',
    icon: 'lucide:hard-drive',
    color: '#52c41a',
    bg: '#f6ffed',
    tagColor: 'green',
    tools: [
      'get_disk_usage',
      'get_large_files',
      'get_open_files',
    ],
  },
  {
    name: '网络与端口类',
    icon: 'lucide:network',
    color: '#13c2c2',
    bg: '#e6fffb',
    tagColor: 'cyan',
    tools: [
      'get_network_connections',
      'check_port_usage',
    ],
  },
  {
    name: '日志分析类',
    icon: 'lucide:file-text',
    color: '#faad14',
    bg: '#fffbe6',
    tagColor: 'gold',
    tools: [
      'query_journal',
      'search_log_file',
    ],
  },
  {
    name: '服务管理类',
    icon: 'lucide:settings',
    color: '#722ed1',
    bg: '#f9f0ff',
    tagColor: 'purple',
    tools: [
      'get_service_status',
      'list_failed_services',
    ],
  },
  {
    name: '安全运维类',
    icon: 'lucide:shield-check',
    color: '#f5222d',
    bg: '#fff1f0',
    tagColor: 'red',
    tools: [
      'check_failed_logins',
      'kill_process',
      'run_safe_command',
      'backup_config',
      'rollback_operation',
    ],
  },
]);

// ── 安全五层防御数据 ──
const safetyStages = ref([
  { name: '输入清洗', className: 'InputSanitizer', icon: 'lucide:sparkles', color: '#fa8c16', bg: '#fff7e6' },
  { name: '意图分类', className: 'IntentClassifier', icon: 'lucide:target', color: '#1890ff', bg: '#e6f7ff' },
  { name: '风险评分', className: 'RiskScorer', icon: 'lucide:bar-chart-3', color: '#fa541c', bg: '#fff2e8' },
  { name: '参数校验', className: 'ParameterValidator', icon: 'lucide:check-circle', color: '#52c41a', bg: '#f6ffed' },
  { name: '注入检测', className: 'InjectionDetector', icon: 'lucide:shield-alert', color: '#f5222d', bg: '#fff1f0' },
]);

// ── 底层安全能力 ──
const safetyCapabilities = ref([
  { name: 'RBAC 三级权限', desc: 'viewer / operator / admin 细粒度角色控制', icon: 'lucide:users', color: '#722ed1' },
  { name: '沙箱隔离执行', desc: 'Docker 隔离或受限子进程，高危命令受限运行', icon: 'lucide:box', color: '#fa541c' },
  { name: '推理链路审计', desc: '全链路追踪，每次操作可审计、可回溯、可回滚', icon: 'lucide:git-branch', color: '#1890ff' },
]);
</script>

<style scoped>
.arch-container {
  padding: 24px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

/* ── 页面头部 ── */
.page-header {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-text {
  display: flex;
  flex-direction: column;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #262626;
  line-height: 1.2;
}

.page-subtitle {
  color: #8c8c8c;
  margin: 0;
  font-size: 14px;
  margin-top: 4px;
}

/* ── 架构主体 ── */
.arch-body {
  max-width: 1200px;
  margin: 0 auto;
}

/* ── 通用层样式 ── */
.layer {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
}

.layer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
}

.layer-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.layer-header-right {
  display: flex;
  gap: 8px;
}

.layer-title {
  font-size: 18px;
  font-weight: 600;
  color: #262626;
}

.layer-en {
  font-size: 13px;
  color: #8c8c8c;
  font-weight: 400;
}

.layer-tag {
  font-weight: 500;
}

.layer-body {
  padding: 24px;
}

/* ── Layer 1: LLM 层 ── */
.layer-llm {
  border-top: 4px solid #722ed1;
}

.llm-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  border-radius: 10px;
  border: 1px solid #f0f0f0;
  background: #fafafa;
  transition: box-shadow 0.3s ease;
}

.llm-card:hover {
  box-shadow: 0 4px 16px rgba(114, 46, 209, 0.12);
}

.llm-card-icon {
  flex-shrink: 0;
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f9f0ff 0%, #efdbff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: subtle-pulse 3s ease-in-out infinite;
}

.llm-card-info {
  flex: 1;
  min-width: 0;
}

.llm-card-title {
  font-size: 16px;
  font-weight: 600;
  color: #262626;
  margin-bottom: 8px;
}

.llm-card-desc {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.llm-card-sub {
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.6;
}

/* ReAct 流水线 */
.react-pipeline {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.react-step {
  display: inline-flex;
  align-items: center;
  padding: 4px 14px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  background: #f0f0f0;
  color: #595959;
}

.react-step.active {
  background: linear-gradient(135deg, #722ed1 0%, #9254de 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(114, 46, 209, 0.3);
  animation: step-glow 2s ease-in-out infinite;
}

.react-arrow {
  color: #bfbfbf;
  font-size: 16px;
  font-weight: 600;
}

/* ── 流向箭头 ── */
.flow-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  position: relative;
}

.arrow-line {
  width: 3px;
  height: 32px;
  background: linear-gradient(to bottom, #d9d9d9, #bfbfbf);
  border-radius: 2px;
}

.arrow-head {
  font-size: 28px;
  color: #8c8c8c;
  line-height: 1;
  animation: arrow-bounce 1.5s ease-in-out infinite;
}

.arrow-label {
  font-size: 12px;
  color: #bfbfbf;
  margin-top: 4px;
}

/* ── Layer 2: MCP 层 ── */
.layer-mcp {
  border-top: 4px solid #1890ff;
  background: #fafcff;
}

.mcp-category {
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
  transition: box-shadow 0.3s ease;
  height: 100%;
}

.mcp-category:hover {
  box-shadow: 0 4px 16px rgba(24, 144, 255, 0.12);
}

.mcp-category-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.mcp-category-title {
  font-size: 14px;
  font-weight: 600;
  flex: 1;
}

.mcp-tools-list {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mcp-tool-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  background: #fafafa;
  transition: background 0.2s;
}

.mcp-tool-item:hover {
  background: #f0f5ff;
}

.tool-code {
  font-size: 12px;
  color: #595959;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  background: none;
  padding: 0;
}

/* ── Layer 3: 安全护栏层 ── */
.layer-safety {
  border-top: 4px solid #fa541c;
  background: #fffbf7;
}

.safety-pipeline {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  padding: 12px 0 24px;
  flex-wrap: wrap;
}

.pipeline-stage {
  display: flex;
  align-items: center;
}

.stage-connector {
  width: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.connector-line {
  width: 100%;
  height: 2px;
  background: linear-gradient(to right, #faad14, #fa8c16);
  position: relative;
}

.connector-line::after {
  content: '';
  position: absolute;
  right: -3px;
  top: -3px;
  width: 0;
  height: 0;
  border-left: 6px solid #fa8c16;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
}

.stage-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 16px 16px;
  border-radius: 10px;
  border: 1px solid #e8e8e8;
  background: #fff;
  min-width: 120px;
  text-align: center;
  transition: box-shadow 0.3s ease, transform 0.3s ease;
}

.stage-card:hover {
  box-shadow: 0 4px 20px rgba(250, 84, 28, 0.15);
  transform: translateY(-2px);
}

.stage-icon-wrap {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: subtle-pulse 3s ease-in-out infinite;
}

.stage-name {
  font-size: 14px;
  font-weight: 600;
  color: #262626;
}

.stage-class {
  font-size: 11px;
  color: #8c8c8c;
  font-family: 'SFMono-Regular', Consolas, monospace;
}

.stage-order {
  font-size: 11px;
  color: #fa541c;
  font-weight: 500;
  padding: 2px 8px;
  background: #fff2e8;
  border-radius: 10px;
}

/* 底层安全能力 */
.safety-capabilities {
  margin-top: 16px;
  padding-top: 20px;
  border-top: 1px dashed #ffd8bf;
}

.capability-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #f0f0f0;
  transition: box-shadow 0.3s ease;
}

.capability-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.capability-name {
  font-size: 14px;
  font-weight: 600;
  color: #262626;
  margin-bottom: 2px;
}

.capability-desc {
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.5;
}

/* ── 图例 ── */
.arch-legend {
  margin-top: 24px;
  padding: 20px 24px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #f0f0f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.legend-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #595959;
  margin-bottom: 16px;
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.legend-dot {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-top: 4px;
}

.legend-text {
  font-size: 13px;
  color: #595959;
  line-height: 1.6;
}

.legend-text strong {
  color: #262626;
}

/* ── 动画 ── */
@keyframes subtle-pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.85;
  }
}

@keyframes step-glow {
  0%, 100% {
    box-shadow: 0 2px 8px rgba(114, 46, 209, 0.3);
  }
  50% {
    box-shadow: 0 4px 16px rgba(114, 46, 209, 0.5);
  }
}

@keyframes arrow-bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(6px);
  }
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .arch-container {
    padding: 12px;
  }

  .layer-header {
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
  }

  .layer-body {
    padding: 16px;
  }

  .safety-pipeline {
    flex-direction: column;
    gap: 8px;
  }

  .stage-connector {
    width: 2px;
    height: 24px;
  }

  .connector-line {
    width: 2px;
    height: 100%;
    background: linear-gradient(to bottom, #faad14, #fa8c16);
  }

  .connector-line::after {
    display: none;
  }

  .stage-card {
    min-width: 100%;
    flex-direction: row;
    text-align: left;
    gap: 12px;
  }

  .stage-icon-wrap {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
  }

  .stage-order {
    margin-left: auto;
  }
}
</style>
