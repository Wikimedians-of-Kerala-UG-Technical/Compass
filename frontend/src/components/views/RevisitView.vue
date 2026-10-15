<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxToggleButtonGroup, CdxInfoChip, CdxMessage } from '@wikimedia/codex'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()
const { t } = useI18n()
const activeFilter = ref('all')

const filterButtons = computed(() => {
  const seen = new Map()
  for (const task of store.revisit) {
    for (const tag of task.tags) seen.set(tag.key, tag.label)
  }
  return [
    { value: 'all', label: t('app.all') },
    { value: 'new', label: t('revisit.newFilter') },
    ...[...seen.entries()].map(([value, label]) => ({ value, label })),
  ]
})

const filteredTasks = computed(() => {
  if (activeFilter.value === 'all') return store.revisit
  if (activeFilter.value === 'new') return store.revisit.filter((task) => task.hasNew)
  return store.revisit.filter((task) => task.tags.some((tag) => tag.key === activeFilter.value))
})

function tagStatus(tag) {
  if (tag.key === 'check_edit') return 'error'
  if (tag.key === 'stub' || tag.key === 'add_link' || tag.key === 'add_image' || tag.key === 'shortdesc') return 'notice'
  return 'warning'
}

function diffUrl(task) {
  const base = task.url.split('/wiki/')[0]
  return `${base}/w/index.php?diff=${task.lastEdit.revid}`
}
</script>

<template>
  <div>
    <h1 class="section-heading">{{ $t('revisit.title') }}</h1>
    <p class="section-sub">
      {{ $t('revisit.sub') }}
    </p>

    <LoadingState v-if="store.revisitLoading && !store.revisit.length" :title="$t('revisit.loading')" :sub="$t('revisit.loadingSub')" />

    <CdxMessage v-else-if="store.revisitError" type="error">{{ store.revisitError }}</CdxMessage>

    <template v-else>
      <div v-if="!store.revisit.length" class="empty-state">{{ $t('revisit.clean') }}</div>

      <template v-else>
        <CdxToggleButtonGroup v-model="activeFilter" :buttons="filterButtons" style="margin-bottom: 16px" />

        <div v-if="!filteredTasks.length" class="empty-state">{{ $t('app.noFilterMatch') }}</div>

        <div v-for="(task, i) in filteredTasks" :key="task.title" class="item-card fade-in" :style="{ animationDelay: i * 0.02 + 's' }">
          <div class="item-card__head">
            <span class="item-card__title">
              <a :href="task.url" target="_blank" rel="noopener">{{ task.title }}</a>
            </span>
            <CdxInfoChip v-if="task.hasNew" status="error">{{ $t('revisit.newChip') }}</CdxInfoChip>
            <CdxInfoChip v-else-if="task.quality" status="subtle">{{ $t('revisit.classChip', { quality: task.quality }) }}</CdxInfoChip>
          </div>
          <div class="item-card__row" style="margin-bottom: 6px">
            <CdxInfoChip v-for="tag in task.tags" :key="tag.key" :status="tagStatus(tag)">
              {{ tag.label }}<template v-if="tag.since"> · {{ tag.since }}</template>
            </CdxInfoChip>
          </div>
          <div class="item-card__reason">
            {{ task.reason }}
            <template v-if="task.yourLastEdit"> · {{ $t('revisit.yourLastEdit', { date: task.yourLastEdit.slice(0, 10) }) }}</template>
          </div>
          <div class="item-card__actions">
            <a :href="task.editUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary">
              {{ $t('app.editOnWikipedia') }}
            </a>
            <a
              v-if="task.tags.some((g) => g.key === 'check_edit')"
              :href="diffUrl(task)"
              target="_blank"
              rel="noopener"
              class="cdx-button"
            >{{ $t('revisit.reviewEdit', { user: task.lastEdit.user }) }}</a>
            <button class="cdx-button" @click="store.searchGuide(task.title, task.wiki)">{{ $t('app.openInGuide') }}</button>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
