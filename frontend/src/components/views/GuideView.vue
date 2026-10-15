<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxTextInput, CdxButton, CdxTabs, CdxTab, CdxInfoChip, CdxMessage, CdxSelect } from '@wikimedia/codex'
import { getGuide, getExternalReferences } from '../../api.js'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()
const { t } = useI18n()

const titleInput = ref('')
const wikiInput = ref(store.wiki || 'enwiki')
const searchedTitle = ref('')
const loading = ref(false)
const searched = ref(false)
const guideData = ref(null)
const refsData = ref(null)
const refsLoading = ref(false)
const activeTab = ref('fix')
const copied = ref(-1)

const wikiOptions = computed(() => {
  const dbs = new Set(['enwiki', ...(store.profile?.wikis || []).map((w) => w.dbname)])
  if (wikiInput.value) dbs.add(wikiInput.value)
  return [...dbs].map((db) => ({ value: db, label: db.replace(/wiki$/, '') + '.wikipedia' }))
})

const hasError = computed(() => searched.value && !loading.value && (!guideData.value || guideData.value.error))
const sections = computed(() => (guideData.value?.sections || []).filter((s) => s.level <= 3))
const refs = computed(() => refsData.value?.results || [])

// The button and Enter go through the URL (so the result can be linked to); the URL
// change brings the query back here through the store. Re-running the same query
// doesn't change the URL, so that runs directly.
function submit() {
  const title = titleInput.value.trim()
  if (!title) return
  if (title === store.guideQuery && wikiInput.value === store.guideWiki) analyse()
  else store.searchGuide(title, wikiInput.value)
}

function analyse() {
  const title = titleInput.value.trim()
  if (!title) return
  const wiki = wikiInput.value || 'enwiki'
  searchedTitle.value = title
  loading.value = true
  searched.value = true
  guideData.value = null
  refsData.value = null
  activeTab.value = 'fix'

  getGuide(title, wiki)
    .catch((e) => ({ error: e.message }))
    .then((g) => {
      guideData.value = g
      loading.value = false
    })
  refsLoading.value = true
  getExternalReferences(title, wiki)
    .catch(() => null)
    .then((r) => {
      refsData.value = r
      refsLoading.value = false
    })
}

function copyCite(i, text) {
  navigator.clipboard?.writeText(text).then(() => {
    copied.value = i
    setTimeout(() => { if (copied.value === i) copied.value = -1 }, 1500)
  })
}

function sectionStatus(s) {
  if (s.uncitedParagraphs.length || s.inlineTags.length) return { label: t('guide.needsCitations'), status: 'warning' }
  if (s.chars < 200 && s.level === 2 && s.name !== '(Lead)') return { label: t('guide.thin'), status: 'notice' }
  return { label: t('guide.ok'), status: 'success' }
}

function syncFromStoreQuery() {
  if (!store.guideQuery) return
  titleInput.value = store.guideQuery
  wikiInput.value = store.guideWiki || store.wiki || 'enwiki'
  analyse()
}

onMounted(syncFromStoreQuery)
watch(() => store.guideQuerySeq, syncFromStoreQuery)
</script>

<template>
  <div>
    <h1 class="section-heading">{{ $t('guide.title') }}</h1>
    <p class="section-sub">{{ $t('guide.sub') }}</p>

    <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap">
      <CdxTextInput
        v-model="titleInput"
        :placeholder="$t('guide.placeholder')"
        :aria-label="$t('guide.label')"
        style="flex: 1; min-width: 200px"
        @keydown.enter="submit"
      />
      <CdxSelect v-model:selected="wikiInput" :menu-items="wikiOptions" :aria-label="$t('guide.wiki')" />
      <CdxButton action="progressive" weight="primary" @click="submit">{{ $t('guide.analyse') }}</CdxButton>
    </div>

    <LoadingState
      v-if="loading"
      :title="$t('guide.analysing', { title: searchedTitle })"
      :sub="$t('guide.analysingSub')"
    />

    <CdxMessage v-else-if="hasError" type="error">
      {{ guideData?.error || $t('guide.notFound') }}
    </CdxMessage>

    <div v-else-if="guideData">
      <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px">
        <a :href="guideData.url" target="_blank" class="serif" style="font-size: 1.125rem">{{ guideData.title }}</a>
        <CdxInfoChip v-if="guideData.quality" status="notice">{{ $t('revisit.classChip', { quality: guideData.quality }) }}</CdxInfoChip>
        <CdxInfoChip v-if="guideData.importance" status="subtle">{{ $t('guide.importance', { level: guideData.importance }) }}</CdxInfoChip>
        <CdxInfoChip status="subtle">{{ $t('guide.kb', { n: Math.round((guideData.currentSize || 0) / 1000) }) }}</CdxInfoChip>
        <CdxInfoChip status="subtle">{{ $t('guide.citations', { n: guideData.totalRefs || 0 }) }}</CdxInfoChip>
        <CdxInfoChip v-for="t in guideData.topics" :key="t" status="subtle">{{ t }}</CdxInfoChip>
        <a :href="guideData.editUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary" style="margin-left: auto">
          {{ $t('guide.edit') }}
        </a>
      </div>
      <p v-if="guideData.qualityNext" class="section-sub" style="margin-bottom: 12px">
        <strong>{{ $t('guide.nextStep') }}</strong> {{ guideData.qualityNext }}
      </p>

      <CdxTabs v-model:active="activeTab">
        <CdxTab name="fix" :label="$t('guide.tabFix', { n: guideData.suggestions.length })">
          <div v-if="!guideData.suggestions.length" class="empty-state">{{ $t('guide.clean') }}</div>
          <div style="display: flex; flex-direction: column; gap: 6px; margin-top: 16px">
            <div
              v-for="(s, i) in guideData.suggestions"
              :key="i"
              class="panel"
              style="padding: 8px 12px; border-left: 3px solid var(--color-progressive); display: flex; gap: 10px; align-items: center"
            >
              <img v-if="s.image" :src="s.image" alt="" style="width: 72px; height: 72px; object-fit: cover" />
              <div style="flex: 1">
                <a v-if="s.url" :href="s.url" target="_blank" rel="noopener">{{ s.text }}</a>
                <template v-else>{{ s.text }}</template>
              </div>
            </div>
          </div>
        </CdxTab>

        <CdxTab name="sections" :label="$t('guide.tabSections')">
          <div class="section-grid">
            <div v-for="s in sections" :key="s.id" class="panel" style="padding: 8px 12px">
              <div style="font-size: 0.8125rem; font-weight: bold">{{ s.name }}</div>
              <div style="margin: 4px 0">
                <CdxInfoChip :status="sectionStatus(s).status">{{ sectionStatus(s).label }}</CdxInfoChip>
              </div>
              <div style="font-size: 0.75rem; color: var(--color-subtle)">
                {{ $t('guide.sectionStats', { chars: s.chars.toLocaleString(), refs: s.refCount }) }}
                <template v-if="s.uncitedParagraphs.length"> · {{ $t('guide.uncited', { n: s.uncitedParagraphs.length }) }}</template>
                <template v-if="s.inlineTags.length"> · {{ $t('guide.inline', { n: s.inlineTags.length }) }}</template>
              </div>
            </div>
          </div>
          <template v-if="guideData.missingSections?.length">
            <div class="section-title" style="margin-top: 16px">{{ $t('guide.missingSections') }}</div>
            <div class="item-card__row">
              <a
                v-for="m in guideData.missingSections"
                :key="m.section"
                :href="m.translateUrl"
                target="_blank"
                rel="noopener"
                class="cdx-info-chip cdx-info-chip--warning"
                style="text-decoration: none"
              >+ {{ m.targetHeading }} ({{ m.section }})</a>
            </div>
          </template>
        </CdxTab>

        <CdxTab name="sources" :label="refsLoading ? $t('guide.tabSourcesLoading') : $t('guide.tabSources', { n: refs.length })">
          <LoadingState v-if="refsLoading" :title="$t('guide.searchingSources')" :sub="$t('guide.searchingSourcesSub')" />
          <template v-else>
            <p v-if="refsData" class="section-sub" style="margin-top: 16px">
              {{ $t('guide.searched', { sources: refsData.sourcesUsed.join(', '), query: refsData.query }) }}
              <template v-if="refsData.medical">{{ $t('guide.medical') }}</template>
              {{ $t('guide.checkEach') }}
            </p>
            <div v-if="!refs.length" class="empty-state">{{ $t('guide.noSources') }}</div>
            <div v-for="(r, i) in refs" :key="i" class="panel" style="padding: 10px 12px; margin-bottom: 8px">
              <a :href="r.url || '#'" target="_blank" rel="noopener" style="font-weight: bold; font-size: 0.8125rem">{{ r.title }}</a>
              <div style="font-size: 0.75rem; color: var(--color-subtle); margin-top: 3px">
                {{ [r.authors, r.year, r.venue].filter(Boolean).join(' · ') }}
                <CdxInfoChip status="subtle" style="margin-left: 6px">{{ r.source }}</CdxInfoChip>
                <template v-if="r.citations"> · {{ $t('guide.citedTimes', { n: r.citations }) }}</template>
              </div>
              <div v-if="r.cite" style="display: flex; gap: 8px; align-items: flex-start; margin-top: 6px">
                <code class="cite">{{ r.cite }}</code>
                <CdxButton size="small" @click="copyCite(i, r.cite)">{{ copied === i ? $t('guide.copied') : $t('guide.copy') }}</CdxButton>
              </div>
            </div>
          </template>
        </CdxTab>
      </CdxTabs>
    </div>

    <div v-else class="empty-state">{{ $t('guide.start') }}</div>
  </div>
</template>

<style scoped>
.section-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 6px;
  margin-top: 16px;
}
.cite {
  flex: 1;
  font-size: 0.6875rem;
  background: var(--background-color-interactive-subtle);
  padding: 4px 6px;
  border-radius: 2px;
  word-break: break-all;
  max-height: 4.5em;
  overflow: auto;
}
</style>
