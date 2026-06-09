import type { RouteRecordRaw } from 'vue-router';

import { BasicLayout } from '#/layouts';

const routes: RouteRecordRaw[] = [
  {
    component: BasicLayout,
    meta: {
      icon: 'lucide:album',
      order: 20,
      title: '智能助手',
    },
    name: 'Assistant',
    path: '/assistant',
    redirect: '/assistant/query',
    children: [
      {
        name: 'AssistantQuery',
        path: '/assistant/query',
        component: () => import('#/views/assistant/AssistantQuery.vue'),
        meta: {
          icon: 'lucide:message-square',
          title: '智能问答',
        },
      },
      {
        name: 'AssistantSession',
        path: '/assistant/session',
        component: () => import('#/views/assistant/AssistantSession.vue'),
        meta: {
          icon: 'lucide:users',
          title: '会话管理',
        },
      },
      {
        name: 'SafetyGuardrail',
        path: '/assistant/safety',
        component: () => import('#/views/assistant/SafetyGuardrail.vue'),
        meta: {
          icon: 'lucide:shield-check',
          title: '安全护栏',
        },
      },
      {
        name: 'ReasoningChain',
        path: '/assistant/reasoning',
        component: () => import('#/views/assistant/ReasoningChain.vue'),
        meta: {
          icon: 'lucide:git-branch',
          title: '推理链路',
        },
      },
      {
        name: 'InterceptionLog',
        path: '/assistant/interception',
        component: () => import('#/views/assistant/InterceptionLog.vue'),
        meta: {
          icon: 'lucide:shield-off',
          title: '拦截记录',
        },
      },
      {
        name: 'AssistantKnowledge',
        path: '/assistant/knowledge',
        component: () => import('#/views/assistant/AssistantKnowledge.vue'),
        meta: {
          icon: 'lucide:book',
          title: '知识库管理',
        },
      },
      {
        name: 'AssistantInfo',
        path: '/assistant/info',
        component: () => import('#/views/assistant/AssistantInfo.vue'),
        meta: {
          icon: 'lucide:info',
          title: '服务信息',
        },
      },
      {
        name: 'ArchitectureView',
        path: '/assistant/architecture',
        component: () => import('#/views/assistant/ArchitectureView.vue'),
        meta: {
          icon: 'lucide:layout-dashboard',
          title: '系统架构',
        },
      },
    ],
  },
];

export default routes;
