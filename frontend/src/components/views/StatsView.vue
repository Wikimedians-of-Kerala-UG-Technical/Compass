<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxMessage } from '@wikimedia/codex'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()
const { t } = useI18n()
const s = computed(() => store.stats)

function compact(n) {
  return new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(n || 0)
}

// 90-day activity calendar: one column per week, Monday first. A single-hue scale
// (Codex's progressive blue at four strengths) so it works in both themes.
const LEVELS = [0, 1, 3, 8] // edits/day at which a cell steps up
const calendar = computed(() => {
  const counts = s.value?.calendar || {}
  const days = []
  const today = new Date()
  for (let i = 89; i >= 0; i--) {
    const d = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate() - i))
    const key = d.toISOString().slice(0, 10)
    const n = counts[key] || 0
    const level = n === 0 ? 0 : LEVELS.filter((l) => n >= l).length
    days.push({ key, n, level, weekday: (d.getUTCDay() + 6) % 7 })
  }
  const weeks = []
  let week = Array(days[0].weekday).fill(null)
  for (const day of days) {
    week.push(day)
    if (week.length === 7) {
      weeks.push(week)
      week = []
    }
  }
  if (week.length) weeks.push(week)
  return weeks
})

const summary = computed(() => {
  const c = s.value?.compass
  return c ? t('stats.compassSummary', { up: c.up, done: c.done, edited: c.edited }) : ''
})
</script>

<template>
  <div>
    <h1 class="section-heading">{{ $t('stats.title') }}</h1>
    <p class="section-sub">{{ $t('stats.sub', { wiki: `${store.profile?.homeLang}.wikipedia` }) }}</p>

    <LoadingState v-if="store.statsLoading && !s" :title="$t('stats.loading')" />
    <CdxMessage v-else-if="store.statsError" type="error">{{ store.statsError }}</CdxMessage>

    <template v-else-if="s">
      <div class="stat-row">
        <div class="stat-tile">
          <span class="stat-tile__num">{{ s.streak.current }}</span>
          <span class="stat-tile__label">{{ $t('stats.streak') }} · {{ $t('stats.longest', { n: s.streak.longest90 }) }}</span>
        </div>
        <div class="stat-tile">
          <span class="stat-tile__num">{{ s.last30.edits.toLocaleString() }}</span>
          <span class="stat-tile__label">
            {{ $t('stats.edits30') }} · {{ $t('stats.articles30', { n: s.last30.articles, kb: Math.round(s.last30.bytesAdded / 1000) }) }}
          </span>
        </div>
        <div class="stat-tile">
          <span class="stat-tile__num">{{ compact(s.readers.monthly) }}</span>
          <span class="stat-tile__label">
            {{ $t('stats.readers') }} · {{ $t('stats.readersNote', { checked: s.readers.articlesChecked, total: s.readers.articlesTotal }) }}
          </span>
        </div>
      </div>

      <div class="panel" style="margin-bottom: 20px">
        <div class="section-title">{{ $t('stats.calendar') }}</div>
        <div class="cal" role="img" :aria-label="$t('stats.calendar')">
          <div v-for="(week, w) in calendar" :key="w" class="cal__week">
            <template v-for="(day, d) in week" :key="d">
              <span
                v-if="day"
                class="cal__day"
                :class="'cal__day--' + day.level"
                :title="$t('stats.calendarDay', { date: day.key, n: day.n })"
                :aria-label="$t('stats.calendarDay', { date: day.key, n: day.n })"
              ></span>
              <span v-else class="cal__day cal__day--blank"></span>
            </template>
          </div>
        </div>
        <div class="cal__legend" aria-hidden="true">
          0 <span v-for="l in 4" :key="l" class="cal__day" :class="'cal__day--' + (l - 1)"></span> {{ LEVELS[3] }}+
        </div>
      </div>

      <div v-if="s.readers.top.length" class="panel" style="margin-bottom: 20px">
        <div class="section-title">{{ $t('stats.topArticles') }}</div>
        <div v-for="a in s.readers.top" :key="a.title" class="alert-row">
          <a :href="a.url" target="_blank" rel="noopener">{{ a.title }}</a>
          <span style="color: var(--color-subtle)">{{ $t('stats.perDay', { n: a.perDay.toLocaleString() }) }}</span>
        </div>
      </div>

      <div v-if="s.compass" class="panel">
        <div class="section-title">{{ $t('stats.compass') }}</div>
        <p style="font-size: 0.8125rem">{{ summary }}</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.cal { display: flex; gap: 2px; overflow-x: auto; padding-bottom: 4px; }
.cal__week { display: flex; flex-direction: column; gap: 2px; }
.cal__day {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 2px;
  background: var(--background-color-interactive-subtle);
  outline: 1px solid var(--border-color-subtle);
  outline-offset: -1px;
}
.cal__day--1 { background: color-mix(in srgb, var(--color-progressive) 35%, transparent); outline: none; }
.cal__day--2 { background: color-mix(in srgb, var(--color-progressive) 65%, transparent); outline: none; }
.cal__day--3 { background: var(--color-progressive); outline: none; }
.cal__day--blank { visibility: hidden; }
.cal__legend { display: flex; align-items: center; gap: 2px; font-size: 0.6875rem; color: var(--color-subtle); margin-top: 6px; }
.cal__legend .cal__day { margin: 0 1px; }
</style>
