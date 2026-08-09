<script setup>
import { computed } from 'vue'
import { CdxIcon, CdxInfoChip } from '@wikimedia/codex'
import { cdxIconNewspaper } from '@wikimedia/codex-icons'
import { useAppStore } from '../../stores/appStore.js'

const store = useAppStore()

const SRC_LABEL = {
  current_events: 'Current Events',
  recent_deaths: 'Recent Deaths',
  ongoing: 'Ongoing',
  dyk: 'Did You Know',
  wiki_trending: 'Trending',
}

function wikiHref(title) {
  return 'https://en.wikipedia.org/wiki/' + encodeURIComponent((title || '').replace(/ /g, '_'))
}

const items = computed(() => (store.trends.news || []).slice(0, 4))
</script>

<template>
  <section class="panel" aria-label="Current events">
    <div class="section-title" style="display:flex; align-items:center; gap:6px">
      <CdxIcon :icon="cdxIconNewspaper" size="small" />
      Today's news
    </div>

    <div v-if="store.trendsLoading" class="fade-in">
      <div class="skeleton-line skeleton-line--wide"></div>
      <div class="skeleton-line skeleton-line--narrow"></div>
      <div class="skeleton-line"></div>
    </div>

    <div v-else-if="items.length" style="display:flex; flex-direction:column; gap:12px">
      <div v-for="(ni, i) in items" :key="i" style="border-left: 3px solid var(--border-color-base); padding: 4px 10px">
        <div style="font-size: 0.8125rem; margin-bottom: 4px">{{ ni.text }}</div>
        <CdxInfoChip status="subtle">{{ SRC_LABEL[ni.source] || 'News' }}</CdxInfoChip>
        <a
          v-for="a in (ni.articles || []).slice(0, 3)"
          :key="a"
          :href="wikiHref(a)"
          target="_blank"
          rel="noopener"
          style="font-size: 0.75rem; margin-left: 6px"
        >{{ a }}</a>
      </div>
    </div>

    <div v-else class="empty-state">No news data.</div>
  </section>
</template>
