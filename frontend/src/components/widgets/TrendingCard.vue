<script setup>
import { computed } from 'vue'
import { CdxIcon, CdxInfoChip } from '@wikimedia/codex'
import { cdxIconChartLine } from '@wikimedia/codex-icons'
import { useAppStore } from '../../stores/appStore.js'

const store = useAppStore()

const items = computed(() => (store.trends.trending || []).slice(0, 8))
const where = computed(() => {
  const country = store.profile?.countries?.[0]?.name
  const wiki = store.profile?.homeLang
  return [country && `readers in ${country}`, wiki && `${wiki}.wikipedia`].filter(Boolean).join(' and ')
})

function views(n) {
  return n >= 1000 ? Math.round(n / 1000) + 'k' : n
}
</script>

<template>
  <section class="panel" aria-label="Trending articles that need work">
    <div class="section-title" style="display: flex; align-items: center; gap: 6px">
      <CdxIcon :icon="cdxIconChartLine" size="small" />
      Read today, needs work
    </div>
    <p v-if="where" style="font-size: 0.75rem; color: var(--color-subtle); margin-bottom: 8px">
      Most-read yesterday by {{ where }}, that also carry a maintenance tag.
    </p>

    <div v-if="store.trendsLoading" class="fade-in">
      <div class="skeleton-line skeleton-line--wide"></div>
      <div class="skeleton-line skeleton-line--narrow"></div>
      <div class="skeleton-line"></div>
    </div>

    <div v-else-if="items.length" style="display: flex; flex-direction: column; gap: 8px">
      <div v-for="t in items" :key="t.wiki + t.title" style="font-size: 0.8125rem">
        <a :href="t.editUrl" target="_blank" rel="noopener">{{ t.title }}</a>
        <span style="color: var(--color-subtle)"> · {{ views(t.views) }} views<template v-if="t.wiki !== 'enwiki'"> · {{ t.wiki.replace(/wiki$/, '') }}</template></span>
        <div style="margin-top: 2px">
          <CdxInfoChip v-for="i in t.issues" :key="i.key" status="warning" style="margin-right: 4px">{{ i.label }}</CdxInfoChip>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">No trending articles that need work right now.</div>
  </section>
</template>
