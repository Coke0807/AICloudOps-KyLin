<script lang="ts" setup>
import { AuthenticationLogin } from '@vben/common-ui';

import { useAuthStore } from '#/store';

defineOptions({ name: 'Login' });

const authStore = useAuthStore();
</script>

<template>
  <AuthenticationLogin
    :loading="authStore.loginLoading"
    password-placeholder="admin"
    username-placeholder="admin"
    title="欢迎回来 👋🏻"
    sub-title="使用您的账户登录 AICloudOps 平台"
    @submit="authStore.authLogin"
  />
</template>
