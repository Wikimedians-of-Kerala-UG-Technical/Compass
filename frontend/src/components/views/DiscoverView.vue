<script setup>
import { ref, computed } from 'vue'
import { CdxToggleButtonGroup, CdxInfoChip, CdxButton, CdxIcon, CdxMessage } from '@wikimedia/codex'
import { cdxIconReload } from '@wikimedia/codex-icons'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()

const tabs = computed(() => [
  { value: 'articles', label: `New articles (${store.discover?.articles?.length || 0})` },
  { value: 'sections', label: `Missing sections (${store.discover?.sections?.length || 0})` },
  { value: 'gaps', label: `Missing near you (${store.discover?.regionGaps?.length || 0})` },
])
const tab = ref('articles')

const pairs = computed(() => store.discover?.pairs || [])
const articles = computed(() => store.discover?.articles || [])
const sections = computed(() => store.discover?.sections || [])
const gaps = computed(() => store.discover?.regionGaps || [])
</script>

<template>
  <div>
    <div class="item-card__head" style="align-items: flex-start; margin-bottom: 4px">
      <div>
        <h1 class="section-heading">Discover</h1>
        <p class="section-sub" style="margin-bottom: 0">
          Articles and sections to translate into your languages, chosen by Content Translation's recommender from the
          articles you already write. Each link opens Content Translation with the article loaded.
        </p>
      </div>
      <CdxButton weight="quiet" :disabled="store.discoverLoading" @click="store.fetchDiscover()">
        <CdxIcon :icon="cdxIconReload" />
        {{ store.discoverLoading ? 'Loading…' : 'Refresh' }}
      </CdxButton>
    </div>

    <LoadingState
      v-if="store.discoverLoading && !store.discover"
      title="Finding articles to translate…"
      sub="Asking Content Translation for articles related to yours that are missing in your languages."
    />

    <CdxMessage v-else-if="store.discoverError" type="error" style="margin: 16px 0">{{ store.discoverError }}</CdxMessage>

    <div v-else-if="!store.discover && !store.discoverLoading" class="empty-state">
      Waiting for your profile and places to load…
    </div>

    <div v-else-if="store.discover?.monolingual" class="empty-state" style="text-align: left">
      You only edit in one language, so there's nothing to translate yet. If you read another language, add a
      <a href="https://meta.wikimedia.org/wiki/User_language" target="_blank" rel="noopener">Babel box</a> to your user
      page and Compass will suggest articles missing in it.
    </div>

    <template v-else>
      <div class="chip-row" style="margin: 16px 0 12px">
        <CdxInfoChip v-for="p in pairs" :key="p.source + p.target" status="progressive">{{ p.source }} → {{ p.target }}</CdxInfoChip>
      </div>

      <CdxToggleButtonGroup v-model="tab" :buttons="tabs" style="margin-bottom: 16px" />

      <template v-if="tab === 'articles'">
        <div v-if="!articles.length" class="empty-state">No translation suggestions right now.</div>
        <div v-for="a in articles" :key="a.title + a.target" class="item-card">
          <div class="item-card__head">
            <span class="item-card__title">
              <a :href="a.sourceUrl" target="_blank" rel="noopener">{{ a.title }}</a>
            </span>
            <CdxInfoChip status="subtle">in {{ a.languages }} languages</CdxInfoChip>
          </div>
          <div class="item-card__reason">{{ a.why }} · {{ Math.round(a.size / 1000) }} kB in {{ a.source }}</div>
          <div class="item-card__actions">
            <a :href="a.translateUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary">
              Translate into {{ a.target }}
            </a>
          </div>
        </div>
      </template>

      <template v-else-if="tab === 'sections'">
        <div v-if="!sections.length" class="empty-state">No missing sections found in articles related to yours.</div>
        <div v-for="s in sections" :key="s.sourceTitle + s.target" class="item-card">
          <div class="item-card__head">
            <span class="item-card__title">
              <a :href="s.targetUrl" target="_blank" rel="noopener">{{ s.targetTitle }}</a>
            </span>
            <CdxInfoChip status="subtle">{{ s.source }}: {{ s.sourceTitle }}</CdxInfoChip>
          </div>
          <div class="item-card__row">
            <a
              v-for="m in s.missing"
              :key="m.section"
              :href="m.translateUrl"
              target="_blank"
              rel="noopener"
              class="cdx-info-chip cdx-info-chip--warning"
              style="text-decoration: none"
            >+ {{ m.targetHeading }} ({{ m.section }})</a>
          </div>
        </div>
      </template>

      <template v-else>
        <div v-if="!gaps.length" class="empty-state">
          No gaps found for your places, or your places haven't been resolved yet.
        </div>
        <div v-for="g in gaps" :key="g.qid" class="item-card">
          <div class="item-card__head">
            <span class="item-card__title">
              <a :href="g.sourceUrl" target="_blank" rel="noopener">{{ g.title }}</a>
            </span>
            <CdxInfoChip status="subtle">{{ g.sitelinks }} Wikimedia sites</CdxInfoChip>
          </div>
          <div class="item-card__reason">Located in {{ g.region || 'your area' }}; has an English article but none in {{ g.target }}.</div>
          <div class="item-card__actions">
            <a :href="g.translateUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary">
              Translate into {{ g.target }}
            </a>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
