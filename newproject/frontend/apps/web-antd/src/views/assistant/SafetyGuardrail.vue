<template>
  <div class="guardrail-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon">
            <SafetyOutlined />
          </div>
          <div class="header-text">
            <h1 class="page-title">安全护栏总览</h1>
            <p class="page-subtitle">五层安全防护体系运行状态与 RBAC 权限管理</p>
          </div>
        </div>
        <div class="header-actions">
          <a-button type="primary" :loading="loading" @click="refreshAll">
            <template #icon>
              <ReloadOutlined />
            </template>
            刷新数据
          </a-button>
        </div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <a-row :gutter="[24, 24]" class="stats-row">
      <a-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card stat-total">
          <div class="stat-icon-wrap">
            <Icon icon="lucide:scan" class="stat-lucide-icon" />
          </div>
          <div class="stat-info">
            <div class="stat-label">总检测次数</div>
            <div class="stat-number">{{ stats.total_checks.toLocaleString() }}</div>
          </div>
        </div>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card stat-blocked">
          <div class="stat-icon-wrap">
            <StopOutlined class="stat-ant-icon" />
          </div>
          <div class="stat-info">
            <div class="stat-label">已拦截</div>
            <div class="stat-number">{{ stats.blocked_count.toLocaleString() }}</div>
          </div>
        </div>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card stat-passed">
          <div class="stat-icon-wrap">
            <CheckCircleOutlined class="stat-ant-icon" />
          </div>
          <div class="stat-info">
            <div class="stat-label">已通过</div>
            <div class="stat-number">{{ stats.passed_count.toLocaleString() }}</div>
          </div>
        </div>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <div class="stat-card stat-rate">
          <div class="stat-icon-wrap">
            <WarningOutlined class="stat-ant-icon" />
          </div>
          <div class="stat-info">
            <div class="stat-label">拦截率</div>
            <div class="stat-number">{{ formatPercent(stats.block_rate * 100) }}%</div>
          </div>
        </div>
      </a-col>
    </a-row>

    <a-row :gutter="[24, 24]">
      <!-- 风险分布 -->
      <a-col :xs="24" :lg="14">
        <a-card class="info-card" :loading="loading">
          <template #title>
            <div class="card-title">
              <AlertOutlined />
              <span>风险等级分布</span>
            </div>
          </template>
          <div class="risk-distribution">
            <div
              v-for="item in riskItems"
              :key="item.key"
              class="risk-row"
            >
              <div class="risk-label">
                <a-tag :color="item.color" class="risk-tag">{{ item.label }}</a-tag>
              </div>
              <div class="risk-bar-wrap">
                <a-progress
                  :percent="roundPercent(item.percent)"
                  :stroke-color="item.hexColor"
                  :trail-color="'#f0f0f0'"
                  :show-text="false"
                  :size="14"
                />
              </div>
              <div class="risk-count">{{ item.count }}</div>
              <div class="risk-pct">{{ formatPercent(item.percent) }}%</div>
            </div>
          </div>
        </a-card>
      </a-col>

      <!-- 沙箱状态 -->
      <a-col :xs="24" :lg="10">
        <a-card class="info-card" :loading="loading">
          <template #title>
            <div class="card-title">
              <Icon icon="lucide:box" class="card-lucide" />
              <span>沙箱执行环境</span>
            </div>
          </template>
          <div class="sandbox-status">
            <div class="sandbox-main">
              <div class="sandbox-indicator" :class="sandbox.docker_available ? 'available' : 'unavailable'">
                <Icon :icon="sandbox.docker_available ? 'lucide:container' : 'lucide:container'" class="sandbox-icon" />
              </div>
              <div class="sandbox-detail">
                <div class="sandbox-title">
                  {{ sandbox.docker_available ? 'Docker 沙箱可用' : 'Docker 沙箱不可用' }}
                </div>
                <div class="sandbox-desc">
                  {{ sandbox.docker_available
                    ? '高危命令将在隔离容器中执行，确保宿主系统安全'
                    : '当前降级为受限子进程模式，命令白名单 + 超时控制' }}
                </div>
              </div>
            </div>
            <a-divider style="margin: 16px 0" />
            <a-descriptions :column="1" size="small" bordered>
              <a-descriptions-item label="Docker 可用">
                <a-tag :color="sandbox.docker_available ? 'green' : 'red'">
                  {{ sandbox.docker_available ? '是' : '否' }}
                </a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="沙箱模式">
                <a-tag color="blue">{{ sandbox.sandbox_mode || '未知' }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="沙箱启用">
                <a-tag :color="sandbox.enabled ? 'green' : 'orange'">
                  {{ sandbox.enabled ? '已启用' : '已禁用' }}
                </a-tag>
              </a-descriptions-item>
            </a-descriptions>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[24, 24]">
      <!-- RBAC 角色 -->
      <a-col :xs="24" :lg="14">
        <a-card class="info-card" :loading="loading">
          <template #title>
            <div class="card-title">
              <TeamOutlined />
              <span>RBAC 角色权限</span>
            </div>
          </template>
          <div class="roles-grid">
            <div
              v-for="role in rbac.roles"
              :key="role.name"
              class="role-card"
              :class="`role-${role.name}`"
            >
              <div class="role-header">
                <div class="role-avatar" :class="`avatar-${role.name}`">
                  <Icon :icon="getRoleIcon(role.name)" class="role-icon" />
                </div>
                <div class="role-meta">
                  <div class="role-name">{{ role.name }}</div>
                  <a-tag :color="getRoleTagColor(role.name)" size="small">
                    Level {{ role.level }}
                  </a-tag>
                </div>
              </div>
              <div class="role-desc">{{ role.description }}</div>
            </div>
          </div>
        </a-card>
      </a-col>

      <!-- 工具权限映射 -->
      <a-col :xs="24" :lg="10">
        <a-card class="info-card" :loading="loading">
          <template #title>
            <div class="card-title">
              <KeyOutlined />
              <span>工具权限要求</span>
            </div>
          </template>
          <a-table
            :columns="toolColumns"
            :data-source="toolTableData"
            :pagination="false"
            size="small"
            :scroll="{ y: 360 }"
            row-key="tool"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'role'">
                <a-tag :color="getRoleTagColor(record.role)" size="small">
                  {{ record.role }}
                </a-tag>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import { Icon } from '@iconify/vue';
import {
  ReloadOutlined,
  SafetyOutlined,
  StopOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  AlertOutlined,
  TeamOutlined,
  KeyOutlined,
} from '@ant-design/icons-vue';
import {
  getSafetyStats,
  getRbacRoles,
  getSandboxStatus,
} from '#/api/core/aiops/agent';

// ---- 类型 ----
interface SafetyStats {
  total_checks: number;
  blocked_count: number;
  passed_count: number;
  block_rate: number;
  risk_distribution: Record<string, number>;
}

interface RbacRole {
  name: string;
  level: number;
  description: string;
}

interface RbacData {
  roles: RbacRole[];
  tool_requirements: Record<string, string>;
}

interface SandboxData {
  docker_available: boolean;
  sandbox_mode: string;
  enabled: boolean;
}

// ---- 加载状态 ----
const loading = ref(false);

// ---- 响应式数据 ----
const stats = reactive<SafetyStats>({
  total_checks: 0,
  blocked_count: 0,
  passed_count: 0,
  block_rate: 0,
  risk_distribution: {},
});

const rbac = reactive<RbacData>({
  roles: [],
  tool_requirements: {},
});

const sandbox = reactive<SandboxData>({
  docker_available: false,
  sandbox_mode: 'unknown',
  enabled: false,
});

// ---- 风险等级配置 ----
const riskLevelConfig: Record<string, { label: string; color: string; hexColor: string }> = {
  safe: { label: '安全', color: 'success', hexColor: '#52c41a' },
  low: { label: '低风险', color: 'processing', hexColor: '#1890ff' },
  medium: { label: '中风险', color: 'warning', hexColor: '#faad14' },
  high: { label: '高风险', color: 'error', hexColor: '#ff4d4f' },
  critical: { label: '严重', color: 'error', hexColor: '#a8071a' },
};

// 风险分布列表（按等级排序）
const riskItems = computed(() => {
  const order = ['safe', 'low', 'medium', 'high', 'critical'];
  const total = Object.values(stats.risk_distribution).reduce((a, b) => a + b, 0) || 1;
  return order
    .filter((key) => key in stats.risk_distribution)
    .map((key) => {
      const count = stats.risk_distribution[key] ?? 0;
      const cfg = riskLevelConfig[key] ?? { label: key, color: 'default', hexColor: '#d9d9d9' };
      return {
        key,
        label: cfg.label,
        color: cfg.color,
        hexColor: cfg.hexColor,
        count,
        percent: (count / total) * 100,
      };
    });
});

// ---- 工具权限表 ----
const toolColumns = [
  { title: '工具名称', dataIndex: 'tool', width: 200 },
  { title: '最低角色', dataIndex: 'role', width: 120 },
];

const toolTableData = computed(() =>
  Object.entries(rbac.tool_requirements).map(([tool, role]) => ({ tool, role })),
);

// ---- 角色样式辅助 ----
function getRoleIcon(name: string): string {
  const map: Record<string, string> = {
    viewer: 'lucide:eye',
    operator: 'lucide:wrench',
    admin: 'lucide:shield-check',
  };
  return map[name] ?? 'lucide:user';
}

function getRoleTagColor(name: string): string {
  const map: Record<string, string> = {
    viewer: 'blue',
    operator: 'cyan',
    admin: 'red',
  };
  return map[name] ?? 'default';
}

// 统一百分比格式化：避免显示 33.33333333% 这类长小数
// - 整数：不显示小数（33%）
// - 非整数：保留 1 位小数（33.3%）
// - 0/100/极小值：固定 1 位小数（0.0%）
function formatPercent(value: number | undefined | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return '0.0';
  const rounded = Math.round(value * 10) / 10;
  // 整数场景（如 33）显示 33.0 → 统一显示一位小数保持视觉一致
  return rounded.toFixed(1);
}

// 用于 a-progress：将 percent 截断到 1 位小数
// 即使 show-text=false 也能避免部分版本进度条内部文本显示长小数
function roundPercent(value: number | undefined | null): number {
  if (value === undefined || value === null || Number.isNaN(value)) return 0;
  return Math.round(value * 10) / 10;
}

// ---- 数据加载 ----
async function fetchStats() {
  try {
    const data = await getSafetyStats();
    Object.assign(stats, data);
  } catch {
    // 静默失败，不影响其他数据加载
  }
}

async function fetchRbac() {
  try {
    const data = await getRbacRoles();
    rbac.roles = data.roles ?? [];
    rbac.tool_requirements = data.tool_requirements ?? {};
  } catch {
    // 静默失败
  }
}

async function fetchSandbox() {
  try {
    const data = await getSandboxStatus();
    Object.assign(sandbox, data);
  } catch {
    // 静默失败
  }
}

async function refreshAll() {
  loading.value = true;
  try {
    await Promise.allSettled([fetchStats(), fetchRbac(), fetchSandbox()]);
  } catch (err: any) {
    message.error(`数据加载失败: ${err.message ?? err}`);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  refreshAll();
});
</script>

<style scoped>
.guardrail-container {
  padding: 24px;
  background-color: #fafafa;
  min-height: 100vh;
}

/* ========== 页面头部 ========== */
.guardrail-container .page-header {
  background: #fff;
  border-radius: 12px;
  padding: 16px 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
}

.guardrail-container .header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.guardrail-container .header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.guardrail-container .header-icon {
  font-size: 32px;
  color: #722ed1;
}

.guardrail-container .header-text {
  display: flex;
  flex-direction: column;
}

.guardrail-container .page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #262626;
  line-height: 1.2;
}

.guardrail-container .page-subtitle {
  color: #8c8c8c;
  margin: 0;
  font-size: 12px;
  margin-top: 4px;
}

.guardrail-container .header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-shrink: 0;
}

/* 头部按钮美化 */
.guardrail-container .header-actions :deep(.ant-btn) {
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.2s ease;
}
.guardrail-container .header-actions :deep(.ant-btn:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
}

/* ========== 统计卡片 ========== */
.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.stat-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  flex-shrink: 0;
}

.stat-total .stat-icon-wrap {
  background: linear-gradient(135deg, #722ed1, #b37feb);
  color: #fff;
}

.stat-blocked .stat-icon-wrap {
  background: linear-gradient(135deg, #ff4d4f, #ff7875);
  color: #fff;
}

.stat-passed .stat-icon-wrap {
  background: linear-gradient(135deg, #52c41a, #95de64);
  color: #fff;
}

.stat-rate .stat-icon-wrap {
  background: linear-gradient(135deg, #faad14, #ffc53d);
  color: #fff;
}

.stat-lucide-icon {
  font-size: 26px;
}

.stat-ant-icon {
  font-size: 26px;
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 13px;
  color: #8c8c8c;
  margin-bottom: 4px;
  font-weight: 500;
}

.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: #262626;
  line-height: 1;
}

/* ========== 通用信息卡片 ========== */
.info-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
  transition: all 0.3s ease;
}

.info-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #262626;
}

.card-title .anticon,
.card-title .card-lucide {
  font-size: 18px;
  color: #722ed1;
}

/* ========== 风险分布 ========== */
.risk-distribution {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.risk-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.risk-label {
  width: 80px;
  flex-shrink: 0;
}

.risk-tag {
  font-weight: 600;
  width: 100%;
  text-align: center;
}

.risk-bar-wrap {
  flex: 1;
}

.risk-count {
  width: 56px;
  text-align: right;
  font-size: 16px;
  font-weight: 700;
  color: #262626;
}

.risk-pct {
  width: 56px;
  text-align: right;
  font-size: 13px;
  color: #8c8c8c;
}

/* ========== 沙箱状态 ========== */
.sandbox-status {
  padding: 4px 0;
}

.sandbox-main {
  display: flex;
  align-items: center;
  gap: 20px;
}

.sandbox-indicator {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sandbox-indicator.available {
  background: linear-gradient(135deg, #52c41a, #95de64);
  color: #fff;
}

.sandbox-indicator.unavailable {
  background: linear-gradient(135deg, #ff4d4f, #ff7875);
  color: #fff;
}

.sandbox-icon {
  font-size: 30px;
}

.sandbox-detail {
  flex: 1;
}

.sandbox-title {
  font-size: 16px;
  font-weight: 600;
  color: #262626;
  margin-bottom: 4px;
}

.sandbox-desc {
  font-size: 13px;
  color: #8c8c8c;
  line-height: 1.5;
}

/* ========== RBAC 角色 ========== */
.roles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.role-card {
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  padding: 20px;
  transition: all 0.3s ease;
}

.role-card:hover {
  border-color: #d9d9d9;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.role-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.role-avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.avatar-viewer {
  background: linear-gradient(135deg, #1890ff, #69c0ff);
  color: #fff;
}

.avatar-operator {
  background: linear-gradient(135deg, #13c2c2, #5cdbd3);
  color: #fff;
}

.avatar-admin {
  background: linear-gradient(135deg, #ff4d4f, #ff7875);
  color: #fff;
}

.role-icon {
  font-size: 20px;
}

.role-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.role-name {
  font-size: 15px;
  font-weight: 600;
  color: #262626;
  text-transform: capitalize;
}

.role-desc {
  font-size: 13px;
  color: #595959;
  line-height: 1.6;
}

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .guardrail-container {
    padding: 16px;
  }

  .guardrail-container .page-header {
    padding: 20px;
    margin-bottom: 16px;
  }

  .guardrail-container .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .guardrail-container .header-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .guardrail-container .page-title {
    font-size: 20px;
  }

  .guardrail-container .header-icon {
    font-size: 36px;
  }

  .stat-card {
    padding: 16px;
    gap: 14px;
  }

  .stat-icon-wrap {
    width: 44px;
    height: 44px;
  }

  .stat-number {
    font-size: 22px;
  }

  .risk-row {
    gap: 10px;
  }

  .risk-label {
    width: 64px;
  }

  .risk-count {
    width: 40px;
    font-size: 14px;
  }

  .risk-pct {
    width: 44px;
    font-size: 12px;
  }

  .roles-grid {
    grid-template-columns: 1fr;
  }
}
</style>
