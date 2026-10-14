<script setup>
import { computed } from 'vue'
import { CdxInfoChip, CdxMessage, CdxIcon } from '@wikimedia/codex'
import { cdxIconLogoWikimediaCommons, cdxIconLogoWikidata, cdxIconCalendar } from '@wikimedia/codex-icons'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()
const c = computed(() => store.contribute)
const unused = computed(() => c.value?.commons?.unused || [])
const items = computed(() => c.value?.wikidata?.items || [])
const events = computed(() => c.value?.events || [])
</script>

<template>
  <div>
    <h1 class="section-heading">Commons &amp; Wikidata</h1>
    <p class="section-sub">
      Work for photographers and Wikidata editors: put your own photos into articles, and fill in Wikidata items near you
      that have no {{ c?.language || 'local-language' }} description.
    </p>

    <LoadingState
      v-if="store.contributeLoading && !c"
      title="Checking your Commons uploads and Wikidata…"
      sub="Looking for photos you uploaded that no article uses yet, and Wikidata items in your area."
    />

    <CdxMessage v-else-if="store.contributeError" type="error">{{ store.contributeError }}</CdxMessage>

    <div v-else-if="!c" class="empty-state">Waiting for your profile and places to load…</div>

    <template v-else>
      <CdxMessage v-if="c.partial" type="warning" style="margin-bottom: 12px">
        Some sources failed ({{ c.failed.join(', ') }}), so this page may be incomplete.
      </CdxMessage>

      <div class="section-title" style="display: flex; align-items: center; gap: 6px">
        <CdxIcon :icon="cdxIconLogoWikimediaCommons" size="small" /> Place your photos
      </div>
      <p class="section-sub">
        {{ unused.length }} of your last {{ c.commons.uploads }} Commons uploads aren't used in any Wikipedia article.
      </p>
      <div v-if="!unused.length" class="empty-state">All your recent photos are used somewhere. 🎉</div>
      <div class="photo-grid">
        <div v-for="f in unused" :key="f.file" class="panel photo-card">
          <a :href="f.url" target="_blank" rel="noopener">
            <img v-if="f.thumb" :src="f.thumb" :alt="f.file" loading="lazy" />
          </a>
          <div class="photo-card__name">{{ f.file.replace(/^File:/, '') }}</div>
          <div v-if="f.articles?.length" class="photo-card__articles">
            Could go in ({{ f.matchedBy === 'location' ? 'within 1 km' : 'matching title' }}):
            <a v-for="a in f.articles" :key="a.title" :href="a.editUrl" target="_blank" rel="noopener">{{ a.title }}</a>
          </div>
        </div>
      </div>

      <div class="section-title" style="display: flex; align-items: center; gap: 6px; margin-top: 24px">
        <CdxIcon :icon="cdxIconLogoWikidata" size="small" /> Wikidata gaps<template v-if="c.wikidata.place"> in {{ c.wikidata.place }}</template>
      </div>
      <div v-if="!items.length" class="empty-state">
        No Wikidata gaps found{{ c.wikidata.place ? '' : " — we couldn't work out a place you edit about" }}.
      </div>
      <div v-for="w in items" :key="w.qid" class="item-card">
        <div class="item-card__head">
          <span class="item-card__title"><a :href="w.url" target="_blank" rel="noopener">{{ w.label }}</a></span>
          <CdxInfoChip status="subtle">{{ w.sitelinks }} sitelinks</CdxInfoChip>
        </div>
        <div class="item-card__row">
          <CdxInfoChip v-for="m in w.missing" :key="m" status="warning">No {{ c.language }} {{ m }}</CdxInfoChip>
        </div>
      </div>

      <template v-if="events.length">
        <div class="section-title" style="display: flex; align-items: center; gap: 6px; margin-top: 24px">
          <CdxIcon :icon="cdxIconCalendar" size="small" /> Campaigns that include your articles
        </div>
        <div v-for="e in events" :key="e.id || e.event_id" class="item-card">
          <div class="item-card__title">{{ e.name || e.event_name || 'Event' }}</div>
          <div class="item-card__reason">Includes: {{ e.yourArticles.join(', ') }}</div>
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
