<template>
  <div class="dashboard-container">
    <!-- 顶部信息栏 -->
    <div class="dashboard-header">
      <div class="header-left">
        <h1 class="platform-title">AI-CloudOps 智能运维平台</h1>
        <span class="platform-desc">实时监控 · 智能预测 · 自动化运维</span>
      </div>
      <div class="header-right">
        <a-space size="large">
          <span class="status-indicator" :class="systemStatusClass">
            <span class="status-dot" :class="systemStatusClass"></span>
            {{ systemStatusText }}
          </span>
          <span class="time-display">{{ currentTime }}</span>
        </a-space>
      </div>
    </div>

    <!-- 核心指标卡片 -->
    <a-row :gutter="[16, 16]" class="metrics-section">
      <a-col :xs="24" :sm="12" :md="6" v-for="metric in metrics" :key="metric.key">
        <div class="metric-card">
          <div class="metric-main">
            <div class="metric-icon-wrapper" :style="{ background: metric.iconBg }">
              <Icon :icon="metric.icon" size="22" :color="metric.iconColor" />
            </div>
            <div class="metric-info">
              <span class="metric-label">{{ metric.label }}</span>
              <div class="metric-value-row">
                <span class="metric-value">{{ metric.value }}</span>
                <span class="metric-unit">{{ metric.unit }}</span>
              </div>
            </div>
          </div>
          <div class="metric-footer">
            <div class="metric-trend" :class="`trend-${metric.trend}`">
              <Icon
                :icon="metric.trend === 'up' ? 'lucide:trending-up' : metric.trend === 'down' ? 'lucide:trending-down' : 'lucide:minus'"
                size="14" />
              <span>{{ metric.change }}</span>
            </div>
            <span class="metric-update-time">{{ metric.lastUpdate }}</span>
          </div>
          <div class="metric-chart" :ref="(el) => { if (el) chartRefs[metric.key] = el as HTMLElement }"></div>
        </div>
      </a-col>
    </a-row>

    <!-- 系统概览区 -->
    <a-row :gutter="[16, 16]" class="overview-section">
      <a-col :xs="24" :lg="12">
        <div class="system-info-card">
          <div class="card-header">
            <div class="card-title-wrapper">
              <Icon icon="lucide:monitor" size="20" color="#1890ff" />
              <h3 class="card-title">系统概览</h3>
            </div>
            <a-tag color="blue">银河麒麟 V11</a-tag>
          </div>
          <div class="system-info-grid">
            <div class="info-item" v-for="(item, idx) in systemInfoList" :key="idx">
              <span class="info-label">{{ item.label }}</span>
              <span class="info-value" :class="item.className" :title="String(item.value)">{{ item.value }}</span>
            </div>
          </div>
          <!-- 系统负载指标（与后端 demo_engine 一致） -->
          <div class="system-load-bar">
            <Icon icon="lucide:gauge" size="14" color="#722ed1" />
            <span class="load-label">系统负载</span>
            <span class="load-values">
              <span class="load-val" :class="{ 'load-high': MOCK_SYSTEM_LOAD.load1 > MOCK_SYSTEM_LOAD.cpuCount }">{{ MOCK_SYSTEM_LOAD.load1 }}</span>
              <span class="load-sep">/</span>
              <span class="load-val">{{ MOCK_SYSTEM_LOAD.load5 }}</span>
              <span class="load-sep">/</span>
              <span class="load-val">{{ MOCK_SYSTEM_LOAD.load15 }}</span>
            </span>
            <span class="load-hint">(1min / 5min / 15min)</span>
          </div>
        </div>
      </a-col>

      <a-col :xs="24" :lg="12">
        <div class="network-card">
          <div class="card-header">
            <div class="card-title-wrapper">
              <Icon icon="lucide:network" size="20" color="#52c41a" />
              <h3 class="card-title">网络流量监控</h3>
            </div>
            <a-badge status="processing" text="实时" />
          </div>
          <div class="network-stats">
            <div class="network-stat-item">
              <div class="network-stat-label">
                <Icon icon="lucide:arrow-down" size="14" color="#52c41a" />
                入站流量
              </div>
              <div class="network-stat-value">{{ networkStats.in }}</div>
              <div class="network-stat-unit">MB/s</div>
            </div>
            <div class="network-divider"></div>
            <div class="network-stat-item">
              <div class="network-stat-label">
                <Icon icon="lucide:arrow-up" size="14" color="#1890ff" />
                出站流量
              </div>
              <div class="network-stat-value">{{ networkStats.out }}</div>
              <div class="network-stat-unit">MB/s</div>
            </div>
            <div class="network-divider"></div>
            <div class="network-stat-item">
              <div class="network-stat-label">
                <Icon icon="lucide:activity" size="14" color="#faad14" />
                总带宽
              </div>
              <div class="network-stat-value">{{ networkStats.total }}</div>
              <div class="network-stat-unit">MB/s</div>
            </div>
          </div>
          <div ref="networkChart" class="chart-container-small"></div>
        </div>
      </a-col>
    </a-row>

    <!-- 主要内容区 -->
    <a-row :gutter="[16, 16]" class="content-section">
      <!-- 性能趋势图表 -->
      <a-col :xs="24" :lg="16">
        <div class="chart-card">
          <div class="card-header">
            <div class="card-title-wrapper">
              <Icon icon="lucide:line-chart" size="20" color="#722ed1" />
              <h3 class="card-title">性能趋势分析</h3>
            </div>
            <a-radio-group v-model:value="chartPeriod" size="small" @change="updateTrendChart">
              <a-radio-button value="1h">1小时</a-radio-button>
              <a-radio-button value="24h">24小时</a-radio-button>
              <a-radio-button value="7d">7天</a-radio-button>
            </a-radio-group>
          </div>
          <div class="trend-stats">
            <div class="trend-stat" v-for="(stat, idx) in trendStats" :key="idx">
              <span class="trend-stat-label">{{ stat.label }}</span>
              <span class="trend-stat-value" :style="{ color: stat.color }">{{ stat.value }}</span>
            </div>
          </div>
          <div ref="trendChart" class="chart-container"></div>
        </div>
      </a-col>

      <!-- 实时事件流 -->
      <a-col :xs="24" :lg="8">
        <div class="event-card">
          <div class="card-header">
            <div class="card-title-wrapper">
              <Icon icon="lucide:bell" size="20" color="#fa541c" />
              <h3 class="card-title">实时事件</h3>
            </div>
            <a-badge status="processing" text="实时更新" />
          </div>
          <div class="event-list">
            <div v-for="event in events" :key="event.id" class="event-item">
              <div :class="`event-icon icon-${event.type}`">
                <Icon :icon="getEventIcon(event.type)" size="16" />
              </div>
              <div class="event-content">
                <div class="event-message">{{ event.message }}</div>
                <div class="event-time">{{ event.time }}</div>
              </div>
            </div>
          </div>
        </div>
      </a-col>
    </a-row>

    <!-- 资源使用情况 -->
    <a-row :gutter="[16, 16]" class="resource-section">
      <a-col :xs="24" :sm="12" :lg="6" v-for="resource in resources" :key="resource.name">
        <div class="resource-card">
          <div class="resource-header">
            <div class="resource-title-wrapper">
              <Icon :icon="resource.icon" size="18" :color="resource.iconColor" />
              <span class="resource-name">{{ resource.name }}</span>
            </div>
            <span class="resource-value" :style="{ color: resource.valueColor }">{{ resource.usage }}%</span>
          </div>
          <a-progress :percent="resource.usage" :stroke-color="resource.progressColor" :show-info="false"
            :stroke-width="8" />
          <div class="resource-details">
            <span>{{ resource.detail }}</span>
            <span class="resource-timestamp">{{ resource.lastUpdate }}</span>
          </div>
        </div>
      </a-col>
    </a-row>

    <!-- 进程监控 & 网络连接 & 安全事件 -->
    <a-row :gutter="[16, 16]" class="detail-section">
      <!-- 进程监控 -->
      <a-col :xs="24" :lg="10">
        <div class="process-card">
          <div class="card-header">
            <div class="card-title-wrapper">
              <Icon icon="lucide:terminal" size="20" color="#fa541c" />
              <h3 class="card-title">进程监控</h3>
            </div>
            <a-tag color="orange">{{ processList.length }} 个活跃进程</a-tag>
          </div>
          <div class="process-table-wrapper">
            <table class="process-table">
              <thead>
                <tr>
                  <th>PID</th>
                  <th>进程名</th>
                  <th>CPU</th>
                  <th>内存</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="proc in processList" :key="proc.pid">
                  <td class="col-pid">{{ proc.pid }}</td>
                  <td class="col-name">
                    <Icon :icon="getProcessIcon(proc.name)" size="14" :color="proc.cpu > 30 ? '#ff4d4f' : '#8c8c8c'" />
                    {{ proc.name }}
                  </td>
                  <td class="col-cpu" :class="{ 'cpu-high': proc.cpu > 30 }">{{ proc.cpu }}%</td>
                  <td class="col-mem">{{ proc.memory }}</td>
                  <td>
                    <a-badge :status="proc.status === 'running' ? 'processing' : 'default'" :text="proc.status" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </a-col>

      <!-- 网络连接状态 -->
      <a-col :xs="24" :lg="6">
        <div class="connection-card">
          <div class="card-header">
            <div class="card-title-wrapper">
              <Icon icon="lucide:link" size="20" color="#52c41a" />
              <h3 class="card-title">网络连接</h3>
            </div>
            <a-tag color="green">{{ MOCK_CONNECTIONS.length }} 条活跃</a-tag>
          </div>
          <div class="connection-list">
            <div v-for="conn in MOCK_CONNECTIONS" :key="conn.local" class="connection-item">
              <div class="conn-top">
                <a-tag color="green" size="small">{{ conn.status }}</a-tag>
                <span class="conn-service">{{ conn.service }}</span>
              </div>
              <div class="conn-addr">
                <span class="conn-local">{{ conn.local }}</span>
                <Icon icon="lucide:arrow-right" size="12" color="#bfbfbf" />
                <span class="conn-remote">{{ conn.remote }}</span>
              </div>
            </div>
          </div>
        </div>
      </a-col>

      <!-- 安全事件 -->
      <a-col :xs="24" :lg="8">
        <div class="security-card">
          <div class="card-header">
            <div class="card-title-wrapper">
              <Icon icon="lucide:shield-check" size="20" color="#ff4d4f" />
              <h3 class="card-title">安全事件</h3>
            </div>
            <a-badge status="processing" text="实时监控" />
          </div>
          <div class="security-list">
            <div v-for="evt in MOCK_SECURITY_EVENTS" :key="evt.id" class="security-item" :class="`sec-${evt.type}`">
              <div class="sec-icon-row">
                <Icon :icon="getSecurityIcon(evt.type)" size="16" :color="getSecurityColor(evt.type)" />
                <span class="sec-title">{{ evt.title }}</span>
                <a-tag :color="getSecurityTagColor(evt.type)" size="small">{{ evt.layer }}</a-tag>
              </div>
              <div class="sec-desc">{{ evt.desc }}</div>
              <div class="sec-time">{{ evt.time }}</div>
            </div>
          </div>
        </div>
      </a-col>
    </a-row>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { Icon } from '@iconify/vue';
// 按需引入echarts，减少打包体积
import * as echarts from 'echarts/core';
import { BarChart, LineChart, PieChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { EChartsType } from 'echarts/core';
import type { CallbackDataParams } from 'echarts/types/dist/shared';

// 注册必需的组件
echarts.use([
  BarChart, LineChart, PieChart,
  GridComponent, TooltipComponent, LegendComponent, TitleComponent,
  CanvasRenderer
]);

// ═══════════════════════════════════════════════════════════════
// 类型定义
// ═══════════════════════════════════════════════════════════════
interface MetricItem {
  key: string;
  label: string;
  value: string;
  unit: string;
  trend: 'up' | 'down' | 'stable';
  change: string;
  data: number[];
  icon: string;
  iconColor: string;
  iconBg: string;
  lastUpdate: string;
}

interface ResourceItem {
  name: string;
  usage: number;
  detail: string;
  icon: string;
  iconColor: string;
  valueColor: string;
  progressColor: string;
  lastUpdate: string;
}

interface SystemEvent {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  message: string;
  time: string;
}

// ═══════════════════════════════════════════════════════════════
// 硬编码基础数据 —— 系统静态信息（银河麒麟 V11）
// ═══════════════════════════════════════════════════════════════
const STATIC_SYSTEM_INFO = {
  version: 'V11 (2503)',
  hostname: 'win000k10309',
  kernel: 'linux 6.6.0-32.7.v2025.ky11.loongarch64',
  cpu: 'Loongson-3A5000',
  arch: 'LoongArch',
  memory: '12GB',
  desktop: 'UKUI',
  username: 'vmuser'
};

// ═══════════════════════════════════════════════════════════════
// Mock 数据 —— 进程、网络连接、系统负载、安全事件
// 数据与后端 demo_engine.py 保持一致
// ═══════════════════════════════════════════════════════════════

interface ProcessInfo {
  pid: number;
  name: string;
  cpu: number;
  memory: string;
  status: string;
}

interface NetworkConnection {
  local: string;
  remote: string;
  status: string;
  pid: number;
  service: string;
}

interface SecurityEvent {
  id: string;
  type: 'critical' | 'warning' | 'success' | 'info';
  title: string;
  desc: string;
  time: string;
  layer: string;
}

// 进程监控数据 - 使用 ref 以便动态更新
const processList = ref<ProcessInfo[]>([
  { pid: 1234, name: 'nginx', cpu: 45.2, memory: '500MB', status: 'running' },
  { pid: 2345, name: 'mysqld', cpu: 28.7, memory: '2GB', status: 'running' },
  { pid: 3456, name: 'python3', cpu: 18.3, memory: '300MB', status: 'running' },
  { pid: 4567, name: 'rsyslogd', cpu: 8.5, memory: '64MB', status: 'running' },
  { pid: 5678, name: 'sshd', cpu: 2.1, memory: '8MB', status: 'running' },
]);

// 进程基准值（用于随机波动计算）
const processBaseValues = [
  { pid: 1234, name: 'nginx', baseCpu: 45.2, baseMem: 500, memUnit: 'MB' },
  { pid: 2345, name: 'mysqld', baseCpu: 28.7, baseMem: 2048, memUnit: 'MB' },
  { pid: 3456, name: 'python3', baseCpu: 18.3, baseMem: 300, memUnit: 'MB' },
  { pid: 4567, name: 'rsyslogd', baseCpu: 8.5, baseMem: 64, memUnit: 'MB' },
  { pid: 5678, name: 'sshd', baseCpu: 2.1, baseMem: 8, memUnit: 'MB' },
];

/**
 * 格式化内存显示
 */
const formatMemory = (mb: number): string => {
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(1)}GB`;
  }
  return `${Math.round(mb)}MB`;
};

/**
 * 更新进程数据 - 添加随机波动
 */
const updateProcessData = () => {
  processList.value = processBaseValues.map(proc => {
    // CPU 波动：基准值 ±15%，确保在合理范围内
    const cpuFluctuation = (Math.random() - 0.5) * 2 * proc.baseCpu * 0.15;
    let newCpu = proc.baseCpu + cpuFluctuation;
    // 边界限制
    newCpu = Math.max(0.5, Math.min(95, newCpu));

    // 内存波动：基准值 ±10%
    const memFluctuation = (Math.random() - 0.5) * 2 * proc.baseMem * 0.10;
    let newMem = proc.baseMem + memFluctuation;
    newMem = Math.max(1, newMem);

    return {
      pid: proc.pid,
      name: proc.name,
      cpu: parseFloat(newCpu.toFixed(1)),
      memory: formatMemory(newMem),
      status: 'running'
    };
  });
};

const MOCK_CONNECTIONS: NetworkConnection[] = [
  { local: '0.0.0.0:80', remote: '192.168.1.100:52341', status: 'ESTABLISHED', pid: 1234, service: 'nginx' },
  { local: '0.0.0.0:3306', remote: '192.168.1.100:52342', status: 'ESTABLISHED', pid: 2345, service: 'mysqld' },
  { local: '0.0.0.0:22', remote: '10.0.0.5:49832', status: 'ESTABLISHED', pid: 5678, service: 'sshd' },
];

const MOCK_SYSTEM_LOAD = { load1: 3.85, load5: 3.12, load15: 2.67, cpuCount: 4 };

const MOCK_SECURITY_EVENTS: SecurityEvent[] = [
  { id: 'sec-001', type: 'critical', title: '安全护栏拦截', desc: 'rm -rf /var/log/* — 风险评分 1.0，已在参数校验层拦截', time: '14:32:15', layer: '风险评分' },
  { id: 'sec-002', type: 'critical', title: '注入攻击检测', desc: '识别到 prompt_injection 攻击模式，已拒绝执行', time: '14:28:03', layer: '注入检测' },
  { id: 'sec-003', type: 'warning', title: '高危操作拦截', desc: 'chmod 777 /etc/shadow — 危险参数已拦截', time: '14:25:41', layer: '参数校验' },
  { id: 'sec-004', type: 'success', title: '安全校验通过', desc: '系统状态查询操作安全放行', time: '14:20:10', layer: '意图分类' },
  { id: 'sec-005', type: 'success', title: '安全校验通过', desc: '磁盘使用率检查操作安全放行', time: '14:15:33', layer: '意图分类' },
];

// ═══════════════════════════════════════════════════════════════
// 随机数据生成工具函数
// ═══════════════════════════════════════════════════════════════

/**
 * 生成指定范围内的随机浮点数，并保留指定小数位
 */
const randomFloat = (min: number, max: number, decimals = 1): number => {
  const val = Math.random() * (max - min) + min;
  return parseFloat(val.toFixed(decimals));
};

/**
 * 基于前一个值生成波动数据（随机游走算法，确保数据连续性）
 * @param prevValue 前一个值
 * @param min 最小值
 * @param max 最大值
 * @param volatility 波动系数 (0-1)，越大波动越剧烈
 */
const generateFluctuation = (
  prevValue: number,
  min: number,
  max: number,
  volatility = 0.15
): number => {
  const range = max - min;
  const change = (Math.random() - 0.5) * 2 * range * volatility;
  let newValue = prevValue + change;
  // 边界回弹：超出范围时向中心拉回
  if (newValue < min) newValue = min + Math.abs(change) * 0.5;
  if (newValue > max) newValue = max - Math.abs(change) * 0.5;
  return parseFloat(newValue.toFixed(1));
};

/**
 * 格式化当前时间为 HH:MM:SS
 */
const formatNow = (): string => {
  const now = new Date();
  return now.toLocaleTimeString('zh-CN', { hour12: false });
};

// ═══════════════════════════════════════════════════════════════
// 响应式状态
// ═══════════════════════════════════════════════════════════════

// 当前时间显示
const currentTime = ref('');

// 核心指标数据（动态随机）
const metrics = ref<MetricItem[]>([
  {
    key: 'cpu_usage',
    label: 'CPU 使用率',
    value: '0',
    unit: '%',
    trend: 'stable',
    change: '0%',
    data: Array(12).fill(0),
    icon: 'lucide:cpu',
    iconColor: '#ff4d4f',
    iconBg: '#fff1f0',
    lastUpdate: formatNow()
  },
  {
    key: 'memory_usage',
    label: '内存使用率',
    value: '0',
    unit: '%',
    trend: 'stable',
    change: '0%',
    data: Array(12).fill(0),
    icon: 'lucide:hard-drive',
    iconColor: '#1890ff',
    iconBg: '#e6f7ff',
    lastUpdate: formatNow()
  },
  {
    key: 'disk_usage',
    label: '磁盘使用率',
    value: '0',
    unit: '%',
    trend: 'stable',
    change: '0%',
    data: Array(12).fill(0),
    icon: 'lucide:database',
    iconColor: '#faad14',
    iconBg: '#fffbe6',
    lastUpdate: formatNow()
  },
  {
    key: 'network_io',
    label: '网络 I/O',
    value: '0',
    unit: 'MB/s',
    trend: 'stable',
    change: '0%',
    data: Array(12).fill(0),
    icon: 'lucide:wifi',
    iconColor: '#52c41a',
    iconBg: '#f6ffed',
    lastUpdate: formatNow()
  }
]);

// 网络流量统计
const networkStats = ref({
  in: '0.00',
  out: '0.00',
  total: '0.00'
});

// 趋势统计
const trendStats = ref([
  { label: 'CPU 均值', value: '0%', color: '#1890ff' },
  { label: '内存峰值', value: '0%', color: '#52c41a' },
  { label: '磁盘占用', value: '0%', color: '#faad14' }
]);

// 系统信息列表（硬编码 + 动态）
const systemInfoList = computed(() => [
  { label: '版本号', value: STATIC_SYSTEM_INFO.version, className: '' },
  { label: '计算机名', value: STATIC_SYSTEM_INFO.hostname, className: 'font-mono' },
  { label: '内核', value: STATIC_SYSTEM_INFO.kernel, className: 'font-mono text-small' },
  { label: 'CPU', value: STATIC_SYSTEM_INFO.cpu, className: 'font-bold' },
  { label: '架构', value: STATIC_SYSTEM_INFO.arch, className: 'arch-tag' },
  { label: '内存', value: STATIC_SYSTEM_INFO.memory, className: '' },
  { label: '桌面', value: STATIC_SYSTEM_INFO.desktop, className: '' },
  { label: '用户名', value: STATIC_SYSTEM_INFO.username, className: 'font-mono' }
]);

// 资源使用情况（动态随机）
const resources = computed<ResourceItem[]>(() => {
  const cpuUsage = parseFloat(metrics.value[0]?.value || '0');
  const memUsage = parseFloat(metrics.value[1]?.value || '0');
  const diskUsage = parseFloat(metrics.value[2]?.value || '0');
  const netUsage = parseFloat(metrics.value[3]?.value || '0');

  return [
    {
      name: 'CPU',
      usage: Math.round(cpuUsage),
      detail: `${STATIC_SYSTEM_INFO.cpu} · 4核`,
      icon: 'lucide:cpu',
      iconColor: '#ff4d4f',
      valueColor: cpuUsage > 80 ? '#ff4d4f' : cpuUsage > 60 ? '#faad14' : '#52c41a',
      progressColor: cpuUsage > 80 ? '#ff4d4f' : cpuUsage > 60 ? '#faad14' : '#52c41a',
      lastUpdate: metrics.value[0]?.lastUpdate || '--'
    },
    {
      name: '内存',
      usage: Math.round(memUsage),
      detail: `已用 ${(memUsage * 0.12).toFixed(1)}GB / 12GB`,
      icon: 'lucide:hard-drive',
      iconColor: '#1890ff',
      valueColor: memUsage > 80 ? '#ff4d4f' : memUsage > 60 ? '#faad14' : '#52c41a',
      progressColor: memUsage > 80 ? '#ff4d4f' : memUsage > 60 ? '#faad14' : '#52c41a',
      lastUpdate: metrics.value[1]?.lastUpdate || '--'
    },
    {
      name: '磁盘',
      usage: Math.round(diskUsage),
      detail: `已用 ${(diskUsage * 5).toFixed(1)}GB / 500GB`,
      icon: 'lucide:database',
      iconColor: '#faad14',
      valueColor: diskUsage > 90 ? '#ff4d4f' : diskUsage > 75 ? '#faad14' : '#52c41a',
      progressColor: diskUsage > 90 ? '#ff4d4f' : diskUsage > 75 ? '#faad14' : '#52c41a',
      lastUpdate: metrics.value[2]?.lastUpdate || '--'
    },
    {
      name: '网络',
      usage: Math.min(100, Math.round(netUsage * 10)),
      detail: `带宽占用 ${(netUsage * 10).toFixed(1)}%`,
      icon: 'lucide:wifi',
      iconColor: '#52c41a',
      valueColor: '#1890ff',
      progressColor: '#52c41a',
      lastUpdate: metrics.value[3]?.lastUpdate || '--'
    }
  ];
});

// 事件列表
const events = ref<SystemEvent[]>([]);

// 图表周期
const chartPeriod = ref<'1h' | '24h' | '7d'>('24h');

// 图表引用
const chartRefs = ref<Record<string, HTMLElement>>({});
const trendChart = ref<HTMLElement | null>(null);
const networkChart = ref<HTMLElement | null>(null);
let trendChartInstance: EChartsType | null = null;
let networkChartInstance: EChartsType | null = null;
const miniCharts: Record<string, EChartsType> = {};

// ═══════════════════════════════════════════════════════════════
// 计算属性
// ═══════════════════════════════════════════════════════════════

const systemStatusClass = computed(() => {
  const cpu = parseFloat(metrics.value[0]?.value || '0');
  const mem = parseFloat(metrics.value[1]?.value || '0');
  const disk = parseFloat(metrics.value[2]?.value || '0');

  if (cpu > 90 || mem > 90 || disk > 95) return 'status-error';
  if (cpu > 75 || mem > 75 || disk > 85) return 'status-warning';
  return 'status-healthy';
});

const systemStatusText = computed(() => {
  const cls = systemStatusClass.value;
  if (cls === 'status-error') return '系统负载过高';
  if (cls === 'status-warning') return '系统负载较高';
  return '系统运行正常';
});

// ═══════════════════════════════════════════════════════════════
// 数据更新逻辑
// ═══════════════════════════════════════════════════════════════

// 上一次的数据值（用于波动计算）
let lastCpuValue = randomFloat(25, 55);
let lastMemValue = randomFloat(40, 70);
let lastDiskValue = randomFloat(55, 80);
let lastNetValue = randomFloat(2, 15);

/**
 * 更新核心指标数据 —— 使用随机游走确保数据连续性
 */
const updateMetrics = () => {
  const now = formatNow();

  // CPU: 25%-85% 波动，中等波动率
  lastCpuValue = generateFluctuation(lastCpuValue, 25, 85, 0.12);
  const cpuTrend = lastCpuValue > parseFloat(metrics.value[0]!.value) ? 'up' :
    lastCpuValue < parseFloat(metrics.value[0]!.value) ? 'down' : 'stable';
  const cpuChange = (lastCpuValue - parseFloat(metrics.value[0]!.value || '0')).toFixed(1);
  metrics.value[0]!.value = lastCpuValue.toFixed(1);
  metrics.value[0]!.trend = cpuTrend as 'up' | 'down' | 'stable';
  metrics.value[0]!.change = `${parseFloat(cpuChange) > 0 ? '+' : ''}${cpuChange}%`;
  metrics.value[0]!.data.shift();
  metrics.value[0]!.data.push(lastCpuValue);
  metrics.value[0]!.lastUpdate = now;

  // 内存: 40%-80% 波动，低波动率（内存变化较缓慢）
  lastMemValue = generateFluctuation(lastMemValue, 40, 80, 0.06);
  const memTrend = lastMemValue > parseFloat(metrics.value[1]!.value) ? 'up' :
    lastMemValue < parseFloat(metrics.value[1]!.value) ? 'down' : 'stable';
  const memChange = (lastMemValue - parseFloat(metrics.value[1]!.value || '0')).toFixed(1);
  metrics.value[1]!.value = lastMemValue.toFixed(1);
  metrics.value[1]!.trend = memTrend as 'up' | 'down' | 'stable';
  metrics.value[1]!.change = `${parseFloat(memChange) > 0 ? '+' : ''}${memChange}%`;
  metrics.value[1]!.data.shift();
  metrics.value[1]!.data.push(lastMemValue);
  metrics.value[1]!.lastUpdate = now;

  // 磁盘: 55%-90% 波动，极低波动率（磁盘变化很慢）
  lastDiskValue = generateFluctuation(lastDiskValue, 55, 90, 0.02);
  const diskTrend = lastDiskValue > parseFloat(metrics.value[2]!.value) ? 'up' :
    lastDiskValue < parseFloat(metrics.value[2]!.value) ? 'down' : 'stable';
  const diskChange = (lastDiskValue - parseFloat(metrics.value[2]!.value || '0')).toFixed(1);
  metrics.value[2]!.value = lastDiskValue.toFixed(1);
  metrics.value[2]!.trend = diskTrend as 'up' | 'down' | 'stable';
  metrics.value[2]!.change = `${parseFloat(diskChange) > 0 ? '+' : ''}${diskChange}%`;
  metrics.value[2]!.data.shift();
  metrics.value[2]!.data.push(lastDiskValue);
  metrics.value[2]!.lastUpdate = now;

  // 网络 I/O: 2-50 MB/s，高波动率
  lastNetValue = generateFluctuation(lastNetValue, 2, 50, 0.25);
  const netTrend = lastNetValue > parseFloat(metrics.value[3]!.value) ? 'up' :
    lastNetValue < parseFloat(metrics.value[3]!.value) ? 'down' : 'stable';
  const netChange = (lastNetValue - parseFloat(metrics.value[3]!.value || '0')).toFixed(1);
  metrics.value[3]!.value = lastNetValue.toFixed(1);
  metrics.value[3]!.trend = netTrend as 'up' | 'down' | 'stable';
  metrics.value[3]!.change = `${parseFloat(netChange) > 0 ? '+' : ''}${netChange}%`;
  metrics.value[3]!.data.shift();
  metrics.value[3]!.data.push(lastNetValue);
  metrics.value[3]!.lastUpdate = now;

  // 更新网络统计
  const netIn = randomFloat(lastNetValue * 0.3, lastNetValue * 0.7, 2);
  const netOut = randomFloat(lastNetValue * 0.2, lastNetValue * 0.5, 2);
  networkStats.value = {
    in: netIn.toFixed(2),
    out: netOut.toFixed(2),
    total: (netIn + netOut).toFixed(2)
  };

  // 更新趋势统计
  const cpuAvg = (metrics.value[0]!.data.reduce((a, b) => a + b, 0) / metrics.value[0]!.data.length).toFixed(1);
  const memPeak = Math.max(...metrics.value[1]!.data).toFixed(1);
  trendStats.value = [
    { label: 'CPU 均值', value: `${cpuAvg}%`, color: '#1890ff' },
    { label: '内存峰值', value: `${memPeak}%`, color: '#52c41a' },
    { label: '磁盘占用', value: `${lastDiskValue.toFixed(1)}%`, color: '#faad14' }
  ];
};

/**
 * 生成系统事件
 */
const generateEvents = () => {
  const cpu = parseFloat(metrics.value[0]?.value || '0');
  const mem = parseFloat(metrics.value[1]?.value || '0');
  const disk = parseFloat(metrics.value[2]?.value || '0');

  const newEvents: SystemEvent[] = [];

  if (cpu > 80) {
    newEvents.push({
      id: `cpu_${Date.now()}`,
      type: cpu > 90 ? 'error' : 'warning',
      message: `CPU 使用率${cpu > 90 ? '过高' : '较高'}: ${cpu.toFixed(1)}%`,
      time: formatNow()
    });
  }
  if (mem > 75) {
    newEvents.push({
      id: `mem_${Date.now()}`,
      type: mem > 90 ? 'error' : 'warning',
      message: `内存使用率${mem > 90 ? '过高' : '较高'}: ${mem.toFixed(1)}%`,
      time: formatNow()
    });
  }
  if (disk > 85) {
    newEvents.push({
      id: `disk_${Date.now()}`,
      type: disk > 95 ? 'error' : 'warning',
      message: `磁盘使用率${disk > 95 ? '过高' : '较高'}: ${disk.toFixed(1)}%`,
      time: formatNow()
    });
  }

  if (newEvents.length === 0) {
    newEvents.push({
      id: `normal_${Date.now()}`,
      type: 'success',
      message: '系统运行正常，所有指标在合理范围内',
      time: formatNow()
    });
  }

  // 保留最近8条事件，避免列表过长
  events.value = [...newEvents, ...events.value].slice(0, 8);
};

// ═══════════════════════════════════════════════════════════════
// 图表初始化与更新
// ═══════════════════════════════════════════════════════════════

const initMiniChart = (element: HTMLElement, data: number[], color = '#1890ff'): EChartsType | undefined => {
  if (!element) return;
  const existing = echarts.getInstanceByDom(element);
  if (existing && !existing.isDisposed()) existing.dispose();

  const chart = echarts.init(element);
  chart.setOption({
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { type: 'category', show: false },
    yAxis: { type: 'value', show: false, min: 0 },
    series: [{
      type: 'line',
      data,
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 2, color },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: `${color}33` },
            { offset: 1, color: `${color}05` }
          ]
        }
      }
    }]
  });
  return chart;
};

const initNetworkChart = () => {
  if (!networkChart.value) return;
  const existing = echarts.getInstanceByDom(networkChart.value);
  if (existing && !existing.isDisposed()) existing.dispose();

  networkChartInstance = echarts.init(networkChart.value);
  updateNetworkChart();
};

const updateNetworkChart = () => {
  if (!networkChartInstance) return;

  const inVal = parseFloat(networkStats.value.in);
  const outVal = parseFloat(networkStats.value.out);

  networkChartInstance.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params: CallbackDataParams) => `${params.seriesName}<br/>${params.name}: ${params.value} MB/s (${params.percent ?? 0}%)`
    },
    legend: {
      orient: 'vertical',
      left: '2%',
      top: 'center',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: '#8c8c8c', fontSize: 11 }
    },
    series: [{
      name: '网络流量',
      type: 'pie',
      radius: ['35%', '60%'],
      center: ['62%', '50%'],
      data: [
        { value: inVal, name: '入流量', itemStyle: { color: '#52c41a' } },
        { value: outVal, name: '出流量', itemStyle: { color: '#1890ff' } }
      ],
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' }
      },
      label: {
        show: false
      }
    }]
  });
};

const initTrendChart = () => {
  if (!trendChart.value) return;
  const existing = echarts.getInstanceByDom(trendChart.value);
  if (existing && !existing.isDisposed()) existing.dispose();

  trendChartInstance = echarts.init(trendChart.value);
  updateTrendChart();
};

const updateTrendChart = () => {
  if (!trendChartInstance) return;

  const cpuData = metrics.value[0]?.data || [];
  const memData = metrics.value[1]?.data || [];
  const labels = generateTimeLabels();

  trendChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      textStyle: { color: '#595959' },
      formatter: (params: CallbackDataParams | CallbackDataParams[]) => {
        const list = Array.isArray(params) ? params : [params];
        let result = `${(list[0] as any)?.axisValue || ''}<br/>`;
        list.forEach((param: CallbackDataParams) => {
          result += `${param.marker}${param.seriesName}: ${param.value}%<br/>`;
        });
        return result;
      }
    },
    legend: {
      data: ['CPU使用率', '内存使用率', '磁盘使用率'],
      bottom: 0,
      textStyle: { color: '#8c8c8c', fontSize: 12 }
    },
    grid: { left: '3%', right: '3%', top: '5%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#8c8c8c', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: '使用率 (%)',
      max: 100,
      axisLine: { show: true, lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#8c8c8c', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } }
    },
    series: [
      {
        name: 'CPU使用率',
        type: 'line',
        smooth: true,
        data: cpuData,
        itemStyle: { color: '#1890ff' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(24,144,255,0.2)' },
              { offset: 1, color: 'rgba(24,144,255,0.05)' }
            ]
          }
        }
      },
      {
        name: '内存使用率',
        type: 'line',
        smooth: true,
        data: memData,
        itemStyle: { color: '#52c41a' }
      },
      {
        name: '磁盘使用率',
        type: 'line',
        smooth: true,
        data: metrics.value[2]?.data || [],
        itemStyle: { color: '#faad14' }
      }
    ]
  }, true); // true = not merge, replace
};

const generateTimeLabels = () => {
  const labels: string[] = [];
  const now = new Date();
  const count = chartPeriod.value === '1h' ? 12 : chartPeriod.value === '24h' ? 12 : 7;

  for (let i = count - 1; i >= 0; i--) {
    const t = new Date(now.getTime() - i * 3000); // 每3秒一个点
    labels.push(t.toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }));
  }
  return labels;
};

const updateCharts = () => {
  updateTrendChart();
  updateNetworkChart();

  // 更新迷你图表
  metrics.value.forEach(metric => {
    const element = chartRefs.value[metric.key];
    if (!element) return;

    if (miniCharts[metric.key]) {
      miniCharts[metric.key]!.setOption({
        series: [{ data: metric.data }]
      });
    } else {
      const chart = initMiniChart(element, metric.data, metric.iconColor);
      if (chart) miniCharts[metric.key] = chart;
    }
  });
};

// ═══════════════════════════════════════════════════════════════
// 事件图标映射
// ═══════════════════════════════════════════════════════════════
const getEventIcon = (type: string): string => {
  const icons: Record<string, string> = {
    success: 'lucide:check-circle',
    info: 'lucide:info',
    warning: 'lucide:alert-triangle',
    error: 'lucide:x-circle'
  };
  return icons[type] || 'lucide:info';
};

// ═══════════════════════════════════════════════════════════════
// 进程/安全事件辅助函数
// ═══════════════════════════════════════════════════════════════

const getProcessIcon = (name: string): string => {
  const map: Record<string, string> = {
    nginx: 'lucide:globe',
    mysqld: 'lucide:database',
    python3: 'lucide:code',
    rsyslogd: 'lucide:scroll-text',
    sshd: 'lucide:terminal',
  };
  return map[name] || 'lucide:box';
};

const getSecurityIcon = (type: string): string => {
  const map: Record<string, string> = {
    critical: 'lucide:shield-x',
    warning: 'lucide:shield-alert',
    success: 'lucide:shield-check',
    info: 'lucide:info',
  };
  return map[type] || 'lucide:info';
};

const getSecurityColor = (type: string): string => {
  const map: Record<string, string> = {
    critical: '#ff4d4f',
    warning: '#faad14',
    success: '#52c41a',
    info: '#1890ff',
  };
  return map[type] || '#8c8c8c';
};

const getSecurityTagColor = (type: string): string => {
  const map: Record<string, string> = {
    critical: 'red',
    warning: 'orange',
    success: 'green',
    info: 'blue',
  };
  return map[type] || 'default';
};

// ═══════════════════════════════════════════════════════════════
// 定时器与生命周期
// ═══════════════════════════════════════════════════════════════
let timeTimer: ReturnType<typeof setInterval> | null = null;
let dataTimer: ReturnType<typeof setInterval> | null = null;

const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

const handleResize = () => {
  trendChartInstance?.resize();
  networkChartInstance?.resize();
  Object.values(miniCharts).forEach(chart => chart?.resize());
};

onMounted(() => {
  updateTime();
  timeTimer = setInterval(updateTime, 1000);

  // 初始化数据
  updateMetrics();
  generateEvents();
  updateProcessData(); // 初始化进程数据

  // 延迟初始化图表，确保DOM已渲染
  setTimeout(() => {
    initTrendChart();
    initNetworkChart();
    updateCharts();
  }, 200);

  // 每3秒更新动态数据（频率适中，既展示动态效果又避免过度刷新）
  dataTimer = setInterval(() => {
    updateMetrics();
    generateEvents();
    updateProcessData(); // 更新进程监控数据（带随机波动）
    updateCharts();
  }, 3000);

  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  if (timeTimer) clearInterval(timeTimer);
  if (dataTimer) clearInterval(dataTimer);
  window.removeEventListener('resize', handleResize);

  trendChartInstance?.dispose();
  networkChartInstance?.dispose();
  Object.values(miniCharts).forEach(chart => chart?.dispose());
});
</script>

<style scoped>
.dashboard-container {
  min-height: 100vh;
  padding: 24px;
  background: #f7f8fa;
}

/* ── 头部样式 ── */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 0 4px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.platform-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
  letter-spacing: -0.5px;
}

.platform-desc {
  font-size: 13px;
  color: #8c8c8c;
}

.header-right {
  display: flex;
  align-items: center;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #52c41a;
}

.status-indicator.status-healthy {
  color: #52c41a;
}

.status-indicator.status-warning {
  color: #faad14;
}

.status-indicator.status-error {
  color: #ff4d4f;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #52c41a;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-dot.status-healthy {
  background: #52c41a;
}

.status-dot.status-warning {
  background: #faad14;
}

.status-dot.status-error {
  background: #ff4d4f;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.2);
  }
}

.time-display {
  font-size: 13px;
  color: #595959;
  font-variant-numeric: tabular-nums;
}

/* ── 指标卡片 ── */
.metrics-section {
  margin-bottom: 24px;
}

.metric-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  height: 150px;
  position: relative;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  transition: all 0.3s ease;
  cursor: pointer;
  overflow: hidden;
}

.metric-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.metric-main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.metric-icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.metric-info {
  flex: 1;
  min-width: 0;
}

.metric-label {
  display: block;
  font-size: 13px;
  color: #8c8c8c;
  margin-bottom: 4px;
}

.metric-value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.metric-value {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

.metric-unit {
  font-size: 13px;
  color: #8c8c8c;
}

.metric-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 2;
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
}

.trend-up {
  color: #ff4d4f;
}

.trend-down {
  color: #52c41a;
}

.trend-stable {
  color: #8c8c8c;
}

.metric-update-time {
  font-size: 11px;
  color: #bfbfbf;
}

.metric-chart {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 50px;
  opacity: 0.5;
  z-index: 1;
}

/* ── 系统概览区 ── */
.overview-section {
  margin-bottom: 24px;
}

.system-info-card,
.network-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  height: 100%;
  min-height: 340px;
  transition: all 0.3s ease;
  border: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
}

.system-info-card:hover,
.network-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
  border-color: #d9d9d9;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.card-title-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.system-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  flex: 1;
  align-content: start;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  background: #fafafa;
  border-radius: 8px;
  transition: all 0.2s ease;
  min-height: 55px;
}

.info-item:hover {
  background: #f5f5f5;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.info-label {
  font-size: 12px;
  color: #8c8c8c;
  font-weight: 500;
}

.info-value {
  font-size: 13px;
  color: #262626;
  font-weight: 600;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.font-mono {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}

.font-bold {
  font-weight: 700;
}

.text-small {
  font-size: 11px;
}

.arch-tag {
  display: inline-block;
  background: #f0f5ff;
  color: #722ed1;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  width: fit-content;
}

/* 网络统计 */
.network-stats {
  display: flex;
  justify-content: space-around;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}

.network-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex: 1;
}

.network-stat-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #8c8c8c;
}

.network-stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
  font-variant-numeric: tabular-nums;
}

.network-stat-unit {
  font-size: 11px;
  color: #bfbfbf;
}

.network-divider {
  width: 1px;
  height: 40px;
  background: #e8e8e8;
}

.chart-container-small {
  flex: 1;
  min-height: 0;
  width: 100%;
}

/* ── 内容区 ── */
.content-section {
  margin-bottom: 24px;
}

.chart-card,
.event-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  height: 460px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
  transition: all 0.3s ease;
}

.chart-card:hover,
.event-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
  border-color: #d9d9d9;
}

.trend-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 12px;
  padding: 8px 0;
}

.trend-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.trend-stat-label {
  font-size: 11px;
  color: #8c8c8c;
}

.trend-stat-value {
  font-size: 16px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.chart-container {
  height: 320px;
  width: 100%;
}

/* 事件列表 */
.event-list {
  height: 380px;
  overflow-y: auto;
}

.event-list::-webkit-scrollbar {
  width: 4px;
}

.event-list::-webkit-scrollbar-track {
  background: transparent;
}

.event-list::-webkit-scrollbar-thumb {
  background: #d9d9d9;
  border-radius: 2px;
}

.event-item {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.2s;
}

.event-item:hover {
  background: #fafafa;
  margin: 0 -8px;
  padding: 12px 8px;
}

.event-item:last-child {
  border-bottom: none;
}

.event-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-success {
  background: rgba(82, 196, 26, 0.1);
  color: #52c41a;
}

.icon-info {
  background: rgba(24, 144, 255, 0.1);
  color: #1890ff;
}

.icon-warning {
  background: rgba(250, 173, 20, 0.1);
  color: #faad14;
}

.icon-error {
  background: rgba(255, 77, 79, 0.1);
  color: #ff4d4f;
}

.event-content {
  flex: 1;
  min-width: 0;
}

.event-message {
  font-size: 13px;
  color: #262626;
  line-height: 1.5;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-time {
  font-size: 12px;
  color: #8c8c8c;
}

/* ── 资源卡片 ── */
.resource-section {
  margin-bottom: 24px;
}

.resource-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
  transition: all 0.3s ease;
}

.resource-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
  border-color: #d9d9d9;
}

.resource-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.resource-title-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.resource-name {
  font-size: 14px;
  font-weight: 500;
  color: #262626;
}

.resource-value {
  font-size: 20px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.resource-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 12px;
  color: #8c8c8c;
}

.resource-timestamp {
  font-size: 11px;
  color: #bfbfbf;
}

/* ── 响应式设计 ── */

/* ── 详情区（进程 / 网络连接 / 安全事件）── */
.detail-section {
  margin-bottom: 24px;
}

.process-card,
.connection-card,
.security-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
  transition: all 0.3s ease;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.process-card:hover,
.connection-card:hover,
.security-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
  border-color: #d9d9d9;
}

/* 进程表格 */
.process-table-wrapper {
  flex: 1;
  overflow-x: auto;
}

.process-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.process-table thead th {
  text-align: left;
  padding: 10px 12px;
  color: #8c8c8c;
  font-weight: 500;
  font-size: 12px;
  border-bottom: 1px solid #f0f0f0;
  white-space: nowrap;
}

.process-table tbody td {
  padding: 10px 12px;
  border-bottom: 1px solid #fafafa;
  color: #262626;
}

.process-table tbody tr:hover {
  background: #fafafa;
}

.col-pid {
  font-family: 'SFMono-Regular', Consolas, monospace;
  color: #8c8c8c;
  font-size: 12px;
}

.col-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.col-cpu {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.cpu-high {
  color: #ff4d4f !important;
}

.col-mem {
  font-variant-numeric: tabular-nums;
  color: #595959;
}

/* 网络连接 */
.connection-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.connection-item {
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.connection-item:hover {
  background: #f0f5ff;
  border-color: #d6e4ff;
}

.conn-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.conn-service {
  font-size: 13px;
  font-weight: 600;
  color: #262626;
}

.conn-addr {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-family: 'SFMono-Regular', Consolas, monospace;
}

.conn-local {
  color: #1890ff;
}

.conn-remote {
  color: #8c8c8c;
}

/* 安全事件 */
.security-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.security-item {
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  transition: all 0.2s;
}

.security-item:hover {
  transform: translateX(2px);
}

.sec-critical {
  background: linear-gradient(135deg, #fff1f0 0%, #fff 100%);
  border-left: 3px solid #ff4d4f;
}

.sec-warning {
  background: linear-gradient(135deg, #fffbe6 0%, #fff 100%);
  border-left: 3px solid #faad14;
}

.sec-success {
  background: linear-gradient(135deg, #f6ffed 0%, #fff 100%);
  border-left: 3px solid #52c41a;
}

.sec-info {
  background: linear-gradient(135deg, #e6f7ff 0%, #fff 100%);
  border-left: 3px solid #1890ff;
}

.sec-icon-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.sec-title {
  font-size: 13px;
  font-weight: 600;
  color: #262626;
  flex: 1;
}

.sec-desc {
  font-size: 12px;
  color: #595959;
  line-height: 1.5;
  margin-bottom: 2px;
  padding-left: 22px;
}

.sec-time {
  font-size: 11px;
  color: #bfbfbf;
  padding-left: 22px;
}

/* 系统负载栏 */
.system-load-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 14px;
  background: linear-gradient(135deg, #f9f0ff 0%, #f0f5ff 100%);
  border-radius: 8px;
  border: 1px solid #d3adf7;
}

.load-label {
  font-size: 12px;
  color: #722ed1;
  font-weight: 600;
}

.load-values {
  display: flex;
  align-items: center;
  gap: 4px;
  font-variant-numeric: tabular-nums;
}

.load-val {
  font-size: 15px;
  font-weight: 700;
  color: #262626;
}

.load-high {
  color: #ff4d4f !important;
}

.load-sep {
  color: #bfbfbf;
  font-size: 12px;
}

.load-hint {
  font-size: 11px;
  color: #bfbfbf;
  margin-left: auto;
}

@media (max-width: 1200px) {
  .system-info-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .platform-title {
    font-size: 20px;
  }

  .metric-card {
    height: 130px;
  }

  .metric-value {
    font-size: 24px;
  }

  .system-info-card,
  .network-card {
    height: auto;
    min-height: 300px;
  }

  .chart-card,
  .event-card {
    height: auto;
    min-height: 400px;
  }

  .network-stats {
    flex-direction: column;
    gap: 12px;
  }

  .network-divider {
    width: 100%;
    height: 1px;
  }

  .trend-stats {
    gap: 16px;
  }
}
</style>
