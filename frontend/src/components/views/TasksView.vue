<script setup>
import { ref, computed } from 'vue'
import { CdxToggleButtonGroup, CdxInfoChip, CdxMessage } from '@wikimedia/codex'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()
const activeFilter = ref('all')

// Built from the task types actually present, so every filter has results.
const filterButtons = computed(() => {
  const seen = new Map()
  for (const t of store.tasks) seen.set(t.type, t.meta?.label || t.type)
  return [{ value: 'all', label: 'All' }, ...[...seen.entries()].map(([value, label]) => ({ value, label }))]
})

const filteredTasks = computed(() =>
  activeFilter.value === 'all' ? store.tasks : store.tasks.filter((t) => t.type === activeFilter.value)
)

const refiningWithGeo = computed(() => store.geoLoading && !store.tasksLoading)

function effortStatus(effort) {
  return effort === 'low' ? 'success' : effort === 'high' ? 'warning' : 'notice'
}
</script>

<template>
  <div>
    <h1 class="section-heading">Recommended tasks</h1>
    <p class="section-sub">
      Articles on {{ store.profile?.homeLang }}.wikipedia that need work, found through your topics, the categories you
      edit in, articles like yours, and places you write about. Each card says why it's here.
    </p>

    <div v-if="refiningWithGeo" class="geo-refining">
      Still working out where you edit — "near you" tasks will be added when that's done.
    </div>

    <LoadingState
      v-if="store.tasksLoading && !store.tasks.length"
      title="Finding tasks for you…"
      sub="Searching tracking categories and Growth suggestions in your topics. Usually 10–30 seconds."
    />

    <CdxMessage v-else-if="store.tasksError && !store.tasks.length" type="error">{{ store.tasksError }}</CdxMessage>

    <template v-else>
      <CdxMessage v-if="store.tasksMeta?.partial" type="warning" style="margin-bottom: 12px">
        Some sources failed (often rate limiting), so this list may be incomplete.
      </CdxMessage>

      <CdxToggleButtonGroup v-model="activeFilter" :buttons="filterButtons" style="margin-bottom: 16px" />

      <div v-if="!filteredTasks.length" class="empty-state">
        {{ store.tasks.length ? 'No tasks match this filter.' : 'No tasks found for your topics on this wiki.' }}
      </div>

      <div v-for="(t, i) in filteredTasks" :key="t.title" class="item-card fade-in" :style="{ animationDelay: i * 0.02 + 's' }">
        <div class="item-card__head">
          <span class="item-card__title">
            <a :href="t.url" target="_blank" rel="noopener">{{ t.title }}</a>
          </span>
          <CdxInfoChip :status="effortStatus(t.meta?.effort)">{{ t.meta?.label }} · ~{{ t.meta?.min }} min</CdxInfoChip>
        </div>
        <div class="item-card__row" style="margin-bottom: 6px">
          <CdxInfoChip v-for="iss in t.issues" :key="iss.key" status="warning">
            {{ iss.label }}<template v-if="iss.since"> · since {{ iss.since }}</template>
          </CdxInfoChip>
          <CdxInfoChip v-if="t.topic" status="subtle">{{ t.topic }}</CdxInfoChip>
        </div>
        <div class="item-card__reason">
          <strong>Why you:</strong> {{ t.reason }}
          <div v-if="t.details?.length" style="margin-top: 2px">{{ t.details.join(' · ') }}</div>
        </div>
        <div class="item-card__actions">
          <a :href="t.editUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary">
            Edit on Wikipedia
          </a>
          <button class="cdx-button" @click="store.searchGuide(t.title, t.wiki)">What exactly needs fixing?</button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.geo-refining {
  margin-bottom: 12px;
  padding: 8px 12px;
  border-left: 3px solid #a2a9b1;
  background: #f8f9fa;
  color: #54595d;
  font-size: 13px;
}
</style>
