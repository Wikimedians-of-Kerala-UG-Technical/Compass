<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { CdxTextInput, CdxButton, CdxTabs, CdxTab, CdxInfoChip, CdxMessage, CdxSelect } from '@wikimedia/codex'
import { getGuide, getExternalReferences } from '../../api.js'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()

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
  if (s.uncitedParagraphs.length || s.inlineTags.length) return { label: 'Needs citations', status: 'warning' }
  if (s.chars < 200 && s.level === 2 && s.name !== '(Lead)') return { label: 'Thin', status: 'notice' }
  return { label: 'OK', status: 'success' }
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
    <h1 class="section-heading">Article Guide</h1>
    <p class="section-sub">
      Shows exactly what to fix in an article: uncited paragraphs, dated tags, dead links, missing sections compared with
      English, a Wikidata image to add, and sources you can paste straight in.
    </p>

    <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap">
      <CdxTextInput
        v-model="titleInput"
        placeholder="Article title…"
        aria-label="Article title for guide"
        style="flex: 1; min-width: 200px"
        @keydown.enter="analyse"
      />
      <CdxSelect v-model:selected="wikiInput" :menu-items="wikiOptions" aria-label="Wiki" />
      <CdxButton action="progressive" weight="primary" @click="analyse">Analyse</CdxButton>
    </div>

    <LoadingState
      v-if="loading"
      :title="`Analysing ${searchedTitle}…`"
      sub="Reading the article paragraph by paragraph, plus its Wikidata item. Usually a few seconds."
    />

    <CdxMessage v-else-if="hasError" type="error">
      {{ guideData?.error || 'Could not load this article. Make sure the title is exact.' }}
    </CdxMessage>

    <div v-else-if="guideData">
      <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px">
        <a :href="guideData.url" target="_blank" class="serif" style="font-size: 1.125rem">{{ guideData.title }}</a>
        <CdxInfoChip v-if="guideData.quality" status="notice">{{ guideData.quality }}-class</CdxInfoChip>
        <CdxInfoChip v-if="guideData.importance" status="subtle">{{ guideData.importance }} importance</CdxInfoChip>
        <CdxInfoChip status="subtle">{{ Math.round((guideData.currentSize || 0) / 1000) }} kB</CdxInfoChip>
        <CdxInfoChip status="subtle">{{ guideData.totalRefs || 0 }} citations</CdxInfoChip>
        <CdxInfoChip v-for="t in guideData.topics" :key="t" status="subtle">{{ t }}</CdxInfoChip>
        <a :href="guideData.editUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary" style="margin-left: auto">
          Edit article
        </a>
      </div>
      <p v-if="guideData.qualityNext" class="section-sub" style="margin-bottom: 12px">
        <strong>Next quality step:</strong> {{ guideData.qualityNext }}
      </p>

      <CdxTabs v-model:active="activeTab">
        <CdxTab name="fix" :label="`What to fix (${guideData.suggestions.length})`">
          <div v-if="!guideData.suggestions.length" class="empty-state">No problems found — this article looks well cited.</div>
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

        <CdxTab name="sections" label="Sections">
          <div class="section-grid">
            <div v-for="s in sections" :key="s.id" class="panel" style="padding: 8px 12px">
              <div style="font-size: 0.8125rem; font-weight: bold">{{ s.name }}</div>
              <div style="margin: 4px 0">
                <CdxInfoChip :status="sectionStatus(s).status">{{ sectionStatus(s).label }}</CdxInfoChip>
              </div>
              <div style="font-size: 0.75rem; color: var(--color-subtle)">
                {{ s.chars.toLocaleString() }} chars · {{ s.refCount }} citations
                <template v-if="s.uncitedParagraphs.length"> · {{ s.uncitedParagraphs.length }} uncited paragraph(s)</template>
                <template v-if="s.inlineTags.length"> · {{ s.inlineTags.length }} inline tag(s)</template>
              </div>
            </div>
          </div>
          <template v-if="guideData.missingSections?.length">
            <div class="section-title" style="margin-top: 16px">Sections in the English article but not here</div>
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

        <CdxTab name="sources" :label="refsLoading ? 'Sources…' : `Sources (${refs.length})`">
          <LoadingState v-if="refsLoading" title="Searching for sources…" sub="PubMed, OpenAlex and CrossRef, then formatting citations with Citoid." />
          <template v-else>
            <p v-if="refsData" class="section-sub" style="margin-top: 16px">
              Searched {{ refsData.sourcesUsed.join(', ') }} for “{{ refsData.query }}”<template v-if="refsData.medical">
              — medical topic, so PubMed review articles come first (WP:MEDRS)</template>. Sources the article already cites are
              left out. Check each one before citing it.
            </p>
            <div v-if="!refs.length" class="empty-state">No sources found.</div>
            <div v-for="(r, i) in refs" :key="i" class="panel" style="padding: 10px 12px; margin-bottom: 8px">
              <a :href="r.url || '#'" target="_blank" rel="noopener" style="font-weight: bold; font-size: 0.8125rem">{{ r.title }}</a>
              <div style="font-size: 0.75rem; color: var(--color-subtle); margin-top: 3px">
                {{ [r.authors, r.year, r.venue].filter(Boolean).join(' · ') }}
                <CdxInfoChip status="subtle" style="margin-left: 6px">{{ r.source }}</CdxInfoChip>
                <template v-if="r.citations"> · cited {{ r.citations }}×</template>
              </div>
              <div v-if="r.cite" style="display: flex; gap: 8px; align-items: flex-start; margin-top: 6px">
                <code class="cite">{{ r.cite }}</code>
                <CdxButton size="small" @click="copyCite(i, r.cite)">{{ copied === i ? 'Copied' : 'Copy' }}</CdxButton>
              </div>
            </div>
          </template>
        </CdxTab>
      </CdxTabs>
    </div>

    <div v-else class="empty-state">Search for an article above to get started.</div>
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
  background: #f8f9fa;
  padding: 4px 6px;
  border-radius: 2px;
  word-break: break-all;
  max-height: 4.5em;
  overflow: auto;
}
</style>
