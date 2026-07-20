<script setup>
import { CdxProgressBar } from '@wikimedia/codex'

defineProps({
  title: { type: String, required: true },
  sub: { type: String, default: '' },
})
</script>

<template>
  <div class="loading-state fade-in">
    <CdxProgressBar aria-label="Loading" />
    <div class="loading-state__title">{{ title }}</div>
    <div v-if="sub" class="loading-state__sub">{{ sub }}</div>
  </div>
</template>
