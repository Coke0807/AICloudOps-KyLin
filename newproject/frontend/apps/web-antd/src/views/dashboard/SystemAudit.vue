<template>
  <div class="audit-log">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>审计日志</h1>
      <div class="header-actions">
        <a-button @click="handleRefresh">
          <Icon icon="material-symbols:refresh" />
          刷新
        </a-button>
        <a-button v-if="activeTab === 'audit'" @click="handleExport">
          <Icon icon="material-symbols:download" />
          导出
        </a-button>
        <a-button
          v-if="activeTab === 'audit' && selectedRowKeys.length > 0"
          type="primary"
          danger
          @click="handleBatchDelete"
        >
          批量删除 ({{ selectedRowKeys.length }})
        </a-button>
      </div>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-bar">
      <div
        class="tab-item"
        :class="{ active: activeTab === 'audit' }"
        @click="activeTab = 'audit'"
      >
        <Icon icon="material-symbols:shield-person-outline" />
        HTTP审计日志
      </div>
      <div
        class="tab-item"
        :class="{ active: activeTab === 'trace' }"
        @click="switchToTrace"
      >
        <Icon icon="material-symbols:route" />
        交互链路追溯
      </div>
    </div>

    <!-- HTTP审计日志 视图 -->
    <div v-show="activeTab === 'audit'">

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-number">{{ auditStatistics.total_count || 0 }}</div>
        <div class="stat-label">总日志数</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ auditStatistics.today_count || 0 }}</div>
        <div class="stat-label">今日新增</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ auditStatistics.error_count || 0 }}</div>
        <div class="stat-label">错误日志</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ Math.round(auditStatistics.avg_duration || 0) }}ms</div>
        <div class="stat-label">平均耗时</div>
      </div>
    </div>

    <!-- 搜索筛选区域 -->
    <div class="search-section">
      <div class="search-left">
        <a-input
          v-model:value="searchParams.search"
          placeholder="搜索关键词、Trace ID..."
          allowClear
          @pressEnter="handleSearch"
          class="search-input"
        >
          <template #prefix>
            <Icon icon="material-symbols:search" />
          </template>
        </a-input>
        
        <a-select
          v-model:value="searchParams.operation_type"
          placeholder="操作类型"
          allowClear
          class="status-select"
        >
          <a-select-option v-for="type in auditTypes" :key="type.type" :value="type.type">
            {{ type.type }} - {{ type.description }}
          </a-select-option>
        </a-select>

        <a-select
          v-model:value="searchParams.target_type"
          placeholder="目标类型"
          allowClear
          class="type-select"
        >
          <a-select-option v-for="type in getUniqueTargetTypes" :key="type" :value="type">
            {{ type }}
          </a-select-option>
        </a-select>

        <a-select
          v-model:value="searchParams.status_code"
          placeholder="状态码"
          allowClear
          class="type-select"
        >
          <a-select-option :value="200">200 - 成功</a-select-option>
          <a-select-option :value="400">400 - 客户端错误</a-select-option>
          <a-select-option :value="401">401 - 未授权</a-select-option>
          <a-select-option :value="403">403 - 禁止访问</a-select-option>
          <a-select-option :value="404">404 - 未找到</a-select-option>
          <a-select-option :value="500">500 - 服务器错误</a-select-option>
        </a-select>

        <a-date-picker
          v-model:value="startTime"
          show-time
          placeholder="开始时间"
          format="YYYY-MM-DD HH:mm:ss"
          class="date-picker"
        />
        
        <a-date-picker
          v-model:value="endTime"
          show-time
          placeholder="结束时间"
          format="YYYY-MM-DD HH:mm:ss"
          class="date-picker"
        />
      </div>
      
      <div class="search-right">
        <a-button type="primary" @click="handleSearch">搜索</a-button>
        <a-button @click="handleReset">重置</a-button>
        <a-button @click="handleAdvancedSearch">高级搜索</a-button>
      </div>
    </div>

    <!-- 审计日志表格 -->
    <div class="table-container">
      <a-table
        :columns="tableColumns"
        :data-source="auditLogList"
        :pagination="paginationConfig"
        :loading="loading"
        row-key="id"
        size="middle"
        @change="handleTableChange"
        :row-selection="{
          selectedRowKeys: selectedRowKeys,
          onChange: onSelectChange,
        }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'time'">
            <div class="time-info">
              {{ formatTime(record.created_at) }}
            </div>
          </template>
          
          <template v-if="column.key === 'user'">
            <div class="user-info">
              <div class="user-id">{{ getUserDisplayName(record) }}</div>
              <div class="trace-id">{{ record.trace_id }}</div>
            </div>
          </template>
          
          <template v-if="column.key === 'operation'">
            <a-tag :color="getOperationColor(record.operation_type)">
              {{ record.operation_type }}
            </a-tag>
          </template>
          
          <template v-if="column.key === 'request'">
            <div class="request-info">
              <a-tag :color="getMethodColor(record.http_method)" class="method-tag">
                {{ record.http_method }}
              </a-tag>
              <div class="endpoint">{{ record.endpoint }}</div>
            </div>
          </template>
          
          <template v-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status_code)">
              {{ record.status_code }}
            </a-tag>
          </template>
          
          <template v-if="column.key === 'duration'">
            <span class="duration">{{ record.duration }}ms</span>
          </template>
          
          <template v-if="column.key === 'ip'">
            <span class="ip-address">{{ record.ip_address }}</span>
          </template>
          
          <template v-if="column.key === 'actions'">
            <div class="action-buttons">
              <a-button type="text" size="small" @click="handleView(record)">查看</a-button>
              <a-popconfirm title="确定要删除吗？" @confirm="handleDelete(record)">
                <a-button type="text" size="small" danger>删除</a-button>
              </a-popconfirm>
            </div>
          </template>
        </template>
      </a-table>
    </div>
    </div>

    <!-- 交互链路追溯 视图 -->
    <div v-show="activeTab === 'trace'">
      <div class="trace-toolbar">
        <a-input
          v-model:value="traceSearch"
          placeholder="搜索 Trace ID 或用户指令..."
          allowClear
          class="trace-search-input"
          @pressEnter="fetchTraces"
        >
          <template #prefix>
            <Icon icon="material-symbols:search" />
          </template>
        </a-input>
        <a-button type="primary" @click="fetchTraces" :loading="traceLoading">
          <Icon icon="material-symbols:refresh" />
          刷新
        </a-button>
      </div>

      <a-spin :spinning="traceLoading">
        <div v-if="filteredTraces.length === 0 && !traceLoading" class="trace-empty">
          <Icon icon="material-symbols:route" class="empty-icon" />
          <p>暂无推理链路数据</p>
        </div>

        <div class="trace-list">
          <div
            v-for="trace in filteredTraces"
            :key="trace.trace_id"
            class="trace-card"
            @click="openTraceDetail(trace)"
          >
            <div class="trace-card-header">
              <div class="trace-id-badge">
                <Icon icon="material-symbols:fingerprint" />
                <span class="trace-id-text">{{ trace.trace_id.slice(0, 8) }}...</span>
              </div>
              <span class="trace-time">{{ formatTime(trace.start_time) }}</span>
            </div>

            <div class="trace-card-body">
              <div class="trace-prompt">{{ truncatePrompt(trace.user_prompt) }}</div>
              <div class="trace-meta">
                <span class="trace-meta-item">
                  <Icon icon="material-symbols:footprint" />
                  {{ trace.steps?.length || 0 }} 步
                </span>
                <span class="trace-meta-item" v-if="trace.end_time">
                  <Icon icon="material-symbols:timer" />
                  {{ calcDuration(trace.start_time, trace.end_time) }}
                </span>
              </div>
            </div>

            <div class="trace-card-steps">
              <a-tag
                v-for="stepType in getUniqueStepTypes(trace.steps)"
                :key="stepType"
                :color="getStepColor(stepType)"
                class="step-tag"
              >
                {{ getStepLabel(stepType) }}
              </a-tag>
            </div>

            <div class="trace-card-footer">
              <a-button type="link" size="small" @click.stop="openTraceDetail(trace)">
                查看推理链
                <Icon icon="material-symbols:arrow-forward" />
              </a-button>
            </div>
          </div>
        </div>
      </a-spin>
    </div>

    <!-- 查看推理链详情 -->
    <a-modal v-model:open="traceDetailVisible" title="推理链路详情" width="960px" :footer="null">
      <div v-if="currentTrace" class="trace-detail">
        <div class="trace-detail-header">
          <div class="detail-item">
            <label>Trace ID</label>
            <span class="mono-text">{{ currentTrace.trace_id }}</span>
          </div>
          <div class="detail-item">
            <label>用户指令</label>
            <span>{{ currentTrace.user_prompt }}</span>
          </div>
          <div class="detail-item">
            <label>开始时间</label>
            <span>{{ formatTime(currentTrace.start_time) }}</span>
          </div>
          <div class="detail-item" v-if="currentTrace.end_time">
            <label>总耗时</label>
            <span class="mono-text">{{ calcDuration(currentTrace.start_time, currentTrace.end_time) }}</span>
          </div>
        </div>

        <div class="trace-chain-label">推理链路</div>
        <a-timeline class="trace-timeline">
          <a-timeline-item
            v-for="step in currentTrace.steps"
            :key="step.step_order"
            :color="getStepColor(step.step)"
          >
            <template #dot>
              <div class="timeline-dot" :class="getStepDotClass(step.step)">
                <Icon :icon="getStepIcon(step.step)" />
              </div>
            </template>
            <div class="timeline-content">
              <div class="timeline-header">
                <a-tag :color="getStepColor(step.step)" class="step-label-tag">
                  {{ getStepLabel(step.step) }}
                </a-tag>
                <span class="timeline-order">#{{ step.step_order }}</span>
                <span class="timeline-time">{{ formatTime(step.timestamp) }}</span>
              </div>
              <div class="timeline-data">
                <pre class="step-data-pre">{{ formatStepData(step.data) }}</pre>
              </div>
            </div>
          </a-timeline-item>
        </a-timeline>

        <div v-if="currentTrace.final_result" class="trace-final-result">
          <h4>最终结果</h4>
          <pre class="step-data-pre">{{ formatJSON(currentTrace.final_result) }}</pre>
        </div>
      </div>
    </a-modal>

    <!-- 查看审计日志详情 -->
    <a-modal v-model:open="viewModalVisible" title="审计日志详情" width="900px" :footer="null">
      <div v-if="viewLogData" class="log-detail">
        <div class="detail-section">
          <h3>基本信息</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>日志ID</label>
              <span>{{ viewLogData.id }}</span>
            </div>
            <div class="detail-item">
              <label>用户</label>
              <span>{{ viewLogData.user_info?.real_name || viewLogData.user_info?.username || `用户 ${viewLogData.user_id}` }}</span>
            </div>
            <div class="detail-item">
              <label>Trace ID</label>
              <span class="trace-id">{{ viewLogData.trace_id }}</span>
            </div>
            <div class="detail-item">
              <label>IP地址</label>
              <span>{{ viewLogData.ip_address }}</span>
            </div>
            <div class="detail-item">
              <label>操作类型</label>
              <a-tag :color="getOperationColor(viewLogData.operation_type)">
                {{ viewLogData.operation_type }}
              </a-tag>
            </div>
            <div class="detail-item">
              <label>目标类型</label>
              <span>{{ viewLogData.target_type || '-' }}</span>
            </div>
            <div class="detail-item">
              <label>目标ID</label>
              <span>{{ viewLogData.target_id || '-' }}</span>
            </div>
            <div class="detail-item">
              <label>操作时间</label>
              <span>{{ formatTime(viewLogData.created_at) }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h3>请求信息</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>请求方法</label>
              <a-tag :color="getMethodColor(viewLogData.http_method)">
                {{ viewLogData.http_method }}
              </a-tag>
            </div>
            <div class="detail-item">
              <label>请求路径</label>
              <span class="endpoint">{{ viewLogData.endpoint }}</span>
            </div>
            <div class="detail-item">
              <label>状态码</label>
              <a-tag :color="getStatusColor(viewLogData.status_code)">
                {{ viewLogData.status_code }}
              </a-tag>
            </div>
            <div class="detail-item">
              <label>响应时间</label>
              <span class="duration">{{ viewLogData.duration }}ms</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h3>User Agent</h3>
          <div class="code-content">
            <pre>{{ viewLogData.user_agent || '无数据' }}</pre>
          </div>
        </div>

        <div class="detail-section">
          <h3>请求体</h3>
          <div class="code-content">
            <pre>{{ formatJSON(viewLogData.request_body) }}</pre>
          </div>
        </div>

        <div class="detail-section">
          <h3>响应体</h3>
          <div class="code-content">
            <pre>{{ formatJSON(viewLogData.response_body) }}</pre>
          </div>
        </div>

        <div v-if="viewLogData.error_msg" class="detail-section error-section">
          <h3>错误信息</h3>
          <div class="code-content error-content">
            <pre>{{ viewLogData.error_msg }}</pre>
          </div>
        </div>
      </div>
    </a-modal>

    <!-- 高级搜索模态框 -->
    <a-modal 
      v-model:open="advancedSearchVisible" 
      title="高级搜索" 
      width="600px"
      @ok="handleAdvancedSearchSubmit"
    >
      <div class="advanced-search-form">
        <div class="form-item">
          <label>IP地址列表</label>
          <a-select
            v-model:value="advancedSearchParams.ip_address_list"
            mode="tags"
            placeholder="输入IP地址，支持多个"
            style="width: 100%"
          />
        </div>
        
        <div class="form-item">
          <label>状态码列表</label>
          <a-select
            v-model:value="advancedSearchParams.status_code_list"
            mode="multiple"
            placeholder="选择状态码"
            style="width: 100%"
          >
            <a-select-option :value="200">200</a-select-option>
            <a-select-option :value="400">400</a-select-option>
            <a-select-option :value="401">401</a-select-option>
            <a-select-option :value="403">403</a-select-option>
            <a-select-option :value="404">404</a-select-option>
            <a-select-option :value="500">500</a-select-option>
          </a-select>
        </div>
        
        <div class="form-row">
          <div class="form-item">
            <label>最小耗时(ms)</label>
            <a-input-number 
              v-model:value="advancedSearchParams.duration_min" 
              placeholder="最小耗时"
              style="width: 100%"
            />
          </div>
          <div class="form-item">
            <label>最大耗时(ms)</label>
            <a-input-number 
              v-model:value="advancedSearchParams.duration_max" 
              placeholder="最大耗时"
              style="width: 100%"
            />
          </div>
        </div>
        
        <div class="form-item">
          <label>接口路径模式</label>
          <a-input 
            v-model:value="advancedSearchParams.endpoint_pattern" 
            placeholder="如: /api/v1/users/*"
          />
        </div>
        
        <div class="form-item">
          <a-checkbox v-model:checked="advancedSearchParams.has_error">
            仅显示错误日志
          </a-checkbox>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { message } from 'ant-design-vue';
import { Icon } from '@iconify/vue';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';

import {
  listAuditLogsApi,
  getAuditLogDetailApi,
  searchAuditLogsApi,
  getAuditStatisticsApi,
  getAuditTypesApi,
  deleteAuditLogApi,
  batchDeleteLogsApi,
  type AuditLog,
  type AuditStatistics,
  type AuditTypeInfo,
  type ListAuditLogsRequest,
  type SearchAuditLogsRequest,
  type AdvancedSearchOptions
} from '#/api/core/system/audit';

import { getUserDetailApi } from '#/api/core/system/user';

import { getTraces, type Trace } from '#/api/core/aiops/agent';

// 扩展审计日志类型，包含用户信息
interface AuditLogWithUser extends AuditLog {
  user_info?: {
    id: number;
    username: string;
    real_name?: string;
    avatar?: string;
  };
}

// 表格列配置
const tableColumns = [
  { title: '时间', key: 'time', width: 150 },
  { title: '用户/Trace', key: 'user', width: 180 },
  { title: '操作类型', key: 'operation', width: 120, align: 'center' },
  { title: '请求信息', key: 'request', width: 200 },
  { title: '状态码', key: 'status', width: 80, align: 'center' },
  { title: '耗时', key: 'duration', width: 80, align: 'center' },
  { title: 'IP地址', key: 'ip', width: 120 },
  { title: '操作', key: 'actions', width: 120, fixed: 'right' }
];

// 状态管理
const loading = ref(false);
const viewModalVisible = ref(false);
const advancedSearchVisible = ref(false);

// Tab 切换 & 交互链路追溯
const activeTab = ref<'audit' | 'trace'>('audit');
const traceLoading = ref(false);
const traceList = ref<Trace[]>([]);
const traceSearch = ref('');
const traceDetailVisible = ref(false);
const currentTrace = ref<Trace | null>(null);

// 数据
const auditLogList = ref<AuditLogWithUser[]>([]);
const viewLogData = ref<AuditLogWithUser | null>(null);
const auditStatistics = ref<AuditStatistics>({
  total_count: 0,
  today_count: 0,
  error_count: 0,
  avg_duration: 0,
  type_distribution: [],
  status_distribution: [],
  recent_activity: [],
  hourly_trend: []
});
const auditTypes = ref<AuditTypeInfo[]>([]);

const selectedRowKeys = ref<number[]>([]);

// 用户信息缓存
const userInfoCache = ref<Map<number, any>>(new Map());

// 时间选择器
const startTime = ref<Dayjs>();
const endTime = ref<Dayjs>();

// 搜索参数
const searchParams = reactive({
  search: '',
  operation_type: undefined as string | undefined,
  target_type: undefined as string | undefined,
  status_code: undefined as number | undefined,
});

// 高级搜索参数
const advancedSearchParams = reactive<AdvancedSearchOptions>({
  ip_address_list: [],
  status_code_list: [],
  duration_min: undefined,
  duration_max: undefined,
  has_error: false,
  endpoint_pattern: ''
});

// 分页配置
const paginationConfig = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showQuickJumper: true,
  pageSizeOptions: ['10', '20', '50', '100'],
  showTotal: (total: number, range: [number, number]) => 
    `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
});

// 计算属性
const getUniqueTargetTypes = computed(() => {
  const types = new Set<string>();
  auditLogList.value.forEach(log => {
    if (log.target_type) {
      types.add(log.target_type);
    }
  });
  return Array.from(types);
});

const filteredTraces = computed(() => {
  if (!traceSearch.value) return traceList.value;
  const kw = traceSearch.value.toLowerCase();
  return traceList.value.filter(
    t =>
      t.trace_id.toLowerCase().includes(kw) ||
      t.user_prompt.toLowerCase().includes(kw),
  );
});

// 工具函数
const formatTime = (timestamp: string) => {
  if (!timestamp) return '-';
  return dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss');
};

const formatJSON = (obj: any) => {
  if (!obj) return '无数据';
  try {
    if (typeof obj === 'string') {
      return JSON.stringify(JSON.parse(obj), null, 2);
    }
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
};

// 获取用户信息
const getUserInfo = async (userId: number) => {
  // 检查缓存
  if (userInfoCache.value.has(userId)) {
    return userInfoCache.value.get(userId);
  }

  try {
    const userInfo = await getUserDetailApi(userId);
    // 缓存用户信息
    userInfoCache.value.set(userId, userInfo);
    return userInfo;
  } catch (error) {

    return null;
  }
};

// 获取用户显示名称
const getUserDisplayName = (log: AuditLogWithUser) => {
  if (log.user_info?.real_name) {
    return log.user_info.real_name;
  }
  if (log.user_info?.username) {
    return log.user_info.username;
  }
  return `用户 ${log.user_id}`;
};

const getOperationColor = (operation: string) => {
  const colorMap: Record<string, string> = {
    'CREATE': 'green',
    'UPDATE': 'blue',
    'DELETE': 'red',
    'VIEW': 'default',
    'LOGIN': 'purple',
    'LOGOUT': 'orange',
    'EXPORT': 'cyan',
    'IMPORT': 'gold'
  };
  return colorMap[operation] || 'default';
};

const getMethodColor = (method: string) => {
  const colorMap: Record<string, string> = {
    'GET': 'blue',
    'POST': 'green',
    'PUT': 'orange',
    'DELETE': 'red',
    'PATCH': 'cyan'
  };
  return colorMap[method] || 'default';
};

const getStatusColor = (status: number) => {
  if (status >= 200 && status < 300) return 'green';
  if (status >= 300 && status < 400) return 'blue';
  if (status >= 400 && status < 500) return 'orange';
  if (status >= 500) return 'red';
  return 'default';
};

// ---- 交互链路追溯方法 ----

/** 步骤类型 → 中文标签映射 */
const stepLabelMap: Record<string, string> = {
  INIT: '接收指令',
  ENVIRONMENT_SENSE: '环境感知',
  INTENT_ANALYSIS: '意图分析',
  SAFETY_VALIDATION: '安全校验',
  TOOL_EXECUTION: '工具执行',
  FINAL_DECISION: '最终决策',
};

/** 步骤类型 → 标签颜色 */
const stepColorMap: Record<string, string> = {
  INIT: 'default',
  ENVIRONMENT_SENSE: 'cyan',
  INTENT_ANALYSIS: 'blue',
  SAFETY_VALIDATION: 'orange',
  TOOL_EXECUTION: 'green',
  FINAL_DECISION: 'purple',
};

/** 步骤类型 → 图标 */
const stepIconMap: Record<string, string> = {
  INIT: 'material-symbols:input',
  ENVIRONMENT_SENSE: 'material-symbols:sensors',
  INTENT_ANALYSIS: 'material-symbols:psychology',
  SAFETY_VALIDATION: 'material-symbols:shield',
  TOOL_EXECUTION: 'material-symbols:build',
  FINAL_DECISION: 'material-symbols:check-circle',
};

const getStepLabel = (step: string) => stepLabelMap[step] || step;
const getStepColor = (step: string) => stepColorMap[step] || 'default';
const getStepIcon = (step: string) => stepIconMap[step] || 'material-symbols:help-outline';
const getStepDotClass = (step: string) => `dot-${step.toLowerCase().replace(/_/g, '-')}`;

/** 从步骤列表中提取去重的步骤类型（保持出现顺序） */
const getUniqueStepTypes = (steps?: Trace['steps']) => {
  if (!steps) return [];
  const seen = new Set<string>();
  return steps.reduce<string[]>((acc, s) => {
    if (!seen.has(s.step)) {
      seen.add(s.step);
      acc.push(s.step);
    }
    return acc;
  }, []);
};

/** 截断用户指令用于卡片展示 */
const truncatePrompt = (text: string, max = 80) =>
  text.length > max ? `${text.slice(0, max)}...` : text;

/** 计算耗时（毫秒/秒） */
const calcDuration = (start: string, end: string) => {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

/** 格式化步骤数据（精简输出） */
const formatStepData = (data: Record<string, any>) => {
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
};

/** 拉取推理链路列表 */
const fetchTraces = async () => {
  traceLoading.value = true;
  try {
    const res = await getTraces(100);
    traceList.value = res.traces || [];
  } catch (error: any) {
    message.error(error.message || '获取推理链路失败');
    traceList.value = [];
  } finally {
    traceLoading.value = false;
  }
};

/** 切换到 trace tab 时懒加载数据 */
const switchToTrace = () => {
  activeTab.value = 'trace';
  if (traceList.value.length === 0) {
    fetchTraces();
  }
};

/** 打开 trace 详情 */
const openTraceDetail = (trace: Trace) => {
  currentTrace.value = trace;
  traceDetailVisible.value = true;
};

// API 调用函数
const fetchAuditLogs = async () => {
  loading.value = true;
  try {
    const params: ListAuditLogsRequest = {
      page: paginationConfig.current,
      size: paginationConfig.pageSize
    };

    // 添加搜索条件
    if (searchParams.search) {
      params.search = searchParams.search;
    }
    if (searchParams.operation_type) {
      params.operation_type = searchParams.operation_type;
    }
    if (searchParams.target_type) {
      params.target_type = searchParams.target_type;
    }
    if (searchParams.status_code) {
      params.status_code = searchParams.status_code;
    }
    if (startTime.value) {
      params.start_time = startTime.value.unix();
    }
    if (endTime.value) {
      params.end_time = endTime.value.unix();
    }

    const response = await listAuditLogsApi(params);
    
    const logs = response.items || [];
    
    // 获取用户信息
    const logsWithUserInfo = await Promise.all(
      logs.map(async (log: AuditLog) => {
        const userInfo = await getUserInfo(log.user_id);
        return {
          ...log,
          user_info: userInfo
        } as AuditLogWithUser;
      })
    );
    
    auditLogList.value = logsWithUserInfo;
    paginationConfig.total = response.total || 0;
    
  } catch (error: any) {

    message.error(error.message || '获取审计日志失败');
    auditLogList.value = [];
    paginationConfig.total = 0;
  } finally {
    loading.value = false;
  }
};

const fetchAuditStatistics = async () => {
  try {
    const response = await getAuditStatisticsApi();
    auditStatistics.value = response;
  } catch (error: any) {

    message.error(error.message || '获取统计数据失败');
  }
};

const fetchAuditTypes = async () => {
  try {
    const response = await getAuditTypesApi();
    auditTypes.value = response;
  } catch (error: any) {

  }
};

const fetchLogDetail = async (id: number) => {
  try {
    const response = await getAuditLogDetailApi(id);
    const log = response as AuditLog;
    
    // 获取用户信息
    const userInfo = await getUserInfo(log.user_id);
    const logWithUserInfo = {
      ...log,
      user_info: userInfo
    } as AuditLogWithUser;
    
    viewLogData.value = logWithUserInfo;
    viewModalVisible.value = true;
  } catch (error: any) {

    message.error(error.message || '获取日志详情失败');
  }
};

// 高级搜索
const performAdvancedSearch = async () => {
  loading.value = true;
  try {
    const params: SearchAuditLogsRequest = {
      page: paginationConfig.current,
      size: paginationConfig.pageSize,
      advanced: { ...advancedSearchParams }
    };

    // 添加基础搜索条件
    if (searchParams.search) {
      params.search = searchParams.search;
    }
    if (searchParams.operation_type) {
      params.operation_type = searchParams.operation_type;
    }
    if (searchParams.target_type) {
      params.target_type = searchParams.target_type;
    }
    if (searchParams.status_code) {
      params.status_code = searchParams.status_code;
    }
    if (startTime.value) {
      params.start_time = startTime.value.unix();
    }
    if (endTime.value) {
      params.end_time = endTime.value.unix();
    }

    const response = await searchAuditLogsApi(params);
    
    const logs = response.items || [];
    
    // 获取用户信息
    const logsWithUserInfo = await Promise.all(
      logs.map(async (log: AuditLog) => {
        const userInfo = await getUserInfo(log.user_id);
        return {
          ...log,
          user_info: userInfo
        } as AuditLogWithUser;
      })
    );
    
    auditLogList.value = logsWithUserInfo;
    paginationConfig.total = response.total || 0;
    
  } catch (error: any) {

    message.error(error.message || '高级搜索失败');
    auditLogList.value = [];
    paginationConfig.total = 0;
  } finally {
    loading.value = false;
  }
};

// 事件处理
const handleSearch = () => {
  paginationConfig.current = 1;
  fetchAuditLogs();
};

const handleReset = () => {
  searchParams.search = '';
  searchParams.operation_type = undefined;
  searchParams.target_type = undefined;
  searchParams.status_code = undefined;
  startTime.value = undefined;
  endTime.value = undefined;
  
  // 重置高级搜索参数
  Object.assign(advancedSearchParams, {
    ip_address_list: [],
    status_code_list: [],
    duration_min: undefined,
    duration_max: undefined,
    has_error: false,
    endpoint_pattern: ''
  });
  
  paginationConfig.current = 1;
  fetchAuditLogs();
};

const handleRefresh = () => {
  fetchAuditLogs();
  fetchAuditStatistics();
};

const handleExport = () => {
  message.info('导出功能开发中...');
};

const handleAdvancedSearch = () => {
  advancedSearchVisible.value = true;
};

const handleAdvancedSearchSubmit = () => {
  advancedSearchVisible.value = false;
  paginationConfig.current = 1;
  performAdvancedSearch();
};

const handleTableChange = (pagination: any) => {
  paginationConfig.current = pagination.current;
  paginationConfig.pageSize = pagination.pageSize;
  fetchAuditLogs();
};

const handleView = (log: AuditLogWithUser) => {
  fetchLogDetail(log.id);
};

const handleDelete = async (log: AuditLogWithUser) => {
  try {
    await deleteAuditLogApi(log.id);
    message.success('删除成功');
    fetchAuditLogs();
    fetchAuditStatistics();
  } catch (error: any) {

    message.error(error.message || '删除失败');
  }
};

const handleBatchDelete = async () => {
  if (selectedRowKeys.value.length === 0) {
    message.warning('请选择要删除的日志');
    return;
  }

  try {
    await batchDeleteLogsApi({ ids: selectedRowKeys.value });
    message.success(`成功删除 ${selectedRowKeys.value.length} 条日志`);
    selectedRowKeys.value = [];
    fetchAuditLogs();
    fetchAuditStatistics();
  } catch (error: any) {

    message.error(error.message || '批量删除失败');
  }
};

const onSelectChange = (selectedKeys: number[]) => {
  selectedRowKeys.value = selectedKeys;
};

// 初始化
onMounted(() => {
  fetchAuditLogs();
  fetchAuditStatistics();
  fetchAuditTypes();
});
</script>

<style scoped>
/* 保持原有样式不变 */
.audit-log {
  padding: 20px;
  background: #f5f5f5;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  border: 1px solid #d9d9d9;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #262626;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.header-actions .ant-btn {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  border: 1px solid #d9d9d9;
}

.stat-number {
  font-size: 28px;
  font-weight: 600;
  color: #1890ff;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #8c8c8c;
}

.search-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 20px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  border: 1px solid #d9d9d9;
}

.search-left {
  display: flex;
  gap: 12px;
  flex: 1;
  align-items: flex-end;
}

.search-input {
  flex: 1;
  max-width: 300px;
}

.status-select,
.type-select {
  width: 140px;
}

.date-picker {
  width: 200px;
}

.search-right {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.table-container {
  background: white;
  border-radius: 8px;
  border: 1px solid #d9d9d9;
  overflow: hidden;
}

.table-container :deep(.ant-table-thead > tr > th) {
  background: #fafafa;
  font-weight: 600;
  color: #262626;
  border-bottom: 1px solid #e8e8e8;
}

.table-container :deep(.ant-table-tbody > tr > td) {
  font-size: 14px;
  color: #262626;
  line-height: 1.5;
}

.table-container :deep(.ant-table-tbody > tr:hover > td) {
  background: #f5f5f5;
}

/* 高级搜索表单样式 */
.advanced-search-form {
  padding: 16px 0;
}

.form-item {
  margin-bottom: 16px;
}

.form-item label {
  display: block;
  margin-bottom: 4px;
  font-weight: 600;
  color: #262626;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* 审计日志特有样式 */
.time-info {
  font-size: 13px;
  color: #262626;
  font-family: 'Courier New', monospace;
  font-weight: 500;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-id {
  font-weight: 600;
  color: #262626;
  font-size: 14px;
}

.trace-id {
  font-size: 12px;
  color: #595959;
  font-family: 'Courier New', monospace;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
}

.request-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.method-tag {
  align-self: flex-start;
  font-weight: 500;
}

.endpoint {
  font-size: 13px;
  color: #262626;
  font-family: 'Courier New', monospace;
  word-break: break-all;
}

.duration {
  font-family: 'Courier New', monospace;
  font-weight: 600;
  color: #262626;
  font-size: 14px;
}

.ip-address {
  font-family: 'Courier New', monospace;
  color: #262626;
  font-size: 14px;
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: 4px;
}

/* 详情模态框样式 */
.log-detail {
  padding: 8px 0;
}

.detail-section {
  margin-bottom: 24px;
}

.detail-section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #262626;
  padding-bottom: 8px;
  border-bottom: 1px solid #e8e8e8;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.detail-item {
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #e8e8e8;
}

.detail-item label {
  display: block;
  font-size: 12px;
  color: #8c8c8c;
  font-weight: 600;
  margin-bottom: 4px;
}

.detail-item span {
  font-size: 14px;
  color: #262626;
}

.detail-item .trace-id {
  font-family: 'Courier New', monospace;
  background: #f0f0f0;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.detail-item .endpoint {
  font-family: 'Courier New', monospace;
  background: #f0f0f0;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  word-break: break-all;
}

.detail-item .duration {
  font-family: 'Courier New', monospace;
  background: #f0f0f0;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.code-content {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 16px;
  max-height: 300px;
  overflow-y: auto;
}

.code-content pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #495057;
  white-space: pre-wrap;
  word-break: break-word;
}

.error-section h3 {
  color: #ff4d4f;
}

.error-content {
  background: #fff2f0;
  border-color: #ffccc7;
}

.error-content pre {
  color: #a8071a;
}

@media (max-width: 1200px) {
  .search-section {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
  }
  
  .search-left {
    flex-direction: column;
    gap: 12px;
  }
  
  .search-input {
    max-width: none;
  }
  
  .status-select,
  .type-select,
  .date-picker {
    width: 100%;
  }
  
  .search-right {
    justify-content: flex-end;
  }
}

@media (max-width: 768px) {
  .audit-log {
    padding: 12px;
  }
  
  .page-header {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
  
  .header-actions {
    width: 100%;
    justify-content: center;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .search-right {
    flex-direction: column;
    gap: 8px;
  }
  
  .detail-grid {
    grid-template-columns: 1fr;
  }
  
  .action-buttons {
    flex-direction: column;
    width: 100%;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
}

/* ===== Tab 切换栏 ===== */
.tab-bar {
  display: flex;
  gap: 0;
  margin-bottom: 20px;
  background: white;
  border-radius: 8px;
  border: 1px solid #d9d9d9;
  overflow: hidden;
}

.tab-item {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 24px;
  font-size: 15px;
  font-weight: 500;
  color: #595959;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.25s;
  user-select: none;
}

.tab-item:hover {
  background: #f5f7fa;
  color: #1890ff;
}

.tab-item.active {
  color: #1890ff;
  border-bottom-color: #1890ff;
  background: #f0f5ff;
}

/* ===== 交互链路追溯 - 工具栏 ===== */
.trace-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: white;
  border-radius: 8px;
  border: 1px solid #d9d9d9;
}

.trace-search-input {
  flex: 1;
  max-width: 420px;
}

/* ===== 空状态 ===== */
.trace-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  background: white;
  border-radius: 8px;
  border: 1px solid #d9d9d9;
  color: #8c8c8c;
}

.trace-empty .empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.4;
}

.trace-empty p {
  font-size: 15px;
  margin: 0;
}

/* ===== Trace 卡片列表 ===== */
.trace-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.trace-card {
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  padding: 18px 20px;
  cursor: pointer;
  transition: all 0.25s;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.trace-card:hover {
  border-color: #1890ff;
  box-shadow: 0 4px 16px rgba(24, 144, 255, 0.12);
  transform: translateY(-2px);
}

.trace-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trace-id-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #595959;
  background: #f5f5f5;
  padding: 3px 10px;
  border-radius: 4px;
}

.trace-id-text {
  letter-spacing: 0.5px;
}

.trace-time {
  font-size: 12px;
  color: #8c8c8c;
}

.trace-card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.trace-prompt {
  font-size: 14px;
  color: #262626;
  line-height: 1.6;
  word-break: break-word;
}

.trace-meta {
  display: flex;
  gap: 16px;
}

.trace-meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #8c8c8c;
}

.trace-card-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.step-tag {
  font-size: 12px;
  border-radius: 4px;
}

.trace-card-footer {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid #f0f0f0;
  padding-top: 8px;
  margin-top: 4px;
}

/* ===== Trace 详情 Modal ===== */
.trace-detail {
  padding: 8px 0;
}

.trace-detail-header {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

.trace-detail-header .detail-item {
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #e8e8e8;
}

.trace-detail-header .detail-item label {
  display: block;
  font-size: 12px;
  color: #8c8c8c;
  font-weight: 600;
  margin-bottom: 4px;
}

.trace-detail-header .detail-item span {
  font-size: 14px;
  color: #262626;
}

.mono-text {
  font-family: 'Courier New', monospace;
  word-break: break-all;
}

.trace-chain-label {
  font-size: 16px;
  font-weight: 600;
  color: #262626;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e8e8e8;
}

.trace-timeline {
  padding-left: 8px;
}

.timeline-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: white;
}

.dot-init {
  background: #8c8c8c;
}
.dot-environment-sense {
  background: #13c2c2;
}
.dot-intent-analysis {
  background: #1890ff;
}
.dot-safety-validation {
  background: #fa8c16;
}
.dot-tool-execution {
  background: #52c41a;
}
.dot-final-decision {
  background: #722ed1;
}

.timeline-content {
  padding-bottom: 16px;
}

.timeline-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.step-label-tag {
  font-weight: 500;
}

.timeline-order {
  font-size: 12px;
  color: #bfbfbf;
  font-family: 'Courier New', monospace;
}

.timeline-time {
  font-size: 12px;
  color: #8c8c8c;
  margin-left: auto;
}

.timeline-data {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 12px;
  max-height: 240px;
  overflow-y: auto;
}

.step-data-pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #495057;
  white-space: pre-wrap;
  word-break: break-word;
}

.trace-final-result {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e8e8e8;
}

.trace-final-result h4 {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 600;
  color: #262626;
}

.trace-final-result .step-data-pre {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 12px;
  max-height: 300px;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .trace-list {
    grid-template-columns: 1fr;
  }

  .trace-toolbar {
    flex-direction: column;
  }

  .trace-search-input {
    max-width: none;
  }

  .trace-detail-header {
    grid-template-columns: 1fr;
  }

  .tab-bar {
    flex-direction: column;
  }
}
</style>
