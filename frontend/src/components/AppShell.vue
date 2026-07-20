<script setup>
import { ref, computed } from 'vue'
import { CdxTextInput, CdxButton, CdxIcon } from '@wikimedia/codex'
import {
  cdxIconArticleSearch,
  cdxIconHome,
  cdxIconCheckAll,
  cdxIconWatchlist,
  cdxIconLightbulb,
  cdxIconSearch,
  cdxIconReload,
  cdxIconLogOut,
} from '@wikimedia/codex-icons'
import { useAppStore } from '../stores/appStore.js'
import OverviewView from './views/OverviewView.vue'
import TasksView from './views/TasksView.vue'
import RevisitView from './views/RevisitView.vue'
import DiscoverView from './views/DiscoverView.vue'
import GuideView from './views/GuideView.vue'

const store = useAppStore()
const searchValue = ref('')

const navItems = computed(() => [
  { key: 'overview', label: 'Overview', icon: cdxIconHome },
  { key: 'tasks', label: 'Tasks', icon: cdxIconCheckAll, badge: store.tasks.length || null },
  {
    key: 'revisit',
    label: 'Revisit',
    icon: cdxIconWatchlist,
    badge: store.revisitLoading ? '…' : store.revisit.length || null,
  },
  {
    key: 'discover',
    label: 'Discover',
    icon: cdxIconLightbulb,
    badge: store.discoverLoading ? '…' : store.discover?.suggestedArticles?.length || null,
  },
  { key: 'guide', label: 'Guide', icon: cdxIconArticleSearch },
])

function runSearch() {
  const q = searchValue.value.trim()
  if (!q) return
  store.searchGuide(q)
  searchValue.value = ''
}
</script>

<template>
  <div class="shell">
    <header class="shell__topbar">
      <div class="shell__brand">
        <CdxIcon :icon="cdxIconArticleSearch" style="color: var(--color-progressive)" />
        <span class="serif">Compass</span>
      </div>

      <div class="shell__search" style="display: flex; gap: 6px">
        <CdxTextInput
          v-model="searchValue"
          :start-icon="cdxIconSearch"
          placeholder="Look up any article…"
          aria-label="Look up an article"
          style="flex: 1"
          @keydown.enter="runSearch"
        />
        <CdxButton weight="quiet" aria-label="Search" @click="runSearch">
          <CdxIcon :icon="cdxIconSearch" />
        </CdxButton>
      </div>

      <div class="shell__spacer"></div>

      <div class="shell__user">
        <span class="shell__username">{{ store.username }}</span>
        <CdxButton
          weight="quiet"
          title="Refresh trends and tasks"
          aria-label="Refresh trends and tasks"
          @click="store.loadTrendsAndTasks()"
        >
          <CdxIcon :icon="cdxIconReload" />
        </CdxButton>
        <CdxButton weight="quiet" action="destructive" @click="store.logout()">
          <CdxIcon :icon="cdxIconLogOut" />
          New user
        </CdxButton>
      </div>
    </header>

    <div class="shell__body">
      <nav class="shell__rail" aria-label="Sections">
        <button
          v-for="item in navItems"
          :key="item.key"
          class="rail-item"
          :class="{ 'is-active': store.activeView === item.key }"
          @click="store.goTo(item.key)"
        >
          <CdxIcon :icon="item.icon" />
          {{ item.label }}
          <span v-if="item.badge" class="rail-item__badge">{{ item.badge }}</span>
        </button>
      </nav>

      <main class="shell__content">
        <div class="view">
          <OverviewView v-if="store.activeView === 'overview'" />
          <TasksView v-else-if="store.activeView === 'tasks'" />
          <RevisitView v-else-if="store.activeView === 'revisit'" />
          <DiscoverView v-else-if="store.activeView === 'discover'" />
          <GuideView v-else-if="store.activeView === 'guide'" />
        </div>
      </main>
    </div>

    <nav class="bottom-nav" aria-label="Sections">
      <div class="bottom-nav__inner">
        <button
          v-for="item in navItems"
          :key="item.key"
          class="rail-item"
          :class="{ 'is-active': store.activeView === item.key }"
          @click="store.goTo(item.key)"
        >
          <CdxIcon :icon="item.icon" />
          {{ item.label }}
        </button>
      </div>
    </nav>
  </div>
</template>
