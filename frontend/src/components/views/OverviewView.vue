<script setup>
import { computed } from 'vue'
import { CdxInfoChip, CdxIcon } from '@wikimedia/codex'
import {
  cdxIconCheckAll,
  cdxIconWatchlist,
  cdxIconLightbulb,
  cdxIconArticleSearch,
  cdxIconMapPin,
} from '@wikimedia/codex-icons'
import { useAppStore } from '../../stores/appStore.js'
import TrendingCard from '../widgets/TrendingCard.vue'
import NewsCard from '../widgets/NewsCard.vue'

const store = useAppStore()

const profile = computed(() => store.profile)
const topTopics = computed(() => profile.value?.topTopics || [])
const userWikis = computed(() => store.discover?.userWikis || [])
const geoPlaces = computed(() => store.geo?.topPlaces || [])

const qualityLabel = computed(() => {
  const t = profile.value?.qualityTier
  if (t === 'high') return 'High quality'
  if (t === 'medium') return 'Solid'
  if (t === 'developing') return 'Developing'
  return '—'
})

const dispatchCards = computed(() => [
  {
    key: 'tasks',
    icon: cdxIconCheckAll,
    title: store.tasksLoading
      ? 'Finding tasks for you…'
      : store.geoLoading
        ? `${store.tasks.length || 0} tasks ready — refining for your region…`
        : `${store.tasks.length || 0} tasks ready`,
    desc: 'Maintenance work matched to your topics — references, orphans, citations.',
  },
  {
    key: 'revisit',
    icon: cdxIconWatchlist,
    title: store.revisitLoading
      ? 'Checking your articles…'
      : `${store.revisit.length || 0} of your articles need attention`,
    desc: 'Articles you heavily edited or created that have since picked up issues.',
  },
  {
    key: 'discover',
    icon: cdxIconLightbulb,
    title: store.discoverLoading
      ? 'Scanning for new articles…'
      : `${store.discover?.suggestedArticles?.length || 0} articles you could start`,
    desc: 'Topics you work in that don\'t exist yet in one of your other languages.',
  },
  {
    key: 'guide',
    icon: cdxIconArticleSearch,
    title: 'Look up an article',
    desc: 'Analyse any Wikipedia article for structural gaps and suggested sources.',
  },
])
</script>

<template>
  <div>
    <h1 class="section-heading">Welcome back, {{ store.username }}</h1>
    <p class="section-sub">Here's what we found from your editing history.</p>

    <div class="stat-row">
      <div class="stat-tile">
        <span class="stat-tile__num">{{ (profile.total || 0).toLocaleString() }}</span>
        <span class="stat-tile__label">Edits</span>
      </div>
      <div class="stat-tile">
        <span class="stat-tile__num">{{ (profile.uniqueArticles || 0).toLocaleString() }}</span>
        <span class="stat-tile__label">Articles</span>
      </div>
      <div class="stat-tile">
        <span class="stat-tile__num" style="font-size: 1.25rem">{{ qualityLabel }}</span>
        <span class="stat-tile__label">Quality tier</span>
      </div>
    </div>

    <div class="chip-row">
      <CdxInfoChip v-for="t in topTopics" :key="t" status="notice">{{ t }}</CdxInfoChip>
      <CdxInfoChip v-for="w in userWikis" :key="w.dbname" status="progressive">
        {{ w.lang }} · {{ w.editcount.toLocaleString() }} edits
      </CdxInfoChip>
      <span v-if="!topTopics.length && !userWikis.length" style="font-size: 0.8125rem; color: var(--color-subtle)">
        Building your topic profile…
      </span>
    </div>

    <div class="panel" style="margin-bottom: 20px">
      <div class="section-title" style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px">
        <CdxIcon :icon="cdxIconMapPin" size="small" />
        Geographic focus
      </div>
      <p style="font-size: 0.75rem; color: var(--color-subtle); margin-bottom: 10px">
        Recalculated every visit — persistent caching is planned once accounts are supported, so this
        won't need to re-run each time.
      </p>

      <div v-if="store.geoLoading && !store.geo" class="fade-in">
        <div class="skeleton-line skeleton-line--wide"></div>
        <div class="skeleton-line skeleton-line--narrow"></div>
      </div>

      <p v-else-if="store.geoError" style="font-size: 0.8125rem; color: var(--color-error)">{{ store.geoError }}</p>

      <div v-else-if="geoPlaces.length" class="chip-row" style="margin-bottom: 0">
        <CdxInfoChip v-for="p in geoPlaces" :key="p.name" status="subtle">
          {{ p.name }} <strong>({{ p.count }})</strong>
        </CdxInfoChip>
      </div>

      <p v-else style="font-size: 0.8125rem; color: var(--color-subtle)">
        No resolvable geographic signal found in your edits yet.
      </p>
    </div>

    <div class="two-col">
      <TrendingCard />
      <NewsCard />
    </div>

    <div class="section-title">What next</div>
    <div class="dispatch-row">
      <button v-for="c in dispatchCards" :key="c.key" class="dispatch-card" @click="store.goTo(c.key)">
        <CdxIcon class="dispatch-card__icon" :icon="c.icon" />
        <div>
          <div class="dispatch-card__title">{{ c.title }}</div>
          <div class="dispatch-card__desc">{{ c.desc }}</div>
        </div>
      </button>
    </div>
  </div>
</template>
