<script setup>
import { ref, computed } from 'vue'
import { CdxToggleButtonGroup, CdxInfoChip } from '@wikimedia/codex'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()

const filterButtons = [
  { value: 'all', label: 'All' },
  { value: 'add_refs', label: 'References' },
  { value: 'fix_orphan', label: 'Orphans' },
  { value: 'add_citations', label: 'Citations' },
]
const activeFilter = ref('all')

const filteredTasks = computed(() =>
  activeFilter.value === 'all' ? store.tasks : store.tasks.filter((t) => t.type === activeFilter.value)
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
    <h1 class="section-heading">Recommended tasks</h1>
    <p class="section-sub">Maintenance work ranked by relevance, impact, and feasibility for your profile.</p>

    <CdxToggleButtonGroup v-model="activeFilter" :buttons="filterButtons" style="margin-bottom: 16px" />

    <LoadingState
      v-if="store.tasksLoading"
      title="Finding tasks for you…"
      sub="Searching Wikipedia for articles that match your topics. Usually just a few seconds."
    />

    <div v-else-if="!filteredTasks.length" class="empty-state">
      {{ store.tasks.length ? 'No tasks match this filter.' : 'No tasks found.' }}
    </div>

    <div v-else>
      <div v-for="(t, i) in filteredTasks" :key="i" class="item-card fade-in" :style="{ animationDelay: i * 0.02 + 's' }">
        <div class="item-card__head">
          <span class="item-card__title">
            <a :href="wikiHref(t.title)" target="_blank" rel="noopener">{{ t.title }}</a>
          </span>
          <CdxInfoChip status="notice">{{ t.type }}</CdxInfoChip>
        </div>
        <div v-if="t.topic" class="item-card__row" style="margin-bottom: 6px">
          <CdxInfoChip status="subtle">{{ t.topic }}</CdxInfoChip>
        </div>
        <div class="item-card__reason">{{ t.reason }}</div>
        <div class="item-card__actions">
          <a :href="editHref(t.title)" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary">
            Edit on Wikipedia
          </a>
          <a :href="wikiHref(t.title)" target="_blank" rel="noopener" class="cdx-button">View</a>
        </div>
      </div>
    </div>
  </div>
</template>
