<script setup>
import { ref, computed } from 'vue'
import { CdxToggleButtonGroup, CdxInfoChip, CdxMessage } from '@wikimedia/codex'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()
const activeFilter = ref('all')

const filterButtons = computed(() => {
  const seen = new Map()
  for (const task of store.revisit) {
    for (const tag of task.tags) seen.set(tag.key, tag.label)
  }
  return [
    { value: 'all', label: 'All' },
    { value: 'new', label: 'New since your edit' },
    ...[...seen.entries()].map(([value, label]) => ({ value, label })),
  ]
})

const filteredTasks = computed(() => {
  if (activeFilter.value === 'all') return store.revisit
  if (activeFilter.value === 'new') return store.revisit.filter((t) => t.hasNew)
  return store.revisit.filter((t) => t.tags.some((tag) => tag.key === activeFilter.value))
})

function tagStatus(tag) {
  if (tag.key === 'check_edit') return 'error'
  if (tag.key === 'stub' || tag.key === 'add_link' || tag.key === 'add_image' || tag.key === 'shortdesc') return 'notice'
  return 'warning'
}

function diffUrl(t) {
  const base = t.url.split('/wiki/')[0]
  return `${base}/w/index.php?diff=${t.lastEdit.revid}`
}
</script>

<template>
  <div>
    <h1 class="section-heading">Revisit</h1>
    <p class="section-sub">
      Articles you created or edited a lot that need attention: new maintenance tags (with dates), a risky-looking
      latest edit by someone else, or a ready-made suggestion. Problems that appeared after your last edit come first.
    </p>

    <LoadingState
      v-if="store.revisitLoading && !store.revisit.length"
      title="Checking your articles…"
      sub="Reading tags, dates and the latest edit on every article you created or edited a lot."
    />

    <CdxMessage v-else-if="store.revisitError" type="error">{{ store.revisitError }}</CdxMessage>

    <template v-else>
      <div v-if="!store.revisit.length" class="empty-state">
        Nothing needs revisiting right now — your articles are clean.
      </div>

      <template v-else>
        <CdxToggleButtonGroup v-model="activeFilter" :buttons="filterButtons" style="margin-bottom: 16px" />

        <div v-if="!filteredTasks.length" class="empty-state">No articles match this filter.</div>

        <div v-for="(t, i) in filteredTasks" :key="t.title" class="item-card fade-in" :style="{ animationDelay: i * 0.02 + 's' }">
          <div class="item-card__head">
            <span class="item-card__title">
              <a :href="t.url" target="_blank" rel="noopener">{{ t.title }}</a>
            </span>
            <CdxInfoChip v-if="t.hasNew" status="error">New since your last edit</CdxInfoChip>
            <CdxInfoChip v-else-if="t.quality" status="subtle">{{ t.quality }}-class</CdxInfoChip>
          </div>
          <div class="item-card__row" style="margin-bottom: 6px">
            <CdxInfoChip v-for="tag in t.tags" :key="tag.key" :status="tagStatus(tag)">
              {{ tag.label }}<template v-if="tag.since"> · {{ tag.since }}</template>
            </CdxInfoChip>
          </div>
          <div class="item-card__reason">
            {{ t.reason }}
            <template v-if="t.yourLastEdit"> · your last edit {{ t.yourLastEdit.slice(0, 10) }}</template>
          </div>
          <div class="item-card__actions">
            <a :href="t.editUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary">
              Edit on Wikipedia
            </a>
            <a
              v-if="t.tags.some((g) => g.key === 'check_edit')"
              :href="diffUrl(t)"
              target="_blank"
              rel="noopener"
              class="cdx-button"
            >Review latest edit by {{ t.lastEdit.user }}</a>
            <button class="cdx-button" @click="store.searchGuide(t.title, t.wiki)">Open in Guide</button>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
