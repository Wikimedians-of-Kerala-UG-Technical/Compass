<script setup>
import { computed } from 'vue'
import { CdxInfoChip, CdxMessage, CdxIcon } from '@wikimedia/codex'
import { cdxIconLogoWikimediaCommons, cdxIconLogoWikidata, cdxIconCalendar } from '@wikimedia/codex-icons'
import { RouterLink } from 'vue-router'
import { useAppStore, urlName } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()
const c = computed(() => store.contribute)
const unused = computed(() => c.value?.commons?.unused || [])
const items = computed(() => c.value?.wikidata?.items || [])
const events = computed(() => c.value?.events || [])
</script>

<template>
  <div>
    <h1 class="section-heading">{{ $t('contribute.title') }}</h1>
    <p class="section-sub">{{ $t('contribute.sub', { lang: c?.language || $t('contribute.localLanguage') }) }}</p>

    <LoadingState v-if="store.contributeLoading && !c" :title="$t('contribute.loading')" :sub="$t('contribute.loadingSub')" />

    <CdxMessage v-else-if="store.contributeError" type="error">{{ store.contributeError }}</CdxMessage>

    <div v-else-if="!c" class="empty-state">{{ $t('app.waiting') }}</div>

    <template v-else>
      <CdxMessage v-if="c.partial" type="warning" style="margin-bottom: 12px">
        {{ $t('app.partialNamed', { sources: c.failed.join(', ') }) }}
      </CdxMessage>

      <div class="section-title" style="display: flex; align-items: center; gap: 6px">
        <CdxIcon :icon="cdxIconLogoWikimediaCommons" size="small" /> {{ $t('contribute.photos') }}
      </div>
      <p class="section-sub">{{ $t('contribute.photosSub', { unused: unused.length, uploads: c.commons.uploads }) }}</p>
      <div v-if="!unused.length" class="empty-state">{{ $t('contribute.allUsed') }}</div>
      <div class="photo-grid">
        <div v-for="f in unused" :key="f.file" class="panel photo-card">
          <a :href="f.url" target="_blank" rel="noopener">
            <img v-if="f.thumb" :src="f.thumb" :alt="f.file" loading="lazy" />
          </a>
          <div class="photo-card__name">{{ f.file.replace(/^File:/, '') }}</div>
          <div v-if="f.articles?.length" class="photo-card__articles">
            {{ $t('contribute.couldGo', { how: f.matchedBy === 'location' ? $t('contribute.byLocation') : $t('contribute.byTitle') }) }}
            <a v-for="a in f.articles" :key="a.title" :href="a.editUrl" target="_blank" rel="noopener">{{ a.title }}</a>
          </div>
        </div>
      </div>

      <div class="section-title" style="display: flex; align-items: center; gap: 6px; margin-top: 24px">
        <CdxIcon :icon="cdxIconLogoWikidata" size="small" />
        {{ c.wikidata.place ? $t('contribute.gapsIn', { place: c.wikidata.place }) : $t('contribute.gaps') }}
      </div>
      <div v-if="!items.length" class="empty-state">
        {{ c.wikidata.place ? $t('contribute.noGaps') : $t('contribute.noGapsNoPlace') }}
      </div>
      <div v-for="w in items" :key="w.qid" class="item-card">
        <div class="item-card__head">
          <span class="item-card__title"><a :href="w.url" target="_blank" rel="noopener">{{ w.label }}</a></span>
          <CdxInfoChip status="subtle">{{ $t('contribute.sitelinks', { n: w.sitelinks }) }}</CdxInfoChip>
        </div>
        <div class="item-card__row">
          <CdxInfoChip v-for="m in w.missing" :key="m" status="warning">{{ $t('contribute.missing', { lang: c.language, what: m }) }}</CdxInfoChip>
        </div>
      </div>

      <template v-if="events.length">
        <div class="section-title" style="display: flex; align-items: center; gap: 6px; margin-top: 24px">
          <CdxIcon :icon="cdxIconCalendar" size="small" /> {{ $t('contribute.campaigns') }}
        </div>
        <div v-for="e in events" :key="e.id || e.event_id" class="item-card">
          <div class="item-card__title">{{ e.name || e.event_name || $t('contribute.event') }}</div>
          <div class="item-card__reason">{{ $t('contribute.includes', { titles: e.yourArticles.join(', ') }) }}</div>
          <RouterLink v-if="e.id || e.event_id" :to="{ name: 'event', params: { id: e.id || e.event_id }, query: { user: urlName(store.username) } }">
            {{ $t('contribute.openEvent') }}
          </RouterLink>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.photo-card { padding: 8px; }
.photo-card img { width: 100%; height: 140px; object-fit: cover; border-radius: 2px; display: block; }
.photo-card__name { font-size: 0.75rem; margin-top: 6px; word-break: break-word; }
.photo-card__articles { font-size: 0.75rem; color: var(--color-subtle); margin-top: 4px; display: flex; flex-direction: column; gap: 2px; }
</style>
