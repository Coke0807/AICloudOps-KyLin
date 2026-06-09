import { requestClientAIOps } from '#/api/request';

/**
 * Agent 流式请求参数
 */
export interface AgentStreamRequest {
  prompt: string;
  session_id?: string | null;
}

/**
 * Agent 普通请求参数
 */
export interface AgentProcessRequest {
  prompt: string;
  session_id?: string | null;
}

/**
 * Agent 响应
 */
export interface AgentResponse {
  session_id: string;
  response: string;
  safety_report?: SafetyReport;
  blocked?: boolean;
  trace_id?: string;
  error?: string;
}

/**
 * 安全报告
 */
export interface SafetyReport {
  is_safe: boolean;
  overall_risk: string;
  layers: Record<string, any>;
}

/**
 * 流式响应块
 */
export interface StreamChunk {
  content?: string;
  reasoning?: string;
  status?: string;
  tools?: string[];
  done?: boolean;
  session_id?: string;
  trace_id?: string;
  safety_report?: SafetyReport;
  error?: string;
}

/**
 * 系统状态
 */
export interface SystemStatus {
  system_info: Record<string, any>;
  cpu: Record<string, any>;
  memory: Record<string, any>;
  disks: any[];
  processes: any[];
  network_connections: any[];
  uptime: Record<string, any>;
}

/**
 * 会话
 */
export interface Session {
  id: string;
  title: string;
  message_count: number;
  preview?: string;
  created_at: string;
  updated_at: string;
}

/**
 * 消息
 */
export interface ToolDetail {
  name: string;
  args?: Record<string, any>;
  result?: any;
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  trace_id?: string;
  safety_report?: SafetyReport;
  timestamp: string;
  // 前端扩展字段（运行时动态添加）
  reasoning?: string;
  toolStatus?: string;
  toolDetails?: ToolDetail[];
  traceId?: string;
  safetyReport?: SafetyReport;
  _expanded?: boolean;
}

/**
 * 推理链路
 */
export interface Trace {
  trace_id: string;
  start_time: string;
  end_time?: string;
  user_prompt: string;
  steps: TraceStep[];
  final_result?: Record<string, any>;
}

/**
 * 推理步骤
 */
export interface TraceStep {
  trace_id: string;
  timestamp: string;
  step: string;
  step_order: number;
  data: Record<string, any>;
}

/**
 * 安全事件
 */
export interface SafetyEvent {
  id: number;
  trace_id: string;
  step: string;
  data: Record<string, any>;
  is_safe: boolean;
  risk_level: string;
  created_at: string;
}

/**
 * 发送Agent普通请求
 */
export async function agentProcess(data: AgentProcessRequest): Promise<AgentResponse> {
  return requestClientAIOps.post('/agent/process', data);
}

/**
 * 发送Agent流式请求（返回原生Response，供SSE解析）
 */
export async function agentStream(data: AgentStreamRequest): Promise<Response> {
  return fetch('/api/v1/agent/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

/**
 * 获取系统状态
 */
export async function getSystemStatus(): Promise<{ data: SystemStatus }> {
  return requestClientAIOps.get('/system/status');
}

/**
 * 获取进程列表
 */
export async function getProcesses(limit = 20): Promise<{ data: any[] }> {
  return requestClientAIOps.get('/system/processes', { params: { limit } });
}

/**
 * 获取磁盘信息
 */
export async function getDisks(): Promise<{ data: any[] }> {
  return requestClientAIOps.get('/system/disks');
}

/**
 * 获取工具列表
 */
export async function getTools(): Promise<any> {
  return requestClientAIOps.get('/tools');
}

/**
 * 执行工具
 */
export async function executeTool(toolName: string, params?: Record<string, any>): Promise<any> {
  return requestClientAIOps.post('/tools/execute', { tool_name: toolName, params });
}

/**
 * 获取会话列表
 */
export async function getSessions(limit = 50): Promise<{ sessions: Session[] }> {
  return requestClientAIOps.get('/history', { params: { limit } });
}

/**
 * 获取会话消息
 */
export async function getSessionMessages(sessionId: string): Promise<{ messages: ChatMessage[] }> {
  return requestClientAIOps.get(`/history/${sessionId}`);
}

/**
 * 删除会话
 */
export async function deleteSession(sessionId: string): Promise<{ success: boolean }> {
  return requestClientAIOps.delete(`/history/${sessionId}`);
}

/**
 * 获取推理链路列表
 */
export async function getTraces(limit = 50): Promise<{ traces: Trace[] }> {
  return requestClientAIOps.get('/traces', { params: { limit } });
}

/**
 * 获取推理链路详情
 */
export async function getTrace(traceId: string): Promise<{ trace: Trace }> {
  return requestClientAIOps.get(`/traces/${traceId}`);
}

/**
 * 获取安全统计
 */
export async function getSafetyStats(): Promise<{
  total_checks: number;
  blocked_count: number;
  passed_count: number;
  block_rate: number;
  risk_distribution: Record<string, number>;
}> {
  return requestClientAIOps.get('/safety/stats');
}

/**
 * 获取安全事件
 */
export async function getSafetyEvents(limit = 100): Promise<{ events: SafetyEvent[]; total: number }> {
  return requestClientAIOps.get('/safety/events', { params: { limit } });
}

/**
 * 获取RBAC角色
 */
export async function getRbacRoles(): Promise<any> {
  return requestClientAIOps.get('/security/rbac/roles');
}

/**
 * 获取沙箱状态
 */
export async function getSandboxStatus(): Promise<any> {
  return requestClientAIOps.get('/security/sandbox/status');
}

/**
 * 获取备份列表
 */
export async function getBackups(): Promise<any> {
  return requestClientAIOps.get('/security/backups');
}

// ============================================================
// 知识库管理 API
// ============================================================

export interface KnowledgeDocument {
  id: string;
  title: string;
  file_name: string;
  content: string;
  created_at: string;
  updated_at: string;
  status: string;
}

/**
 * 刷新知识库
 */
export async function refreshKnowledgeBase(): Promise<{
  refreshed: boolean;
  documents_count: number;
  vector_count: number;
  timestamp: string;
  message: string;
}> {
  return requestClientAIOps.post('/assistant/refresh');
}

/**
 * 上传知识库文件
 */
export async function uploadKnowledgeFile(): Promise<{
  uploaded: boolean;
  document_id: string;
  filename: string;
  file_size: number;
  message: string;
  timestamp: string;
}> {
  return requestClientAIOps.post('/assistant/upload-knowledge-file');
}

/**
 * 手动添加文档
 */
export async function addKnowledgeDocument(data?: {
  title?: string;
  file_name?: string;
  content?: string;
}): Promise<{
  added: boolean;
  document_id: string;
  message: string;
  timestamp: string;
}> {
  return requestClientAIOps.post('/assistant/add-document', data || {});
}
