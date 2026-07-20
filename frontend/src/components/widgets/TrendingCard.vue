<script setup>
import { computed } from 'vue'
import { CdxIcon } from '@wikimedia/codex'
import { cdxIconChartLine } from '@wikimedia/codex-icons'
import { useAppStore } from '../../stores/appStore.js'

const store = useAppStore()

function wikiHref(title) {
  return 'https://en.wikipedia.org/wiki/' + encodeURIComponent((title || '').replace(/ /g, '_'))
}
function shortLabel(title) {
  const t = title || ''
  return t.length > 32 ? t.slice(0, 30) + '…' : t
}

const items = computed(() => (store.trends.trending || []).slice(0, 12))
</script>

<template>
  <section class="panel" aria-label="Trending articles">
    <div class="section-title" style="display:flex; align-items:center; gap:6px">
      <CdxIcon :icon="cdxIconChartLine" size="small" />
      Trending now
    </div>

    <div v-if="store.trendsLoading" class="fade-in">
      <div class="skeleton-line skeleton-line--wide"></div>
      <div class="skeleton-line skeleton-line--narrow"></div>
      <div class="skeleton-line"></div>
    </div>

    <div v-else-if="items.length" class="chip-row" style="margin-bottom: 0">
      <a
        v-for="(t, i) in items"
        :key="i"
        :href="wikiHref(t.title)"
        target="_blank"
        rel="noopener"
        class="cdx-info-chip"
        style="text-decoration: none"
      >
        {{ shortLabel(t.title) }}
        <template v-if="t.views">&nbsp;· {{ Math.round(t.views / 1000) }}k</template>
      </a>
    </div>

    <div v-else class="empty-state">No trending data.</div>
  </section>
</template>
