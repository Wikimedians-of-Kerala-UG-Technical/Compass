<script setup>
import { ref, computed } from 'vue'
import { CdxToggleButtonGroup, CdxInfoChip, CdxMessage } from '@wikimedia/codex'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()

const activeFilter = ref('all')

// Built from whatever tags actually show up in the data, so the filter row only ever
// offers options that are meaningful for this specific user.
const filterButtons = computed(() => {
  const seen = new Map()
  for (const task of store.revisit) {
    for (const tag of task.tags) seen.set(tag.key, tag.label)
  }
  return [
    { value: 'all', label: 'All' },
    ...[...seen.entries()].map(([value, label]) => ({ value, label })),
  ]
})

const filteredTasks = computed(() =>
  activeFilter.value === 'all'
    ? store.revisit
    : store.revisit.filter((t) => t.tags.some((tag) => tag.key === activeFilter.value))
)

function wikiHref(title) {
  return 'https://en.wikipedia.org/wiki/' + encodeURIComponent((title || '').replace(/ /g, '_'))
}
function editHref(title) {
  return (
    'https://en.wikipedia.org/w/index.php?title=' +
    encodeURIComponent((title || '').replace(/ /g, '_')) +
    '&action=edit'
  )
}
</script>

<template>
  <div>
    <h1 class="section-heading">Revisit</h1>
    <p class="section-sub">
      Articles you've heavily edited or created that have since picked up maintenance issues —
      the ones that carry your name are worth defending.
    </p>

    <LoadingState
      v-if="store.revisitLoading && !store.revisit.length"
      title="Checking your articles for new issues…"
      sub="Scanning every article you've heavily edited or created for maintenance tags. This can take a minute or two."
    />

    <CdxMessage v-else-if="store.revisitError" type="error">
      {{ store.revisitError }}
    </CdxMessage>

    <template v-else>
      <div v-if="!store.revisit.length" class="empty-state">
        Nothing needs revisiting right now — your heavily-edited and created articles are clean.
      </div>

      <template v-else>
        <CdxToggleButtonGroup v-model="activeFilter" :buttons="filterButtons" style="margin-bottom: 16px" />

        <div v-if="!filteredTasks.length" class="empty-state">No articles match this tag.</div>

        <div v-for="(t, i) in filteredTasks" :key="i" class="item-card fade-in" :style="{ animationDelay: i * 0.02 + 's' }">
          <div class="item-card__head">
            <span class="item-card__title">
              <a :href="wikiHref(t.title)" target="_blank" rel="noopener">{{ t.title }}</a>
            </span>
          </div>
          <div class="item-card__row" style="margin-bottom: 6px">
            <CdxInfoChip v-for="tag in t.tags" :key="tag.key" status="warning">{{ tag.label }}</CdxInfoChip>
          </div>
          <div class="item-card__reason">{{ t.reason }}</div>
          <div class="item-card__actions">
            <a :href="editHref(t.title)" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary">
              Edit on Wikipedia
            </a>
            <a :href="wikiHref(t.title)" target="_blank" rel="noopener" class="cdx-button">View</a>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
