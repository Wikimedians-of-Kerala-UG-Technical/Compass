<script setup>
import { ref, computed } from 'vue'
import { getDiscover } from '../api.js'

const props = defineProps({
  username: { type: String, required: true },
})

const loading = ref(false)
const loaded = ref(false)
const errorMsg = ref('')
const data = ref(null)
const sortMode = ref('weight')

const sortOptions = [
  { key: 'weight', label: 'By relevance' },
  { key: 'category', label: 'By category' },
  { key: 'missing', label: 'By languages missing' },
]

function find() {
  loading.value = true
  errorMsg.value = ''
  getDiscover(props.username)
    .then((d) => {
      data.value = d
      loaded.value = true
    })
    .catch((err) => {
      errorMsg.value = err.message || 'Failed to load suggestions.'
    })
    .finally(() => {
      loading.value = false
    })
}

const suggestions = computed(() => data.value?.suggestedArticles || [])
const userWikis = computed(() => data.value?.userWikis || [])

const flatSorted = computed(() => {
  const list = [...suggestions.value]
  if (sortMode.value === 'missing') {
    return list.sort((a, b) => b.missingIn.length - a.missingIn.length || b.categoryWeight - a.categoryWeight)
  }
  return list.sort((a, b) => b.categoryWeight - a.categoryWeight)
})

const grouped = computed(() => {
  const groups = new Map()
  for (const article of suggestions.value) {
    if (!groups.has(article.fromCategory)) {
      groups.set(article.fromCategory, { name: article.fromCategory, weight: article.categoryWeight, items: [] })
    }
    groups.get(article.fromCategory).items.push(article)
  }
  return [...groups.values()].sort((a, b) => b.weight - a.weight)
})

function wikiUrl(title) {
  return 'https://en.wikipedia.org/wiki/' + encodeURIComponent((title || '').replace(/ /g, '_'))
}
function createUrl(wiki, title) {
  return wiki.url + '/wiki/' + encodeURIComponent((title || '').replace(/ /g, '_'))
}
</script>

<template>
  <section class="wtp-card dash-main__discover">
    <div class="wtp-card__header">
      <h3 class="wtp-card__heading">
        Discover New Articles
        <span v-if="suggestions.length" class="wtp-badge wtp-badge--neutral">({{ suggestions.length }})</span>
      </h3>
      <p class="wtp-card__sub">
        Articles from your top topics that don't exist yet in one of your other languages — a chance to write
        something genuinely new.
      </p>
    </div>

    <div v-if="!loaded && !loading" class="empty-state">
      <div class="empty-state__icon">🧭</div>
      <p style="margin-bottom: 12px">This scans your last 1000 edits and can take a minute or two.</p>
      <button class="cdx-button cdx-button--action-progressive cdx-button--weight-primary" @click="find">
        Find suggestions
      </button>
    </div>

    <div v-else-if="loading" style="display: flex; align-items: center; gap: 10px; padding: 16px; color: #54595d">
      <div class="loading-card__spinner" style="width: 24px; height: 24px; border-width: 2px; flex-shrink: 0"></div>
      Scanning your edits, categories, and languages…
    </div>

    <div v-else-if="errorMsg" class="cdx-message cdx-message--error" style="margin-top: 8px">
      <span class="cdx-message__icon"></span>
      <div class="cdx-message__content">{{ errorMsg }}</div>
      <button class="cdx-button" style="margin-top: 8px" @click="find">Try again</button>
    </div>

    <template v-else>
      <div v-if="userWikis.length" class="profile-tags" style="margin-bottom: 16px">
        <span v-for="w in userWikis" :key="w.dbname" class="wtp-badge wtp-badge--notice">
          {{ w.lang }} <strong>({{ w.editcount.toLocaleString() }} edits)</strong>
        </span>
      </div>

      <div v-if="!suggestions.length" class="empty-state">
        <div class="empty-state__icon">✅</div>
        No language gaps found in your top topics right now.
      </div>

      <template v-else>
        <div class="dash-task-filters" style="margin-bottom: 12px">
          <button
            v-for="opt in sortOptions"
            :key="opt.key"
            class="cdx-button cdx-button--size-medium filter-btn"
            :class="{ 'filter-btn--active': sortMode === opt.key }"
            @click="sortMode = opt.key"
          >
            {{ opt.label }}
          </button>
        </div>

        <template v-if="sortMode === 'category'">
          <div v-for="group in grouped" :key="group.name">
            <div class="guide-col-title" style="margin-top: 16px">{{ group.name }} (weight {{ group.weight }})</div>
            <div
              v-for="article in group.items"
              :key="article.qid"
              class="task-item"
              style="border-left-color: #14866d"
            >
              <div class="task-item__head">
                <span class="task-item__title">
                  <a :href="wikiUrl(article.title)" target="_blank" rel="noopener">{{ article.title }}</a>
                </span>
              </div>
              <div class="task-item__actions" style="flex-wrap: wrap; gap: 4px">
                <span v-for="w in article.existsIn" :key="w" class="wtp-badge wtp-badge--success">{{ w }}</span>
                <a
                  v-for="w in article.missingIn"
                  :key="w.dbname"
                  :href="createUrl(w, article.title)"
                  target="_blank"
                  rel="noopener"
                  class="wtp-badge wtp-badge--error"
                  style="text-decoration: none"
                >
                  Write in {{ w.dbname }}
                </a>
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <div
            v-for="article in flatSorted"
            :key="article.qid"
            class="task-item"
            style="border-left-color: #14866d"
          >
            <div class="task-item__head">
              <span class="task-item__title">
                <a :href="wikiUrl(article.title)" target="_blank" rel="noopener">{{ article.title }}</a>
              </span>
              <span class="wtp-badge wtp-badge--notice">{{ article.fromCategory }}</span>
            </div>
            <div class="task-item__actions" style="flex-wrap: wrap; gap: 4px">
              <span v-for="w in article.existsIn" :key="w" class="wtp-badge wtp-badge--success">{{ w }}</span>
              <a
                v-for="w in article.missingIn"
                :key="w.dbname"
                :href="createUrl(w, article.title)"
                target="_blank"
                rel="noopener"
                class="wtp-badge wtp-badge--error"
                style="text-decoration: none"
              >
                Write in {{ w.dbname }}
              </a>
            </div>
          </div>
        </template>
      </template>
    </template>
  </section>
</template>
