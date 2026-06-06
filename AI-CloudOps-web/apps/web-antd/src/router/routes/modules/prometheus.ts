import type { RouteRecordRaw } from 'vue-router';

import { BasicLayout } from '#/layouts';

const routes: RouteRecordRaw[] = [
  {
    component: BasicLayout,
    meta: {
      order: 2,
      title: 'Prometheus管理',
      icon: 'lucide:monitor',
    },
    name: 'Prometheus',
    path: '/prometheus',
    children: [
      {
        name: 'MonitorScrapePool',
        path: '/monitor_pool',
        component: () => import('#/views/prometheus/MonitorScrapePool.vue'),
        meta: {
          title: '采集池',
          icon: 'lucide:database',
        },
      },
      {
        name: 'MonitorScrapeJob',
        path: '/monitor_job',
        component: () => import('#/views/prometheus/MonitorScrapeJob.vue'),
        meta: {
          title: '采集任务',
          icon: 'lucide:list-check',
        },
      },
      {
        name: 'MonitorAlertPool',
        path: '/monitor_alert_pool',
        component: () => import('#/views/prometheus/MonitorAlertPool.vue'),
        meta: {
          title: 'alert告警池',
          icon: 'tabler:alert-circle-filled',
        },
      },

      {
        name: 'MonitorAlertRule',
        path: '/monitor_alert_rule',
        component: () => import('#/views/prometheus/MonitorAlertRule.vue'),
        meta: {
          title: '告警规则',
          icon: 'lucide:badge-alert',
        },
      },
      {
        name: 'MonitorAlertEvent',
        path: '/monitor_alert_event',
        component: () => import('#/views/prometheus/MonitorAlertEvent.vue'),
        meta: {
          title: '告警事件',
          icon: 'lucide:bell-ring',
        },
      },
      {
        name: 'MonitorAlertRecord',
        path: '/monitor_alert_record',
        component: () => import('#/views/prometheus/MonitorAlertRecord.vue'),
        meta: {
          title: '预聚合',
          icon: 'lucide:box',
        },
      },
      {
        name: 'MonitorConfig',
        path: '/monitor_config',
        component: () => import('#/views/prometheus/MonitorConfig.vue'),
        meta: {
          title: '配置文件',
          icon: 'lucide:file-text',
        },
      },
      {
        name: 'MonitorOnDutyGroup',
        path: '/monitor_onduty_group',
        component: () => import('#/views/prometheus/MonitorOnDutyGroup.vue'),
        meta: {
          title: '值班组',
          icon: 'lucide:user-round-minus',
        },
      },
      {
        name: 'MonitorOnDutyGroupTable',
        path: '/monitor_onduty_group_table',
        component: () =>
          import('#/views/prometheus/MonitorOnDutyGroupTable.vue'),
        meta: {
          hideInMenu: true,
          title: '排班表',
          icon: 'material-symbols:table-outline',
        },
      },
      {
        name: 'MonitorSend',
        path: '/monitor_send',
        component: () => import('#/views/prometheus/MonitorSend.vue'),
        meta: {
          title: '发送组',
          icon: 'lucide:send-horizontal',
        },
      },
    ],
  },
];

export default routes;
