<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxIcon, CdxInfoChip } from '@wikimedia/codex'
import { cdxIconChartLine } from '@wikimedia/codex-icons'
import { useAppStore } from '../../stores/appStore.js'

const store = useAppStore()
const { t } = useI18n()

const items = computed(() => (store.trends.trending || []).slice(0, 8))
const where = computed(() => {
  const country = store.profile?.countries?.[0]?.name
  const wiki = store.profile?.homeLang && `${store.profile.homeLang}.wikipedia`
  const parts = [country && t('trends.readersIn', { country }), wiki].filter(Boolean)
  return parts.length === 2 ? t('trends.and', { a: parts[0], b: parts[1] }) : parts[0] || ''
})

function views(n) {
  return n >= 1000 ? Math.round(n / 1000) + 'k' : n
}
</script>

<template>
  <section class="panel" :aria-label="$t('trends.label')">
    <div class="section-title" style="display: flex; align-items: center; gap: 6px">
      <CdxIcon :icon="cdxIconChartLine" size="small" />
      {{ $t('trends.title') }}
    </div>
    <p v-if="where" style="font-size: 0.75rem; color: var(--color-subtle); margin-bottom: 8px">{{ $t('trends.where', { where }) }}</p>

    <div v-if="store.trendsLoading" class="fade-in">
      <div class="skeleton-line skeleton-line--wide"></div>
      <div class="skeleton-line skeleton-line--narrow"></div>
      <div class="skeleton-line"></div>
    </div>

    <div v-else-if="items.length" style="display: flex; flex-direction: column; gap: 8px">
      <div v-for="item in items" :key="item.wiki + item.title" style="font-size: 0.8125rem">
        <a :href="item.editUrl" target="_blank" rel="noopener">{{ item.title }}</a>
        <span style="color: var(--color-subtle)"> · {{ $t('trends.views', { n: views(item.views) }) }}<template v-if="item.wiki !== 'enwiki'"> · {{ item.wiki.replace(/wiki$/, '') }}</template></span>
        <div style="margin-top: 2px">
          <CdxInfoChip v-for="i in item.issues" :key="i.key" status="warning" style="margin-right: 4px">{{ i.label }}</CdxInfoChip>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">{{ $t('trends.none') }}</div>
  </section>
</template>
