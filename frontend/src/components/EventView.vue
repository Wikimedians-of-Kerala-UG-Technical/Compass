<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CdxTextInput, CdxButton, CdxMessage, CdxInfoChip, CdxField, CdxSelect } from '@wikimedia/codex'
import { resolveEvent, getEvent, rankEvent } from '../api.js'
import { useAppStore, urlName } from '../stores/appStore.js'
import LoadingState from './widgets/LoadingState.vue'

// An Event Registration event: everything about the event itself lives on Wikimedia
// (signup, worklist, progress). This page only orders the worklist for one editor.
const route = useRoute()
const router = useRouter()
const store = useAppStore()

const id = computed(() => route.params.id || '')
const eventRef = ref('')
const resolving = ref(false)
const event = ref(null)
const error = ref('')
const username = ref('')
const ranked = ref(null)
const ranking = ref(false)
const rankError = ref('')

const worklistTotal = computed(() => Object.values(event.value?.worklist || {}).reduce((n, t) => n + t.length, 0))
const wikiOptions = computed(() =>
  Object.entries(ranked.value?.wikis || {}).map(([w, n]) => ({ value: w, label: `${w} (${n})` })))
const day = (iso) => (iso ? iso.slice(0, 10) : '')

function open() {
  error.value = ''
  resolving.value = true
  resolveEvent(eventRef.value)
    .then((r) => router.push({ name: 'event', params: { id: r.id } }))
    .catch((e) => { error.value = e.message })
    .finally(() => { resolving.value = false })
}

function load() {
  event.value = null
  ranked.value = null
  error.value = ''
  if (!id.value) return
  getEvent(id.value)
    .then((e) => {
      event.value = e
      if (route.query.user) rank(String(route.query.user).replace(/_/g, ' '), route.query.wiki)
    })
    .catch((e) => { error.value = e.message })
}
watch(id, load, { immediate: true })
username.value = String(route.query.user || store.recent[0] || '').replace(/_/g, ' ')

function rank(name, wiki) {
  name = (name || username.value).trim()
  if (!name) return
  username.value = name
  rankError.value = ''
  ranking.value = true
  ranked.value = null
  // Keep it in the URL, so a participant can bookmark or share their own list.
  router.replace({ query: { user: urlName(name), ...(wiki ? { wiki } : {}) } })
  rankEvent(id.value, name, wiki)
    .then((r) => { ranked.value = r })
    .catch((e) => { rankError.value = e.message })
    .finally(() => { ranking.value = false })
}
</script>

<template>
  <div class="page">
    <h1 class="section-heading">{{ event ? event.name : $t('event.title') }}</h1>

    <template v-if="!id">
      <p class="section-sub">{{ $t('event.sub') }}</p>
      <form class="panel" @submit.prevent="open">
        <CdxField><template #label>{{ $t('event.refLabel') }}</template>
          <CdxTextInput v-model="eventRef" :placeholder="$t('event.refPlaceholder')" required />
        </CdxField>
        <CdxMessage v-if="error" type="error" style="margin: 12px 0">{{ error }}</CdxMessage>
        <CdxButton type="submit" action="progressive" weight="primary" :disabled="resolving">{{ $t('event.open') }}</CdxButton>
      </form>
    </template>

    <CdxMessage v-else-if="error" type="error">{{ error }}</CdxMessage>
    <LoadingState v-else-if="!event" :title="$t('app.loading')" />

    <template v-else>
      <p class="section-sub event-meta">
        <span>{{ $t('event.dates', { starts: day(event.starts), ends: day(event.ends) }) }}</span>
        <span>{{ $t('event.worklistSize', { n: worklistTotal }) }}</span>
        <a v-if="event.eventPageUrl" :href="event.eventPageUrl" target="_blank" rel="noopener">{{ $t('event.officialPage') }}</a>
        <a :href="event.detailsUrl" target="_blank" rel="noopener">{{ $t('event.progress') }}</a>
      </p>

      <CdxMessage v-if="!worklistTotal" type="notice" :allow-user-dismiss="false">{{ $t('event.noWorklist') }}</CdxMessage>

      <template v-else>
        <form class="panel rank-form" @submit.prevent="rank()">
          <CdxTextInput v-model="username" :placeholder="$t('event.usernameLabel')" :aria-label="$t('event.usernameLabel')" class="rank-form__input" />
          <CdxButton type="submit" action="progressive" weight="primary" :disabled="ranking">{{ $t('event.rank') }}</CdxButton>
        </form>
        <div v-if="event.participants.length" class="participants">
          <span class="participants__label">{{ $t('event.participants', { n: event.participants.length }) }}</span>
          <span v-for="p in event.participants" :key="p" class="recent-chip">
            <button class="recent-chip__name participant" @click="rank(p)">{{ p }}</button>
          </span>
        </div>

        <CdxMessage v-if="rankError" type="error" style="margin-top: 16px">{{ rankError }}</CdxMessage>
        <LoadingState v-if="ranking" :title="$t('event.ranking', { name: username })" />

        <template v-if="ranked">
          <div class="ranked-head">
            <div>
              <div class="section-title">{{ $t('event.rankedFor', { name: ranked.username }) }}</div>
              <p class="section-sub">{{ $t('event.rankedSub', { shown: ranked.items.length, total: ranked.total, wiki: ranked.wiki }) }}</p>
            </div>
            <CdxSelect v-if="wikiOptions.length > 1" :selected="ranked.wiki" :menu-items="wikiOptions"
              :aria-label="$t('event.wiki')" @update:selected="(w) => rank(ranked.username, w)" />
          </div>

          <div v-for="item in ranked.items" :key="item.title" class="item-card">
            <div class="item-card__head">
              <span class="item-card__title"><a :href="item.url" target="_blank" rel="noopener">{{ item.title }}</a></span>
              <CdxInfoChip v-if="item.meta" status="notice">{{ $t('tasks.minutes', { label: item.meta.label, min: item.meta.min }) }}</CdxInfoChip>
            </div>
            <div class="item-card__reason"><strong>{{ $t('tasks.whyYou') }}</strong> {{ item.reasons.join(' · ') }}</div>
            <div class="item-card__row">
              <CdxInfoChip v-for="n in item.needs" :key="n.key" status="warning">{{ n.label }}</CdxInfoChip>
              <span class="item-card__details">{{ item.details.join(' · ') }}</span>
            </div>
            <div class="item-card__actions">
              <a :href="item.editUrl" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary">{{ $t('app.editOnWikipedia') }}</a>
            </div>
          </div>

          <template v-if="ranked.toCreate.length">
            <div class="section-title" style="margin-top: 24px">{{ $t('event.toCreate', { n: ranked.toCreate.length }) }}</div>
            <p class="section-sub">{{ $t('event.toCreateSub', { wiki: ranked.wiki }) }}</p>
            <ul class="to-create">
              <li v-for="p in ranked.toCreate" :key="p.title">
                {{ p.title }} · <a :href="p.editUrl" target="_blank" rel="noopener">{{ $t('event.create') }}</a>
              </li>
            </ul>
          </template>
        </template>
      </template>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 860px; margin: 0 auto; padding: 32px 16px; }
.event-meta { display: flex; flex-wrap: wrap; gap: 4px 16px; }
.rank-form { display: flex; gap: 8px; flex-wrap: wrap; margin: 16px 0 8px; }
.rank-form__input { flex: 1; min-width: 200px; }
.participants { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; font-size: 0.8125rem; margin-bottom: 16px; }
.participants__label { color: var(--color-subtle); margin-right: 4px; }
.participant { padding-right: 12px; }
.ranked-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
.item-card__details { font-size: 0.75rem; color: var(--color-subtle); }
.to-create { font-size: 0.875rem; padding-left: 20px; }
</style>
