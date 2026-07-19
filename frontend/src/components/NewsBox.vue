<script setup>
import { computed } from 'vue'

const props = defineProps({
  news: { type: Array, default: () => [] },
})

const SRC_LABEL = {
  current_events: 'Current Events',
  recent_deaths: 'Recent Deaths',
  ongoing: 'Ongoing',
  dyk: 'Did You Know',
  wiki_trending: 'Trending',
}
const SRC_ICON = {
  current_events: '📰',
  recent_deaths: '🕊️',
  ongoing: '🔴',
  dyk: '💡',
  wiki_trending: '📈',
}

function wikiHref(title) {
  return 'https://en.wikipedia.org/wiki/' + encodeURIComponent((title || '').replace(/ /g, '_'))
}

const items = computed(() => (props.news || []).slice(0, 5))
</script>

<template>
  <section class="wtp-card" aria-label="Current events">
    <template v-if="items.length">
      <div class="news-title">📰 Today's News</div>
      <div class="news-items fade-in">
        <div v-for="(ni, i) in items" :key="i" class="news-item">
          <div class="news-item__text">{{ ni.text }}</div>
          <div class="news-item__source">
            <span class="wtp-badge wtp-badge--neutral">
              {{ SRC_ICON[ni.source] || '📰' }} {{ SRC_LABEL[ni.source] || 'News' }}
            </span>
          </div>
          <div v-if="(ni.articles || []).length" class="news-item__articles">
            <a
              v-for="a in ni.articles.slice(0, 4)"
              :key="a"
              class="news-item__art"
              :href="wikiHref(a)"
              target="_blank"
              rel="noopener"
            >{{ a }}</a>
          </div>
        </div>
      </div>
    </template>
    <div v-else class="empty-state">
      <div class="empty-state__icon">📰</div>
      No news data
    </div>
  </section>
</template>
