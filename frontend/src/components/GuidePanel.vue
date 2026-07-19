<script setup>
import { ref, computed } from 'vue'
import { getGuide, getReferences, getExternalReferences } from '../api.js'

const titleInput = ref('')
const searchedTitle = ref('')
const loading = ref(false)
const searched = ref(false)
const guideData = ref(null)
const extRefsData = ref(null)

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
  if (s.status === 'missing') return '✗ Missing'
  if (s.status === 'short') return '△ Thin section'
  return '✓ Present'
}

const sectionItems = computed(() => {
  const g = guideData.value
  if (!g) return []
  const sliced = (g.sections || []).slice(0, 8)
  if (sliced.length) {
    return sliced.map((s) => ({
      name: s.name,
      cls: s.status === 'missing' ? 'is-missing' : s.status === 'short' ? 'is-short' : 'is-ok',
      status: sectionStatusText(s),
      tip: s.tip,
    }))
  }
  if (g.missingExpected && g.missingExpected.length) {
    return g.missingExpected.map((s) => ({
      name: s,
      cls: 'is-missing',
      status: '✗ Missing',
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
</script>

<template>
  <section class="wtp-card dash-main__guide">
    <div class="wtp-card__header">
      <h3 class="wtp-card__heading">Article Guide &amp; References</h3>
      <p class="wtp-card__sub">Analyse any Wikipedia article for structural gaps and suggest academic sources.</p>
    </div>

    <div class="guide-search-row">
      <div class="cdx-text-input" style="flex: 1">
        <input
          v-model="titleInput"
          class="cdx-text-input__input"
          type="text"
          placeholder="Enter any Wikipedia article title…"
          aria-label="Article title for guide"
          @keydown.enter="analyse"
        />
      </div>
      <button class="cdx-button cdx-button--action-progressive" @click="analyse">Analyse</button>
    </div>

    <div v-if="loading" style="display: flex; align-items: center; gap: 10px; padding: 16px; color: #54595d">
      <div class="loading-card__spinner" style="width: 24px; height: 24px; border-width: 2px; flex-shrink: 0"></div>
      Analysing <strong>{{ searchedTitle }}</strong>…
    </div>

    <div v-else-if="hasError" class="cdx-message cdx-message--error" style="margin-top: 8px">
      <span class="cdx-message__icon"></span>
      <div class="cdx-message__content">Could not load article guide. Make sure the title is exact.</div>
    </div>

    <div v-else-if="guideData" style="margin-top: 8px">
      <div
        style="
          display: flex;
          align-items: center;
          gap: 6px;
          flex-wrap: wrap;
          border-bottom: 1px solid #eaecf0;
          padding-bottom: 12px;
        "
      >
        <a
          :href="wikiUrl(searchedTitle)"
          target="_blank"
          style="font-family: 'Linux Libertine', Georgia, serif; font-size: 1.125rem; font-weight: bold"
        >{{ searchedTitle }}</a>
        <span class="wtp-badge wtp-badge--notice">{{ cap(guideData.articleType || 'general') }}</span>
        <span class="wtp-badge wtp-badge--neutral">{{ Math.round((guideData.currentSize || 0) / 1000) }}k chars</span>
        <span class="wtp-badge wtp-badge--neutral">{{ guideData.totalRefs || 0 }} refs</span>
        <span v-if="!guideData.hasInfobox" class="wtp-badge wtp-badge--warning">No infobox</span>
        <span v-if="!guideData.hasImages" class="wtp-badge wtp-badge--warning">No images</span>
        <a
          :href="editUrl(searchedTitle)"
          target="_blank"
          class="cdx-button cdx-button--action-progressive cdx-button--weight-primary"
          style="text-decoration: none; margin-left: auto"
        >
          Edit article
        </a>
      </div>

      <div style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #eaecf0">
        <template v-if="(guideData.suggestions || []).length">
          <div class="guide-col-title" style="margin-top: 16px">Overall Analysis: What to Edit</div>
          <div class="guide-suggestions">
            <div v-for="(s, i) in guideData.suggestions" :key="i" class="guide-suggestion">{{ s.text || s }}</div>
          </div>
        </template>

        <template v-if="sectionItems.length">
          <div class="guide-col-title" style="margin-top: 16px">Section Analysis</div>
          <div class="guide-section-list" style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px">
            <div v-for="(s, i) in sectionItems" :key="i" class="guide-section-item" :class="s.cls">
              <div class="guide-section-name">{{ s.name }}</div>
              <div class="guide-section-status">
                {{ s.status }}<template v-if="s.tip"> — {{ s.tip }}</template>
              </div>
            </div>
          </div>
        </template>
      </div>

      <div class="guide-result-grid">
        <div>
          <div class="guide-col-title" style="margin-bottom: 12px">Suggested Wikimedia References</div>
          <template v-if="wikiRefs.length">
            <div style="display: flex; flex-direction: column; gap: 6px">
              <div v-for="(r, i) in wikiRefs" :key="i" class="guide-ref-item" style="cursor: default">
                <a
                  :href="r.url || '#'"
                  target="_blank"
                  rel="noopener"
                  style="text-decoration: none; color: inherit; display: block"
                >
                  <div class="guide-ref-title">{{ r.title || 'Untitled' }}</div>
                  <div class="guide-ref-meta">
                    {{ r.authors || '' }}<template v-if="r.year"> · {{ r.year }}</template
                    ><template v-if="r.venue"> · {{ r.venue }}</template>
                  </div>
                  <div v-if="r.citations" class="guide-ref-source">{{ r.citations }} citations</div>
                </a>
                <details
                  v-if="(r.whatToEdit && r.whatToEdit.length) || (r.missingSections && r.missingSections.length)"
                  style="margin-top: 8px; cursor: pointer"
                >
                  <summary
                    style="
                      font-size: 0.8125rem;
                      color: #3366cc;
                      font-weight: bold;
                      outline: none;
                      user-select: none;
                    "
                  >
                    View missing items &amp; suggestions
                  </summary>
                  <div
                    style="
                      padding: 8px 12px;
                      background: #f8f9fa;
                      border-radius: 2px;
                      border: 1px solid #eaecf0;
                      margin-top: 6px;
                    "
                  >
                    <div v-if="r.whatToEdit && r.whatToEdit.length" style="margin-top: 8px; font-size: 0.85em; color: #202122">
                      <strong>What to Edit:</strong>
                      <ul style="padding-left: 16px; margin: 4px 0">
                        <li v-for="(s, j) in r.whatToEdit" :key="j">{{ s.text }}</li>
                      </ul>
                    </div>
                    <div
                      v-if="r.missingSections && r.missingSections.length"
                      style="margin-top: 4px; font-size: 0.85em; color: #d33"
                    >
                      <strong>Missing Sections:</strong> {{ r.missingSections.join(', ') }}
                    </div>
                  </div>
                </details>
              </div>
            </div>
            <button
              v-if="nextOffset"
              class="cdx-button"
              style="width: 100%; margin-top: 8px"
              :disabled="loadingMore"
              @click="loadMore"
            >
              {{ loadMoreError ? 'Error — try again' : loadingMore ? 'Loading…' : 'Load more references…' }}
            </button>
          </template>
          <div v-else class="empty-state">
            <div class="empty-state__icon">📄</div>
            No internal references found.
          </div>
        </div>

        <div>
          <div class="guide-col-title" style="margin-bottom: 12px">External Academic Research</div>
          <template v-if="extRefs.length">
            <div style="display: flex; flex-direction: column; gap: 6px">
              <a
                v-for="(r, i) in extRefs"
                :key="i"
                class="guide-ref-item"
                :href="r.url || '#'"
                target="_blank"
                rel="noopener"
                style="text-decoration: none; color: inherit; display: block"
              >
                <div class="guide-ref-title">{{ r.title || 'Untitled' }}</div>
                <div class="guide-ref-meta" style="margin-top: 6px">
                  <span class="wtp-badge wtp-badge--neutral" style="margin-right: 4px">{{ r.source }}</span>
                  <template v-if="r.citations !== null && r.citations !== undefined">{{ r.citations }} citations</template>
                </div>
              </a>
            </div>
          </template>
          <div v-else class="empty-state">
            <div class="empty-state__icon">📄</div>
            No external research found.
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
