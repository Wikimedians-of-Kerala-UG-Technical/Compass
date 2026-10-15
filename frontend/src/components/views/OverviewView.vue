<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxInfoChip, CdxIcon } from '@wikimedia/codex'
import {
  cdxIconCheckAll,
  cdxIconWatchlist,
  cdxIconLightbulb,
  cdxIconArticleSearch,
  cdxIconMapPin,
  cdxIconLogoWikimediaCommons,
  cdxIconChart,
} from '@wikimedia/codex-icons'
import { useAppStore } from '../../stores/appStore.js'
import TrendingCard from '../widgets/TrendingCard.vue'
import NewsCard from '../widgets/NewsCard.vue'

const store = useAppStore()
const { t } = useI18n()

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

const dispatchCards = computed(() => {
  const d = store.discover
  return [
    {
      key: 'tasks',
      icon: cdxIconCheckAll,
      title: store.tasksLoading && !store.tasks.length ? t('overview.card.tasksLoading') : t('overview.card.tasks', store.tasks.length),
      desc: t('overview.card.tasksDesc'),
    },
    {
      key: 'revisit',
      icon: cdxIconWatchlist,
      title: store.revisitLoading ? t('overview.card.revisitLoading') : t('overview.card.revisit', store.revisit.length),
      desc: t('overview.card.revisitDesc'),
    },
    {
      key: 'discover',
      icon: cdxIconLightbulb,
      title: store.discoverLoading
        ? t('overview.card.discoverLoading')
        : d?.monolingual
          ? t('overview.card.discoverMono')
          : t('overview.card.discover', d?.articles?.length || 0),
      desc: t('overview.card.discoverDesc'),
    },
    {
      key: 'contribute',
      icon: cdxIconLogoWikimediaCommons,
      title: store.contributeLoading
        ? t('overview.card.contributeLoading')
        : t('overview.card.contribute', {
            photos: store.contribute?.commons?.unused?.length || 0,
            gaps: store.contribute?.wikidata?.items?.length || 0,
          }),
      desc: t('overview.card.contributeDesc'),
    },
    { key: 'guide', icon: cdxIconArticleSearch, title: t('overview.card.guide'), desc: t('overview.card.guideDesc') },
    { key: 'stats', icon: cdxIconChart, title: t('overview.card.stats'), desc: t('overview.card.statsDesc') },
  ]
})
</script>

<template>
  <div>
    <h1 class="section-heading">{{ $t('overview.welcome', { name: profile.username }) }}</h1>
    <p class="section-sub">
      {{ $t('overview.builtFrom', { count: profile.editsAnalysed.toLocaleString(), wiki: `${profile.homeLang}.wikipedia` }) }}
      <template v-if="wikis.length > 1">
        {{ $t('overview.switchWiki') }}
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
        <span class="stat-tile__label">{{ $t('overview.editsOn', { wiki: `${profile.homeLang}.wikipedia`, total: (profile.total || 0).toLocaleString() }) }}</span>
      </div>
      <div class="stat-tile">
        <span class="stat-tile__num">{{ createdLabel }}</span>
        <span class="stat-tile__label">{{ $t('overview.created') }}</span>
      </div>
      <div class="stat-tile">
        <span class="stat-tile__num">{{ revertedLabel }}</span>
        <span class="stat-tile__label">{{ $t('overview.reverted') }}</span>
      </div>
    </div>

    <div class="chip-row">
      <CdxInfoChip v-for="tp in topics" :key="tp.path" status="notice">
        {{ tp.label }} · {{ Math.round(tp.share * 100) }}%
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
        {{ $t('overview.whereYouEdit') }}
      </div>

      <div v-if="store.geoLoading && !store.geo" class="fade-in">
        <div class="skeleton-line skeleton-line--wide"></div>
        <div class="skeleton-line skeleton-line--narrow"></div>
      </div>

      <p v-else-if="store.geoError" style="font-size: 0.8125rem; color: var(--color-error)">{{ store.geoError }}</p>

      <template v-else-if="geoPlaces.length">
        <p v-if="focus.region || focus.local" style="font-size: 0.8125rem; margin-bottom: 8px">
          {{ $t('overview.focus') }} <strong>{{ [focus.local?.name, focus.region?.name, focus.country?.name].filter(Boolean).join(', ') }}</strong>
          {{ $t('overview.focusUse') }}
        </p>
        <div class="chip-row" style="margin-bottom: 0">
          <CdxInfoChip v-for="p in geoPlaces" :key="p.qid" status="subtle">
            {{ p.name }} <strong>({{ p.count }})</strong>
          </CdxInfoChip>
        </div>
      </template>

      <p v-else style="font-size: 0.8125rem; color: var(--color-subtle)">{{ $t('overview.noPlaces') }}</p>
    </div>

    <div class="two-col">
      <TrendingCard />
      <NewsCard />
    </div>

    <div class="section-title">{{ $t('overview.whatNext') }}</div>
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
