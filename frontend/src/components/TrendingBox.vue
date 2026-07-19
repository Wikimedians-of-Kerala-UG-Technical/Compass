<script setup>
import { computed } from 'vue'

const props = defineProps({
  trending: { type: Array, default: () => [] },
})

function wikiHref(title) {
  return 'https://en.wikipedia.org/wiki/' + encodeURIComponent((title || '').replace(/ /g, '_'))
}

function shortLabel(title) {
  const t = title || ''
  return t.length > 32 ? t.slice(0, 30) + '…' : t
}

const items = computed(() => (props.trending || []).slice(0, 15))
</script>

<template>
  <section class="wtp-card" aria-label="Trending articles">
    <template v-if="items.length">
      <div class="trending-title">📈 Trending Now</div>
      <div class="trend-pills fade-in">
        <a
          v-for="(t, i) in items"
          :key="i"
          class="trend-pill"
          :href="wikiHref(t.title)"
          target="_blank"
          rel="noopener"
        >
          {{ shortLabel(t.title) }}
          <span v-if="t.views" class="trend-pill__views">{{ Math.round(t.views / 1000) }}k</span>
        </a>
      </div>
    </template>
    <div v-else class="empty-state">
      <div class="empty-state__icon">📈</div>
      No trending data
    </div>
  </section>
</template>
