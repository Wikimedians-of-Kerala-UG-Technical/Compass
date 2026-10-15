<script setup>
import { CdxProgressBar } from '@wikimedia/codex'
import { useAppStore } from '../stores/appStore.js'

const store = useAppStore()
</script>

<template>
  <div class="loading-screen" role="main" aria-live="polite">
    <div class="loading-screen__card">
      <CdxProgressBar :aria-label="$t('app.loading')" />
      <h2 class="loading-screen__title">{{ $t('loading.title', { name: store.username }) }}</h2>
      <p class="loading-screen__sub">{{ $t('loading.sub') }}</p>
    </div>
  </div>
</template>
