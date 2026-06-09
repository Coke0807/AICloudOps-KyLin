<template>
  <div class="interception-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon">
            <Icon icon="lucide:shield-off" size="32" color="#ff4d4f" />
          </div>
          <div class="header-text">
            <h1 class="page-title">拦截记录</h1>
            <p class="page-subtitle">查看安全护栏拦截的高危操作记录</p>
          </div>
        </div>
        <div class="header-actions">
          <a-button type="primary" @click="fetchEvents" :loading="loading">
            <Icon icon="lucide:refresh-cw" size="16" style="margin-right: 6px;" />
            <span>刷新数据</span>
          </a-button>
        </div>
      </div>
    </div>

    <div class="interception-content">
      <!-- 统计卡片 -->
      <a-row :gutter="[24, 24]" class="stats-row">
        <a-col :xs="24" :sm="12" :lg="8">
          <div class="stat-card stat-total">
            <div class="stat-icon-wrap">
              <Icon icon="lucide:activity" size="26" />
            </div>
            <div class="stat-info">
              <div class="stat-label">总事件数</div>
              <div class="stat-number">{{ totalCount }}</div>
            </div>
          </div>
        </a-col>
        <a-col :xs="24" :sm="12" :lg="8">
          <div class="stat-card stat-blocked">
            <div class="stat-icon-wrap">
              <Icon icon="lucide:shield-off" size="26" />
            </div>
            <div class="stat-info">
              <div class="stat-label">已拦截</div>
              <div class="stat-number">{{ blockedCount }}</div>
            </div>
          </div>
        </a-col>
        <a-col :xs="24" :sm="12" :lg="8">
          <div class="stat-card stat-passed">
            <div class="stat-icon-wrap">
              <Icon icon="lucide:shield-check" size="26" />
            </div>
            <div class="stat-info">
              <div class="stat-label">已通过</div>
              <div class="stat-number">{{ safeCount }}</div>
            </div>
          </div>
        </a-col>
      </a-row>

      <!-- 事件列表 -->
      <div class="content-card">
        <div class="card-header">
          <div class="header-title">
            <Icon icon="lucide:list" size="18" color="#ff4d4f" />
            拦截事件列表
          </div>
          <div class="header-actions">
            <a-radio-group v-model:value="filterMode" button-style="solid" size="small">
              <a-radio-button value="all">全部</a-radio-button>
              <a-radio-button value="blocked">已拦截</a-radio-button>
              <a-radio-button value="safe">已通过</a-radio-button>
            </a-radio-group>
          </div>
        </div>

        <div class="card-content">
          <a-table
            :data-source="filteredEvents"
            :columns="columns"
            :loading="loading"
            :pagination="pagination"
            row-key="id"
            size="middle"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'id'">
                <span class="id-text">#{{ record.id }}</span>
              </template>

              <template v-if="column.key === 'trace_id'">
                <span class="trace-id-text">{{ truncateId(record.trace_id) }}</span>
              </template>

              <template v-if="column.key === 'risk_level'">
                <a-tag :color="getRiskColor(record.risk_level)">
                  {{ getRiskLabel(record.risk_level) }}
                </a-tag>
              </template>

              <template v-if="column.key === 'is_safe'">
                <span v-if="record.is_safe" class="status-pill status-pill-safe">
                  <span class="status-dot status-dot-safe"></span>
                  <span class="status-text">已通过</span>
                </span>
                <span v-else class="status-pill status-pill-blocked">
                  <span class="status-dot status-dot-blocked"></span>
                  <span class="status-text">已拦截</span>
                </span>
              </template>

              <template v-if="column.key === 'created_at'">
                <span class="time-text">{{ formatDate(record.created_at) }}</span>
              </template>

              <template v-if="column.key === 'action'">
                <a-space>
                  <a-button type="link" size="small" @click="showDetailModal(record)">
                    <Icon icon="lucide:eye" size="14" />
                    详情
                  </a-button>
                </a-space>
              </template>
            </template>

            <template #expandedRowRender="{ record }">
              <div class="expanded-detail">
                <a-descriptions :column="2" size="small" bordered>
                  <a-descriptions-item label="链路ID" :span="2">
                    <span class="mono-text">{{ record.trace_id }}</span>
                  </a-descriptions-item>
                  <a-descriptions-item label="风险等级">
                    <a-tag :color="getRiskColor(record.risk_level)">
                      {{ getRiskLabel(record.risk_level) }}
                    </a-tag>
                  </a-descriptions-item>
                  <a-descriptions-item label="安全状态">
                    <a-tag :color="record.is_safe ? 'green' : 'red'">
                      {{ record.is_safe ? '通过' : '已拦截' }}
                    </a-tag>
                  </a-descriptions-item>
                  <a-descriptions-item label="时间" :span="2">
                    {{ formatDate(record.created_at) }}
                  </a-descriptions-item>
                </a-descriptions>
                <div class="detail-section" style="margin-top: 12px;">
                  <div class="detail-section-title">
                    <Icon icon="lucide:code-2" size="14" />
                    完整数据
                  </div>
                  <pre class="detail-json">{{ formatJson(record.data) }}</pre>
                </div>
              </div>
            </template>

            <template #emptyText>
              <div class="empty-state">
                <Icon icon="lucide:inbox" size="48" color="#bfbfbf" />
                <p>暂无拦截记录</p>
              </div>
            </template>
          </a-table>
        </div>
      </div>
    </div>

    <!-- 拦截记录详情弹窗 -->
    <a-modal
      v-model:open="detailModalVisible"
      title="拦截记录详情"
      width="800px"
      :footer="null"
      :destroyOnClose="true"
    >
      <div v-if="selectedEvent" class="detail-modal-content">
        <!-- 基本信息 -->
        <div class="detail-section">
          <div class="detail-section-title">
            <Icon icon="lucide:info" size="16" color="#1890ff" />
            基本信息
          </div>
          <a-descriptions :column="2" size="small" bordered>
            <a-descriptions-item label="事件ID">
              #{{ selectedEvent.id }}
            </a-descriptions-item>
            <a-descriptions-item label="链路ID">
              <span class="mono-text">{{ selectedEvent.trace_id }}</span>
            </a-descriptions-item>
            <a-descriptions-item label="风险等级">
              <a-tag :color="getRiskColor(selectedEvent.risk_level)" :style="{ fontWeight: 600 }">
                {{ getRiskLabel(selectedEvent.risk_level) }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="安全状态">
              <a-tag :color="selectedEvent.is_safe ? 'green' : 'red'" :style="{ fontWeight: 600 }">
                {{ selectedEvent.is_safe ? '通过' : '已拦截' }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="触发步骤">
              {{ selectedEvent.step || 'SAFETY_VALIDATION' }}
            </a-descriptions-item>
            <a-descriptions-item label="时间">
              {{ formatDate(selectedEvent.created_at) }}
            </a-descriptions-item>
          </a-descriptions>
        </div>

        <!-- 安全校验详情 -->
        <div class="detail-section" style="margin-top: 16px;">
          <div class="detail-section-title">
            <Icon icon="lucide:shield-check" size="16" color="#ff4d4f" />
            安全校验详情
          </div>
          <div v-if="validationData" class="validation-layers">
            <a-collapse v-model:activeKey="activeLayers" accordion>
              <a-collapse-panel
                v-for="(layer, key) in validationData"
                :key="key"
                :header="getLayerHeader(key, layer)"
                :class="{ 'panel-blocked': !layer.passed }"
              >
                <div class="layer-content">
                  <a-descriptions :column="1" size="small" bordered>
                    <a-descriptions-item label="校验结果">
                      <a-tag :color="layer.passed ? 'green' : 'red'">
                        {{ layer.passed ? '通过' : '拦截' }}
                      </a-tag>
                    </a-descriptions-item>
                    <a-descriptions-item label="风险等级">
                      <a-tag :color="getRiskColor(layer.risk_level)">
                        {{ getRiskLabel(layer.risk_level) }}
                      </a-tag>
                    </a-descriptions-item>
                    <a-descriptions-item v-if="layer.reasons" label="拦截原因">
                      <ul class="reason-list">
                        <li v-for="(reason, idx) in layer.reasons" :key="idx">{{ reason }}</li>
                      </ul>
                    </a-descriptions-item>
                    <a-descriptions-item v-if="layer.violations" label="违规项">
                      <ul class="reason-list">
                        <li v-for="(violation, idx) in layer.violations" :key="idx">{{ violation }}</li>
                      </ul>
                    </a-descriptions-item>
                    <a-descriptions-item v-if="layer.patterns_found" label="检测到的模式">
                      <ul class="reason-list">
                        <li v-for="(pattern, idx) in layer.patterns_found" :key="idx">{{ pattern }}</li>
                      </ul>
                    </a-descriptions-item>
                    <a-descriptions-item v-if="layer.command_checked" label="检查的命令">
                      <code class="command-code">{{ layer.command_checked }}</code>
                    </a-descriptions-item>
                    <a-descriptions-item v-if="layer.intent" label="识别意图">
                      {{ layer.intent }}
                    </a-descriptions-item>
                    <a-descriptions-item v-if="layer.score !== undefined" label="风险评分">
                      {{ layer.score }}
                    </a-descriptions-item>
                    <a-descriptions-item v-if="layer.modifications?.length" label="输入修改">
                      {{ layer.modifications.join(', ') || '无' }}
                    </a-descriptions-item>
                  </a-descriptions>
                </div>
              </a-collapse-panel>
            </a-collapse>
          </div>
        </div>

        <!-- 原始数据 -->
        <div class="detail-section" style="margin-top: 16px;">
          <div class="detail-section-title">
            <Icon icon="lucide:code-2" size="16" color="#8c8c8c" />
            原始数据
          </div>
          <pre class="detail-json">{{ formatJson(selectedEvent.data) }}</pre>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import { Icon } from '@iconify/vue';
import { getSafetyEvents } from '#/api/core/aiops/agent';
import type { SafetyEvent } from '#/api/core/aiops/agent';

// 响应式数据
const loading = ref(false);
const events = ref<SafetyEvent[]>([]);
const filterMode = ref<'all' | 'blocked' | 'safe'>('all');
const detailModalVisible = ref(false);
const selectedEvent = ref<SafetyEvent | null>(null);
const activeLayers = ref<string[]>([]);

// 表格列定义
const columns = [
  {
    title: 'ID',
    key: 'id',
    dataIndex: 'id',
    width: 80,
    align: 'center' as const,
  },
  {
    title: '链路ID',
    key: 'trace_id',
    dataIndex: 'trace_id',
    width: 200,
    ellipsis: true,
  },
  {
    title: '风险等级',
    key: 'risk_level',
    dataIndex: 'risk_level',
    width: 120,
    align: 'center' as const,
  },
  {
    title: '状态',
    key: 'is_safe',
    dataIndex: 'is_safe',
    width: 130,
    align: 'center' as const,
  },
  {
    title: '时间',
    key: 'created_at',
    dataIndex: 'created_at',
    width: 180,
  },
  {
    title: '操作',
    key: 'action',
    width: 100,
    align: 'center' as const,
  },
];

// 分页配置
const pagination = {
  pageSize: 10,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
};

// 统计计算
const totalCount = computed(() => events.value.length);

const blockedCount = computed(() =>
  events.value.filter((e) => !e.is_safe).length
);

const safeCount = computed(() =>
  events.value.filter((e) => e.is_safe).length
);

// 按筛选模式过滤事件列表
const filteredEvents = computed(() => {
  if (filterMode.value === 'blocked') {
    return events.value.filter((e) => !e.is_safe);
  }
  if (filterMode.value === 'safe') {
    return events.value.filter((e) => e.is_safe);
  }
  return events.value;
});

// 获取安全层校验数据
const validationData = computed(() => {
  if (!selectedEvent.value?.data) return null;
  return selectedEvent.value.data.validation || selectedEvent.value.data.result || null;
});

// 截断 ID 显示
const truncateId = (id: string): string => {
  if (!id) return '-';
  return id.length > 20 ? `${id.slice(0, 8)}...${id.slice(-4)}` : id;
};

// 风险等级颜色映射
const getRiskColor = (level: string) => {
  const l = (level || '').toLowerCase();
  if (l === 'critical' || l === 'high') return 'red';
  if (l === 'medium') return 'orange';
  if (l === 'low') return 'blue';
  return 'green';
};

// 风险等级中文标签
const getRiskLabel = (level: string) => {
  const map: Record<string, string> = {
    critical: '严重',
    high: '高危',
    medium: '中等',
    low: '低危',
    safe: '安全',
  };
  return map[(level || '').toLowerCase()] || level || '未知';
};

// 格式化日期时间
const formatDate = (timestamp?: string) => {
  if (!timestamp) return '-';
  const date = new Date(timestamp);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

// 格式化 JSON 数据
const formatJson = (data?: Record<string, any>) => {
  if (!data) return '{}';
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
};

// 获取安全层标题
const getLayerHeader = (key: string, layer: any) => {
  const layerNames: Record<string, string> = {
    sanitizer: '输入清洗',
    intent: '意图分类',
    injection: '注入检测',
    risk_scorer: '风险评分',
    param_validator: '参数校验',
  };
  const name = layerNames[key] || key;
  const icon = layer.passed ? '✅' : '❌';
  return `${icon} ${name}`;
};

// 显示详情弹窗
const showDetailModal = (record: SafetyEvent) => {
  selectedEvent.value = record;
  activeLayers.value = [];
  detailModalVisible.value = true;
};

// 获取安全事件列表
const fetchEvents = async () => {
  loading.value = true;
  try {
    const res = await getSafetyEvents(100);
    events.value = res.events || [];
  } catch (e: any) {
    message.error(`获取拦截记录失败: ${e.message}`);
  } finally {
    loading.value = false;
  }
};

// 页面初始化
onMounted(() => {
  fetchEvents();
});
</script>

<style scoped>
.interception-container {
  padding: 24px;
  background-color: #fafafa;
  min-height: 100vh;
}

/* 页面头部 */
.interception-container .page-header {
  background: #fff;
  border-radius: 12px;
  padding: 16px 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #f0f0f0;
}

.interception-container .header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.interception-container .header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.interception-container .header-icon {
  font-size: 32px;
  color: #ff4d4f;
}

.interception-container .header-text {
  display: flex;
  flex-direction: column;
}

.interception-container .page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #262626;
  line-height: 1.2;
}

.interception-container .page-subtitle {
  color: #8c8c8c;
  margin: 0;
  font-size: 12px;
  margin-top: 4px;
}

.interception-container .header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-shrink: 0;
}

/* 头部按钮美化 */
.interception-container .header-actions :deep(.ant-btn) {
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
}
.interception-container .header-actions :deep(.ant-btn:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
}

/* 统计卡片 */
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
  background: linear-gradient(135deg, #1890ff, #69c0ff);
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

/* 内容卡片 */
.content-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.card-header {
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #262626;
}

.card-content {
  padding: 0;
}

/* 表格内文本样式 */
.id-text {
  font-weight: 500;
  color: #262626;
}

/* 状态徽章：使用点+文字组合，避免换行/拥挤 */
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.status-pill .status-text {
  letter-spacing: 0.2px;
}

.status-pill .status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.6);
}

.status-pill-safe {
  background: linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%);
  color: #389e0d;
  border-color: #b7eb8f;
}

.status-pill-safe .status-dot {
  background: #52c41a;
  box-shadow: 0 0 0 2px rgba(82, 196, 26, 0.15);
}

.status-pill-blocked {
  background: linear-gradient(135deg, #fff1f0 0%, #ffccc7 100%);
  color: #cf1322;
  border-color: #ffa39e;
}

.status-pill-blocked .status-dot {
  background: #ff4d4f;
  box-shadow: 0 0 0 2px rgba(255, 77, 79, 0.15);
  animation: pulse-blocked 1.8s ease-in-out infinite;
}

@keyframes pulse-blocked {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.85); }
}

.trace-id-text {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  color: #8c8c8c;
}

.time-text {
  font-size: 13px;
  color: #8c8c8c;
}

.mono-text {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  color: #595959;
  word-break: break-all;
}

/* 展开行详情 */
.expanded-detail {
  padding: 12px 16px;
}

.detail-section {
  margin-bottom: 16px;
}

.detail-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #262626;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.detail-json {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 6px;
  font-size: 12px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
  margin: 0;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

/* 详情弹窗 */
.detail-modal-content {
  max-height: 70vh;
  overflow-y: auto;
  padding-right: 8px;
}

.validation-layers {
  /* collapse 样式 */
}

.panel-blocked :deep(.ant-collapse-header) {
  background: #fff1f0;
}

.layer-content {
  padding: 8px 0;
}

.reason-list {
  margin: 0;
  padding-left: 20px;
}

.reason-list li {
  font-size: 13px;
  color: #595959;
  line-height: 1.8;
}

.command-code {
  display: inline-block;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 12px;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
  color: #bfbfbf;
}

.empty-state p {
  margin: 12px 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .interception-container {
    padding: 16px;
  }

  .interception-container .page-header {
    padding: 20px;
    margin-bottom: 16px;
  }

  .interception-container .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .interception-container .header-actions {
    width: 100%;
    justify-content: flex-start;
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
}
</style>
