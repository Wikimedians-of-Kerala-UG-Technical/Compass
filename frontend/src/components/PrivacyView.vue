<script setup>
import { RouterLink } from 'vue-router'

// Plain statements of what Compass reads and keeps. Keep this in step with the code:
// store.py (votes, sessions), auth_service.py (login), profile_service.opted_out.
const sections = ['reads', 'login', 'stored', 'browser', 'logs', 'optOut', 'contact']
</script>

<template>
  <div class="page">
    <RouterLink :to="{ name: 'onboard' }" class="back">{{ $t('privacy.back') }}</RouterLink>
    <h1 class="section-heading">{{ $t('privacy.title') }}</h1>
    <p class="section-sub">{{ $t('privacy.intro') }}</p>
    <section v-for="s in sections" :key="s" class="panel privacy-section">
      <h2 class="section-title">{{ $t(`privacy.${s}`) }}</h2>
      <p>{{ $t(`privacy.${s}Body`, { page: 'User:<your name>/Compass-opt-out' }) }}</p>
    </section>
  </div>
</template>

<style scoped>
.page { max-width: 720px; margin: 0 auto; padding: 32px 16px; }
.back { display: inline-block; margin-bottom: 12px; font-size: 0.875rem; }
.privacy-section { margin-bottom: 12px; }
.privacy-section p { font-size: 0.875rem; line-height: 1.6; margin: 0; }
</style>
