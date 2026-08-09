<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { CdxTextInput, CdxButton, CdxTabs, CdxTab, CdxInfoChip, CdxMessage } from '@wikimedia/codex'
import { getGuide, getReferences, getExternalReferences } from '../../api.js'
import { useAppStore } from '../../stores/appStore.js'
import LoadingState from '../widgets/LoadingState.vue'

const store = useAppStore()

const titleInput = ref('')
const searchedTitle = ref('')
const loading = ref(false)
const searched = ref(false)
const guideData = ref(null)
const extRefsData = ref(null)
const activeTab = ref('structure')

const wikiRefs = ref([])
const nextOffset = ref(null)
const loadingMore = ref(false)
const loadMoreError = ref(false)

const hasError = computed(() => searched.value && !loading.value && (!guideData.value || guideData.value.error))

function wikiUrl(title) {
  return 'https://en.wikipedia.org/wiki/' + encodeURIComponent((title || '').replace(/ /g, '_'))
}
function editUrl(title) {
  return (
    'https://en.wikipedia.org/w/index.php?title=' +
    encodeURIComponent((title || '').replace(/ /g, '_')) +
    '&action=edit'
  )
}
function cap(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''
}
function sectionStatusText(s) {
  if (s.status === 'missing') return 'Missing'
  if (s.status === 'short') return 'Thin section'
  return 'Present'
}

const sectionItems = computed(() => {
  const g = guideData.value
  if (!g) return []
  const sliced = (g.sections || []).slice(0, 8)
  if (sliced.length) {
    return sliced.map((s) => ({
      name: s.name,
      status: sectionStatusText(s),
      chipStatus: s.status === 'missing' ? 'error' : s.status === 'short' ? 'warning' : 'success',
      tip: s.tip,
    }))
  }
  if (g.missingExpected && g.missingExpected.length) {
    return g.missingExpected.map((s) => ({
      name: s,
      status: 'Missing',
      chipStatus: 'error',
      tip: `expected for ${cap(g.articleType || 'general')} articles`,
    }))
  }
  return []
})

function analyse() {
  const title = titleInput.value.trim()
  if (!title) return

  searchedTitle.value = title
  loading.value = true
  searched.value = true
  guideData.value = null
  extRefsData.value = null
  wikiRefs.value = []
  nextOffset.value = null
  loadMoreError.value = false
  activeTab.value = 'structure'

  Promise.all([
    getGuide(title).catch(() => null),
    getReferences(title).catch(() => null),
    getExternalReferences(title).catch(() => null),
  ]).then(([g, refs, extRefs]) => {
    guideData.value = g
    wikiRefs.value = (refs?.results || []).slice(0, 10)
    nextOffset.value = refs?.nextOffset ?? null
    extRefsData.value = extRefs
    loading.value = false
  })
}

function loadMore() {
  if (!nextOffset.value) return
  loadingMore.value = true
  loadMoreError.value = false
  getReferences(searchedTitle.value, nextOffset.value)
    .then((more) => {
      if (more && more.results) {
        wikiRefs.value = [...wikiRefs.value, ...more.results]
        nextOffset.value = more.nextOffset ?? null
      }
      loadingMore.value = false
    })
    .catch(() => {
      loadMoreError.value = true
      loadingMore.value = false
    })
}

const extRefs = computed(() => (extRefsData.value?.results || []).slice(0, 10))

function syncFromStoreQuery() {
  if (!store.guideQuery) return
  titleInput.value = store.guideQuery
  analyse()
}

// Covers a search dispatched from the top-bar while GuideView wasn't mounted yet
// (guideQuerySeq already changed before this component's watcher existed).
onMounted(syncFromStoreQuery)

// Covers a search dispatched from the top-bar while GuideView is already active.
watch(() => store.guideQuerySeq, syncFromStoreQuery)
</script>

<template>
  <div>
    <h1 class="section-heading">Article Guide &amp; References</h1>
    <p class="section-sub">Analyse any Wikipedia article for structural gaps and suggested sources.</p>

    <div style="display: flex; gap: 8px; margin-bottom: 16px">
      <CdxTextInput
        v-model="titleInput"
        placeholder="Enter any Wikipedia article title…"
        aria-label="Article title for guide"
        style="flex: 1"
        @keydown.enter="analyse"
      />
      <CdxButton action="progressive" @click="analyse">Analyse</CdxButton>
    </div>

    <LoadingState
      v-if="loading"
      :title="`Analysing ${searchedTitle}…`"
      sub="Checking sections, references, and academic sources. Usually just a few seconds, occasionally up to a minute for long articles."
    />

    <CdxMessage v-else-if="hasError" type="error">
      Could not load article guide. Make sure the title is exact.
    </CdxMessage>

    <div v-else-if="guideData">
      <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 16px">
        <a :href="wikiUrl(searchedTitle)" target="_blank" class="serif" style="font-size: 1.125rem">{{ searchedTitle }}</a>
        <CdxInfoChip status="notice">{{ cap(guideData.articleType || 'general') }}</CdxInfoChip>
        <CdxInfoChip status="subtle">{{ Math.round((guideData.currentSize || 0) / 1000) }}k chars</CdxInfoChip>
        <CdxInfoChip status="subtle">{{ guideData.totalRefs || 0 }} refs</CdxInfoChip>
        <CdxInfoChip v-if="!guideData.hasInfobox" status="warning">No infobox</CdxInfoChip>
        <CdxInfoChip v-if="!guideData.hasImages" status="warning">No images</CdxInfoChip>
        <a :href="editUrl(searchedTitle)" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary" style="margin-left: auto">
          Edit article
        </a>
      </div>

      <CdxTabs v-model:active="activeTab">
        <CdxTab name="structure" label="Structure">
          <template v-if="(guideData.suggestions || []).length">
            <div class="section-title" style="margin-top: 16px">Overall analysis</div>
            <div style="display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px">
              <div v-for="(s, i) in guideData.suggestions" :key="i" class="panel" style="padding: 8px 12px; border-left: 3px solid var(--color-progressive)">
                {{ s.text || s }}
              </div>
            </div>
          </template>

          <template v-if="sectionItems.length">
            <div class="section-title">Section analysis</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px">
              <div v-for="(s, i) in sectionItems" :key="i" class="panel" style="padding: 8px 12px">
                <div style="font-size: 0.8125rem; font-weight: bold">{{ s.name }}</div>
                <div style="margin-top: 4px"><CdxInfoChip :status="s.chipStatus">{{ s.status }}</CdxInfoChip></div>
                <div v-if="s.tip" style="font-size: 0.75rem; color: var(--color-subtle); margin-top: 4px">{{ s.tip }}</div>
              </div>
            </div>
          </template>

          <div v-if="!(guideData.suggestions || []).length && !sectionItems.length" class="empty-state">
            No structural analysis available for this article.
          </div>
        </CdxTab>

        <CdxTab name="wiki" label="Wikipedia References">
          <template v-if="wikiRefs.length">
            <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 16px">
              <a v-for="(r, i) in wikiRefs" :key="i" :href="r.url || '#'" target="_blank" rel="noopener" class="panel" style="display: block; text-decoration: none; color: inherit">
                <div style="font-size: 0.8125rem; color: var(--color-progressive); font-weight: bold">{{ r.title || 'Untitled' }}</div>
                <div style="font-size: 0.75rem; color: var(--color-subtle); margin-top: 3px">
                  {{ r.authors || '' }}<template v-if="r.year"> · {{ r.year }}</template><template v-if="r.venue"> · {{ r.venue }}</template>
                </div>
              </a>
            </div>
            <CdxButton v-if="nextOffset" style="width: 100%; margin-top: 8px" :disabled="loadingMore" @click="loadMore">
              {{ loadMoreError ? 'Error — try again' : loadingMore ? 'Loading…' : 'Load more references…' }}
            </CdxButton>
          </template>
          <div v-else class="empty-state">No internal references found.</div>
        </CdxTab>

        <CdxTab name="academic" label="Academic References">
          <template v-if="extRefs.length">
            <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 16px">
              <a v-for="(r, i) in extRefs" :key="i" :href="r.url || '#'" target="_blank" rel="noopener" class="panel" style="display: block; text-decoration: none; color: inherit">
                <div style="font-size: 0.8125rem; color: var(--color-progressive); font-weight: bold">{{ r.title || 'Untitled' }}</div>
                <div style="margin-top: 6px">
                  <CdxInfoChip status="subtle">{{ r.source }}</CdxInfoChip>
                  <template v-if="r.citations !== null && r.citations !== undefined"> {{ r.citations }} citations</template>
                </div>
              </a>
            </div>
          </template>
          <div v-else class="empty-state">No external research found.</div>
        </CdxTab>
      </CdxTabs>
    </div>

    <div v-else class="empty-state">Search for an article above to get started.</div>
  </div>
</template>
