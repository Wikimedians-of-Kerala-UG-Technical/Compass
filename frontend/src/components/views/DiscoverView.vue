<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxToggleButtonGroup, CdxInfoChip, CdxButton, CdxIcon, CdxMessage } from '@wikimedia/codex'
import { cdxIconReload } from '@wikimedia/codex-icons'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()
const { t } = useI18n()

const tabs = computed(() => [
  { value: 'articles', label: t('discover.tabArticles', { n: store.discover?.articles?.length || 0 }) },
  { value: 'sections', label: t('discover.tabSections', { n: store.discover?.sections?.length || 0 }) },
  { value: 'gaps', label: t('discover.tabGaps', { n: store.discover?.regionGaps?.length || 0 }) },
])
const tab = ref('articles')

const pairs = computed(() => store.discover?.pairs || [])
const articles = computed(() => store.discover?.articles || [])
const sections = computed(() => store.discover?.sections || [])
const gaps = computed(() => store.discover?.regionGaps || [])
const missingHere = computed(() => store.discover?.missingHere || [])
const BABEL_URL = 'https://meta.wikimedia.org/wiki/User_language'
</script>

<template>
  <div>
    <div class="item-card__head" style="align-items: flex-start; margin-bottom: 4px">
      <div>
        <h1 class="section-heading">{{ $t('discover.title') }}</h1>
        <p class="section-sub" style="margin-bottom: 0">{{ $t('discover.sub') }}</p>
      </div>
      <CdxButton weight="quiet" :disabled="store.discoverLoading" @click="store.fetchDiscover()">
        <CdxIcon :icon="cdxIconReload" />
        {{ store.discoverLoading ? $t('app.loading') : $t('app.refresh') }}
      </CdxButton>
    </div>

    <LoadingState v-if="store.discoverLoading && !store.discover" :title="$t('discover.loading')" :sub="$t('discover.loadingSub')" />

    <CdxMessage v-else-if="store.discoverError" type="error" style="margin: 16px 0">{{ store.discoverError }}</CdxMessage>

    <div v-else-if="!store.discover && !store.discoverLoading" class="empty-state">{{ $t('app.waiting') }}</div>

    <template v-else-if="store.discover?.monolingual">
      <template v-if="store.profile?.homeWiki !== 'enwiki'">
        <div class="section-title" style="margin-top: 16px">{{ $t('discover.monoTitle') }}</div>
        <i18n-t keypath="discover.monoSub" tag="p" class="section-sub">
          <template #lang>{{ store.profile?.homeLang }}</template>
          <template #babel><a :href="BABEL_URL" target="_blank" rel="noopener">{{ $t('discover.babel') }}</a></template>
        </i18n-t>
        <div v-if="!missingHere.length" class="empty-state">{{ $t('discover.monoNone') }}</div>
        <div v-for="m in missingHere" :key="m.title" class="item-card">
          <div class="item-card__head">
            <span class="item-card__title"><a :href="m.sourceUrl" target="_blank" rel="noopener">{{ m.title }}</a></span>
          </div>
          <div class="item-card__reason">{{ m.why }}</div>
          <div class="item-card__actions">
            <a v-if="m.createUrl" :href="m.createUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary">
              {{ $t('discover.startArticle', { title: m.localTitle }) }}
            </a>
            <a :href="m.sourceUrl" target="_blank" rel="noopener" class="cdx-button">{{ $t('discover.readEnglish') }}</a>
            <a v-if="m.wikidataUrl" :href="m.wikidataUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--weight-quiet">{{ $t('discover.seeWikidata') }}</a>
          </div>
        </div>
      </template>
      <i18n-t v-else keypath="discover.monoEnglish" tag="div" class="empty-state" style="text-align: left">
        <template #babel><a :href="BABEL_URL" target="_blank" rel="noopener">{{ $t('discover.babel') }}</a></template>
      </i18n-t>
    </template>

    <template v-else>
      <div class="chip-row" style="margin: 16px 0 12px">
        <CdxInfoChip v-for="p in pairs" :key="p.source + p.target" status="progressive">{{ p.source }} → {{ p.target }}</CdxInfoChip>
      </div>

      <CdxToggleButtonGroup v-model="tab" :buttons="tabs" style="margin-bottom: 16px" />

      <template v-if="tab === 'articles'">
        <div v-if="!articles.length" class="empty-state">{{ $t('discover.noArticles') }}</div>
        <div v-for="a in articles" :key="a.title + a.target" class="item-card">
          <div class="item-card__head">
            <span class="item-card__title">
              <a :href="a.sourceUrl" target="_blank" rel="noopener">{{ a.title }}</a>
            </span>
            <CdxInfoChip status="subtle">{{ $t('discover.inLanguages', { n: a.languages }) }}</CdxInfoChip>
          </div>
          <div class="item-card__reason">{{ $t('discover.sizeIn', { why: a.why, kb: Math.round(a.size / 1000), lang: a.source }) }}</div>
          <div class="item-card__actions">
            <a :href="a.translateUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary">
              {{ $t('discover.translateInto', { lang: a.target }) }}
            </a>
          </div>
        </div>
      </template>

      <template v-else-if="tab === 'sections'">
        <div v-if="!sections.length" class="empty-state">{{ $t('discover.noSections') }}</div>
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
        <div v-if="!gaps.length" class="empty-state">{{ $t('discover.noGaps') }}</div>
        <div v-for="g in gaps" :key="g.qid" class="item-card">
          <div class="item-card__head">
            <span class="item-card__title">
              <a :href="g.sourceUrl" target="_blank" rel="noopener">{{ g.title }}</a>
            </span>
            <CdxInfoChip status="subtle">{{ $t('discover.sites', { n: g.sitelinks }) }}</CdxInfoChip>
          </div>
          <div class="item-card__reason">{{ $t('discover.gapReason', { place: g.region || $t('discover.yourArea'), lang: g.target }) }}</div>
          <div class="item-card__actions">
            <a :href="g.translateUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary">
              {{ $t('discover.translateInto', { lang: g.target }) }}
            </a>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
