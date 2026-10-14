<script setup>
import { computed } from 'vue'
import { CdxInfoChip, CdxIcon } from '@wikimedia/codex'
import {
  cdxIconCheckAll,
  cdxIconWatchlist,
  cdxIconLightbulb,
  cdxIconArticleSearch,
  cdxIconMapPin,
  cdxIconLogoWikimediaCommons,
} from '@wikimedia/codex-icons'
import { useAppStore } from '../../stores/appStore.js'
import TrendingCard from '../widgets/TrendingCard.vue'
import NewsCard from '../widgets/NewsCard.vue'

const store = useAppStore()

const profile = computed(() => store.profile)
const topics = computed(() => profile.value?.topics || [])
const countries = computed(() => profile.value?.countries || [])
const languages = computed(() => profile.value?.languages || [])
const wikis = computed(() => (profile.value?.wikis || []).filter((w) => w.editcount >= 50).slice(0, 6))
const geoPlaces = computed(() => store.geo?.topPlaces || [])
const focus = computed(() => store.geo?.focus || {})

const createdLabel = computed(() => {
  const p = profile.value
  if (!p) return '—'
  return p.createdCount.toLocaleString() + (p.createdCountCapped ? '+' : '')
})
const revertedLabel = computed(() => {
  const r = profile.value?.reverted
  if (!r || !r.of) return '—'
  return (r.share * 100).toFixed(1) + '%'
})

const dispatchCards = computed(() => [
  {
    key: 'tasks',
    icon: cdxIconCheckAll,
    title: store.tasksLoading && !store.tasks.length ? 'Finding tasks for you…' : `${store.tasks.length || 0} tasks ready`,
    desc: 'Articles that need work in your topics, your categories and near the places you write about.',
  },
  {
    key: 'revisit',
    icon: cdxIconWatchlist,
    title: store.revisitLoading ? 'Checking your articles…' : `${store.revisit.length || 0} of your articles need attention`,
    desc: 'Articles you created or edited a lot that picked up tags, suspicious edits or suggestions.',
  },
  {
    key: 'discover',
    icon: cdxIconLightbulb,
    title: store.discoverLoading
      ? 'Finding articles to translate…'
      : store.discover?.monolingual
        ? 'Translation suggestions'
        : `${store.discover?.articles?.length || 0} articles to translate`,
    desc: 'Articles and sections missing in your languages, picked from what you already write.',
  },
  {
    key: 'contribute',
    icon: cdxIconLogoWikimediaCommons,
    title: store.contributeLoading
      ? 'Checking Commons and Wikidata…'
      : `${store.contribute?.commons?.unused?.length || 0} photos to place · ${store.contribute?.wikidata?.items?.length || 0} Wikidata gaps`,
    desc: 'Your unused Commons photos, and Wikidata items near you missing your language.',
  },
  {
    key: 'guide',
    icon: cdxIconArticleSearch,
    title: 'Look up an article',
    desc: 'Find uncited paragraphs, tags, missing sections and ready-to-paste sources.',
  },
])
</script>

<template>
  <div>
    <h1 class="section-heading">Welcome back, {{ profile.username }}</h1>
    <p class="section-sub">
      Built from your last {{ profile.editsAnalysed.toLocaleString() }} edits on
      <strong>{{ profile.homeLang }}.wikipedia</strong>.
      <template v-if="wikis.length > 1">
        Switch wiki:
        <a
          v-for="w in wikis.filter((w) => w.dbname !== profile.homeWiki)"
          :key="w.dbname"
          href="#"
          style="margin-left: 6px"
          @click.prevent="store.switchWiki(w.dbname)"
        >{{ w.lang }} ({{ w.editcount.toLocaleString() }})</a>
      </template>
    </p>

    <div class="stat-row">
      <div class="stat-tile">
        <span class="stat-tile__num">{{ (profile.homeEdits || 0).toLocaleString() }}</span>
        <span class="stat-tile__label">Edits on {{ profile.homeLang }}.wikipedia · {{ (profile.total || 0).toLocaleString() }} across Wikimedia</span>
      </div>
      <div class="stat-tile">
        <span class="stat-tile__num">{{ createdLabel }}</span>
        <span class="stat-tile__label">Articles created</span>
      </div>
      <div class="stat-tile">
        <span class="stat-tile__num">{{ revertedLabel }}</span>
        <span class="stat-tile__label">Recent edits reverted by others</span>
      </div>
    </div>

    <div class="chip-row">
      <CdxInfoChip v-for="t in topics" :key="t.path" status="notice">
        {{ t.label }} · {{ Math.round(t.share * 100) }}%
      </CdxInfoChip>
      <CdxInfoChip v-for="c in countries" :key="c.a3" status="subtle">{{ c.name }}</CdxInfoChip>
      <CdxInfoChip v-for="l in languages" :key="l.lang" status="progressive">
        {{ l.lang }}<template v-if="l.level"> · {{ l.level }}</template>
      </CdxInfoChip>
      <CdxInfoChip v-if="profile.sisterProjects?.wikidatawiki" status="subtle">
        Wikidata · {{ profile.sisterProjects.wikidatawiki.toLocaleString() }}
      </CdxInfoChip>
      <CdxInfoChip v-if="profile.sisterProjects?.commonswiki" status="subtle">
        Commons · {{ profile.sisterProjects.commonswiki.toLocaleString() }}
      </CdxInfoChip>
    </div>

    <div class="panel" style="margin-bottom: 20px">
      <div class="section-title" style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px">
        <CdxIcon :icon="cdxIconMapPin" size="small" />
        Where you edit
      </div>

      <div v-if="store.geoLoading && !store.geo" class="fade-in">
        <div class="skeleton-line skeleton-line--wide"></div>
        <div class="skeleton-line skeleton-line--narrow"></div>
      </div>

      <p v-else-if="store.geoError" style="font-size: 0.8125rem; color: var(--color-error)">{{ store.geoError }}</p>

      <template v-else-if="geoPlaces.length">
        <p v-if="focus.region || focus.local" style="font-size: 0.8125rem; margin-bottom: 8px">
          Focus: <strong>{{ [focus.local?.name, focus.region?.name, focus.country?.name].filter(Boolean).join(', ') }}</strong>
          — used for "near you" tasks and local gaps.
        </p>
        <div class="chip-row" style="margin-bottom: 0">
          <CdxInfoChip v-for="p in geoPlaces" :key="p.qid" status="subtle">
            {{ p.name }} <strong>({{ p.count }})</strong>
          </CdxInfoChip>
        </div>
      </template>

      <p v-else style="font-size: 0.8125rem; color: var(--color-subtle)">
        None of your recent articles are about a place, so tasks aren't limited to a region.
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
