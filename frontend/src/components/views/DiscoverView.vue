<script setup>
import { ref, computed } from 'vue'
import { CdxToggleButtonGroup, CdxInfoChip, CdxButton, CdxIcon, CdxMessage } from '@wikimedia/codex'
import { cdxIconReload } from '@wikimedia/codex-icons'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()

const sortButtons = [
  { value: 'weight', label: 'By relevance' },
  { value: 'category', label: 'By category' },
  { value: 'missing', label: 'By languages missing' },
]
const sortMode = ref('weight')

const suggestions = computed(() => store.discover?.suggestedArticles || [])
const userWikis = computed(() => store.discover?.userWikis || [])

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
  <div>
    <div class="item-card__head" style="align-items: flex-start; margin-bottom: 4px">
      <div>
        <h1 class="section-heading">Discover new articles</h1>
        <p class="section-sub" style="margin-bottom: 0">
          Articles from your top topics that don't exist yet in one of your other languages.
        </p>
      </div>
      <CdxButton weight="quiet" :disabled="store.discoverLoading" @click="store.fetchDiscover()">
        <CdxIcon :icon="cdxIconReload" />
        {{ store.discoverLoading ? 'Scanning…' : 'Rescan' }}
      </CdxButton>
    </div>

    <p v-if="store.discoverLoading && store.discover" class="section-sub" style="margin-bottom: 16px">
      Rescanning — this can take a minute or two. Showing your last results below until it's done.
    </p>

    <LoadingState
      v-if="store.discoverLoading && !store.discover"
      title="Scanning your edits, categories, and languages…"
      sub="Expanding your top categories into candidate articles and checking each one against your languages. This can take a minute or two."
    />

    <CdxMessage v-else-if="store.discoverError" type="error" style="margin: 16px 0">
      {{ store.discoverError }}
    </CdxMessage>

    <template v-else>
      <div v-if="userWikis.length" class="chip-row">
        <CdxInfoChip v-for="w in userWikis" :key="w.dbname" status="progressive">
          {{ w.lang }} · {{ w.editcount.toLocaleString() }} edits
        </CdxInfoChip>
      </div>

      <div v-if="!suggestions.length" class="empty-state">
        No language gaps found in your top topics right now.
      </div>

      <template v-else>
        <CdxToggleButtonGroup v-model="sortMode" :buttons="sortButtons" style="margin-bottom: 16px" />

        <template v-if="sortMode === 'category'">
          <div v-for="group in grouped" :key="group.name">
            <div class="group-heading">{{ group.name }} (weight {{ group.weight }})</div>
            <div v-for="article in group.items" :key="article.qid" class="item-card">
              <div class="item-card__head">
                <span class="item-card__title">
                  <a :href="wikiUrl(article.title)" target="_blank" rel="noopener">{{ article.title }}</a>
                </span>
              </div>
              <div class="item-card__row">
                <CdxInfoChip v-for="w in article.existsIn" :key="w" status="success">{{ w }}</CdxInfoChip>
                <a
                  v-for="w in article.missingIn"
                  :key="w.dbname"
                  :href="createUrl(w, article.title)"
                  target="_blank"
                  rel="noopener"
                  class="cdx-info-chip cdx-info-chip--error"
                  style="text-decoration: none"
                >
                  Write in {{ w.dbname }}
                </a>
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <div v-for="article in flatSorted" :key="article.qid" class="item-card">
            <div class="item-card__head">
              <span class="item-card__title">
                <a :href="wikiUrl(article.title)" target="_blank" rel="noopener">{{ article.title }}</a>
              </span>
              <CdxInfoChip status="notice">{{ article.fromCategory }}</CdxInfoChip>
            </div>
            <div class="item-card__row">
              <CdxInfoChip v-for="w in article.existsIn" :key="w" status="success">{{ w }}</CdxInfoChip>
              <a
                v-for="w in article.missingIn"
                :key="w.dbname"
                :href="createUrl(w, article.title)"
                target="_blank"
                rel="noopener"
                class="cdx-info-chip cdx-info-chip--error"
                style="text-decoration: none"
              >
                Write in {{ w.dbname }}
              </a>
            </div>
          </div>
        </template>
      </template>
    </template>
  </div>
</template>
