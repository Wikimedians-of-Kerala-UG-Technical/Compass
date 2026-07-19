<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  tasks: { type: Array, default: () => [] },
})

const filters = [
  { key: 'all', label: 'All' },
  { key: 'add_refs', label: 'References' },
  { key: 'fix_orphan', label: 'Orphans' },
  { key: 'add_citations', label: 'Citations' },
]

const activeFilter = ref('all')

const filteredTasks = computed(() =>
  activeFilter.value === 'all' ? props.tasks : props.tasks.filter((t) => t.type === activeFilter.value)
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
  <section class="wtp-card dash-main__tasks">
    <div class="wtp-card__header">
      <h3 class="wtp-card__heading">
        Recommended Tasks
        <span class="wtp-badge wtp-badge--neutral">{{ tasks.length ? '(' + tasks.length + ')' : '' }}</span>
      </h3>
      <div class="dash-task-filters">
        <button
          v-for="f in filters"
          :key="f.key"
          class="cdx-button cdx-button--size-medium filter-btn"
          :class="{ 'filter-btn--active': activeFilter === f.key }"
          @click="activeFilter = f.key"
        >
          {{ f.label }}
        </button>
      </div>
    </div>

    <div v-if="!filteredTasks.length" class="empty-state">
      <div class="empty-state__icon">✅</div>
      {{ tasks.length ? 'No tasks match this filter.' : 'No tasks found.' }}
    </div>

    <div v-else>
      <div
        v-for="(t, i) in filteredTasks"
        :key="i"
        class="task-item fade-in"
        :style="{ animationDelay: i * 0.03 + 's' }"
      >
        <div class="task-item__head">
          <span class="task-item__num">#{{ i + 1 }}</span>
          <span class="task-item__title">
            <a :href="wikiHref(t.title)" target="_blank" rel="noopener">{{ t.title }}</a>
          </span>
          <span class="wtp-badge wtp-badge--notice">{{ t.type }}</span>
        </div>
        <div v-if="t.topic" class="task-item__topic">🏷 {{ t.topic }}</div>
        <div class="task-item__reason">{{ t.reason }}</div>
        <div class="task-item__actions">
          <a
            :href="editHref(t.title)"
            target="_blank"
            rel="noopener"
            class="cdx-button cdx-button--action-progressive cdx-button--weight-primary"
            style="text-decoration: none"
          >
            Edit on Wikipedia
          </a>
          <a :href="wikiHref(t.title)" target="_blank" rel="noopener" class="cdx-button" style="text-decoration: none">
            View
          </a>
        </div>
      </div>
    </div>
  </section>
</template>
