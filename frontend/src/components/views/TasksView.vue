<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxToggleButtonGroup, CdxInfoChip, CdxMessage, CdxIcon } from '@wikimedia/codex'
import { cdxIconStar, cdxIconClose, cdxIconCheck, cdxIconEyeClosed } from '@wikimedia/codex-icons'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()
const { t } = useI18n()
const activeFilter = ref('all')

// Built from the task types actually present, so every filter has results.
const filterButtons = computed(() => {
  const seen = new Map()
  for (const task of store.visibleTasks) seen.set(task.type, task.meta?.label || task.type)
  return [{ value: 'all', label: t('app.all') }, ...[...seen.entries()].map(([value, label]) => ({ value, label }))]
})

const filteredTasks = computed(() =>
  activeFilter.value === 'all' ? store.visibleTasks : store.visibleTasks.filter((task) => task.type === activeFilter.value)
)
const hiddenCount = computed(() => (store.tasksMeta?.hidden || 0) + store.tasks.length - store.visibleTasks.length)
const refiningWithGeo = computed(() => store.geoLoading && !store.tasksLoading)
const guided = computed(() => store.tasksMeta?.mode === 'guided')

const votes = [
  { action: 'up', icon: cdxIconStar, label: 'tasks.good' },
  { action: 'done', icon: cdxIconCheck, label: 'tasks.done' },
  { action: 'down', icon: cdxIconClose, label: 'tasks.bad' },
  { action: 'dismiss', icon: cdxIconEyeClosed, label: 'tasks.dismiss' },
]

function effortStatus(effort) {
  return effort === 'low' ? 'success' : effort === 'high' ? 'warning' : 'notice'
}
</script>

<template>
  <div>
    <h1 class="section-heading">{{ $t('tasks.title') }}</h1>
    <p class="section-sub">{{ $t('tasks.sub', { wiki: `${store.profile?.homeLang}.wikipedia` }) }}</p>

    <CdxMessage v-if="guided" type="notice" style="margin-bottom: 12px">{{ $t('tasks.guided') }}</CdxMessage>

    <div v-if="refiningWithGeo" class="note-bar">{{ $t('tasks.geoRefining') }}</div>

    <LoadingState v-if="store.tasksLoading && !store.tasks.length" :title="$t('tasks.loading')" :sub="$t('tasks.loadingSub')" />

    <CdxMessage v-else-if="store.tasksError && !store.tasks.length" type="error">{{ store.tasksError }}</CdxMessage>

    <template v-else>
      <CdxMessage v-if="store.tasksMeta?.partial" type="warning" style="margin-bottom: 12px">{{ $t('app.partial') }}</CdxMessage>
      <CdxMessage v-if="store.feedbackError" type="error" style="margin-bottom: 12px">{{ store.feedbackError }}</CdxMessage>

      <CdxToggleButtonGroup v-model="activeFilter" :buttons="filterButtons" style="margin-bottom: 16px" />

      <p v-if="hiddenCount > 0" class="section-sub">{{ $t('tasks.hidden', { n: hiddenCount }) }}</p>

      <div v-if="!filteredTasks.length" class="empty-state">
        {{ store.visibleTasks.length ? $t('app.noFilterMatch') : $t('tasks.none') }}
      </div>

      <div v-for="(task, i) in filteredTasks" :key="task.title" class="item-card fade-in" :style="{ animationDelay: i * 0.02 + 's' }">
        <div class="item-card__head">
          <span class="item-card__title">
            <a :href="task.url" target="_blank" rel="noopener">{{ task.title }}</a>
          </span>
          <CdxInfoChip :status="effortStatus(task.meta?.effort)">{{ $t('tasks.minutes', { label: task.meta?.label, min: task.meta?.min }) }}</CdxInfoChip>
        </div>
        <div class="item-card__row" style="margin-bottom: 6px">
          <CdxInfoChip v-for="iss in task.issues" :key="iss.key" status="warning">
            {{ iss.label }}<template v-if="iss.since"> · {{ $t('tasks.since', { date: iss.since }) }}</template>
          </CdxInfoChip>
          <CdxInfoChip v-if="task.topic" status="subtle">{{ task.topic }}</CdxInfoChip>
        </div>
        <div class="item-card__reason">
          <strong>{{ $t('tasks.whyYou') }}</strong> {{ task.reason }}
          <div v-if="task.details?.length" style="margin-top: 2px">{{ task.details.join(' · ') }}</div>
        </div>
        <div class="item-card__actions">
          <a :href="task.editUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary">
            {{ $t('app.editOnWikipedia') }}
          </a>
          <button class="cdx-button" @click="store.searchGuide(task.title, task.wiki)">{{ $t('tasks.whatToFix') }}</button>
          <span class="vote-group" role="group">
            <button
              v-for="v in votes"
              :key="v.action"
              class="cdx-button cdx-button--weight-quiet vote"
              :class="{ 'is-on': store.feedback[task.title] === v.action }"
              :title="$t(v.label)"
              :aria-label="$t(v.label)"
              :aria-pressed="store.feedback[task.title] === v.action"
              @click="store.vote(task, v.action)"
            >
              <CdxIcon :icon="v.icon" size="small" />
            </button>
          </span>
        </div>
        <div v-if="store.feedback[task.title] === 'up'" class="item-card__reason" style="margin-top: 4px">{{ $t('tasks.thanks') }}</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.vote-group { display: inline-flex; gap: 2px; margin-left: auto; }
.vote.is-on { color: var(--color-progressive); background: var(--background-color-progressive-subtle); }
</style>
