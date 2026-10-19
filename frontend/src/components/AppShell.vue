<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
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
  cdxIconLogIn,
  cdxIconLogoWikimediaCommons,
  cdxIconChart,
  cdxIconBell,
  cdxIconBellOutline,
  cdxIconMoon,
  cdxIconBright,
  cdxIconUserAvatar,
} from '@wikimedia/codex-icons'
import { useAppStore } from '../stores/appStore.js'
import { loginUrl } from '../api.js'
import { getTheme, setTheme } from '../theme.js'
import OverviewView from './views/OverviewView.vue'
import TasksView from './views/TasksView.vue'
import RevisitView from './views/RevisitView.vue'
import DiscoverView from './views/DiscoverView.vue'
import GuideView from './views/GuideView.vue'
import ContributeView from './views/ContributeView.vue'
import StatsView from './views/StatsView.vue'

const store = useAppStore()
const { t } = useI18n()
const searchValue = ref('')
const theme = ref(getTheme())

const VIEWS = {
  overview: OverviewView,
  tasks: TasksView,
  revisit: RevisitView,
  discover: DiscoverView,
  contribute: ContributeView,
  guide: GuideView,
  stats: StatsView,
}

const navItems = computed(() => [
  { key: 'overview', label: t('nav.overview'), icon: cdxIconHome },
  { key: 'tasks', label: t('nav.tasks'), icon: cdxIconCheckAll, badge: store.tasksLoading && !store.tasks.length ? '…' : store.visibleTasks.length || null },
  { key: 'revisit', label: t('nav.revisit'), icon: cdxIconWatchlist, badge: store.revisitLoading ? '…' : store.revisit.length || null },
  {
    key: 'discover',
    label: t('nav.discover'),
    icon: cdxIconLightbulb,
    badge: store.discoverLoading ? '…' : (store.discover?.articles?.length || store.discover?.missingHere?.length || null),
  },
  { key: 'contribute', label: t('nav.contribute'), icon: cdxIconLogoWikimediaCommons, badge: store.contributeLoading ? '…' : store.contribute?.commons?.unused?.length || null },
  { key: 'guide', label: t('nav.guide'), icon: cdxIconArticleSearch },
  { key: 'stats', label: t('nav.stats'), icon: cdxIconChart },
])

// Cycles match-system -> dark -> light.
const nextTheme = { auto: 'dark', dark: 'light', light: 'auto' }
const themeLabel = computed(() => t('app.theme') + ': ' + t({ auto: 'app.themeAuto', dark: 'app.themeDark', light: 'app.themeLight' }[theme.value]))
function cycleTheme() {
  theme.value = nextTheme[theme.value]
  setTheme(theme.value)
}

function runSearch() {
  const q = searchValue.value.trim()
  if (!q) return
  store.searchGuide(q)
  searchValue.value = ''
}

function login() {
  window.location.href = loginUrl(window.location.href)
}
</script>

<template>
  <div class="shell">
    <header class="shell__topbar">
      <div class="shell__brand">
        <CdxIcon :icon="cdxIconArticleSearch" style="color: var(--color-progressive)" />
        <span class="serif">{{ $t('app.name') }}</span>
      </div>

      <div class="shell__search">
        <CdxTextInput
          v-model="searchValue"
          :start-icon="cdxIconSearch"
          :placeholder="$t('nav.search')"
          :aria-label="$t('nav.searchLabel')"
          style="flex: 1"
          @keydown.enter="runSearch"
        />
        <CdxButton weight="quiet" :aria-label="$t('nav.searchLabel')" @click="runSearch">
          <CdxIcon :icon="cdxIconSearch" />
        </CdxButton>
      </div>

      <div class="shell__spacer"></div>

      <div class="shell__user">
        <span class="shell__username">{{ store.username }}<template v-if="store.profile"> · {{ store.profile.homeLang }}.wikipedia</template></span>
        <CdxButton
          v-if="store.isSelf"
          weight="quiet"
          :title="store.alertsOn ? $t('nav.alertsOn') : $t('nav.alertsHint')"
          :aria-label="store.alertsOn ? $t('nav.alertsOn') : $t('nav.alertsOff')"
          :aria-pressed="store.alertsOn"
          @click="store.toggleAlerts()"
        >
          <CdxIcon :icon="store.alertsOn ? cdxIconBell : cdxIconBellOutline" />
        </CdxButton>
        <CdxButton weight="quiet" :title="themeLabel" :aria-label="themeLabel" @click="cycleTheme">
          <CdxIcon :icon="theme === 'light' ? cdxIconBright : cdxIconMoon" />
        </CdxButton>
        <CdxButton
          weight="quiet"
          :title="$t('nav.refresh')"
          :aria-label="$t('nav.refresh')"
          @click="store.loadTrends(); store.loadTasks()"
        >
          <CdxIcon :icon="cdxIconReload" />
        </CdxButton>
        <template v-if="store.auth.enabled">
          <CdxButton v-if="store.auth.username" weight="quiet" @click="store.logoutAccount()">
            <CdxIcon :icon="cdxIconLogOut" />
            <span class="shell__btn-label">{{ $t('nav.logout', { name: store.auth.username }) }}</span>
          </CdxButton>
          <CdxButton v-else weight="quiet" :title="$t('nav.loginHint')" @click="login">
            <CdxIcon :icon="cdxIconLogIn" />
            <span class="shell__btn-label">{{ $t('nav.login') }}</span>
          </CdxButton>
        </template>
        <CdxButton weight="quiet" action="destructive" :aria-label="$t('nav.newUser')" @click="store.logout()">
          <CdxIcon :icon="cdxIconUserAvatar" class="shell__narrow-only" />
          <span class="shell__btn-label">{{ $t('nav.newUser') }}</span>
        </CdxButton>
      </div>
    </header>

    <div class="shell__body">
      <nav class="shell__rail" :aria-label="$t('nav.sections')">
        <button
          v-for="item in navItems"
          :key="item.key"
          class="rail-item"
          :class="{ 'is-active': store.activeView === item.key }"
          :aria-current="store.activeView === item.key ? 'page' : undefined"
          @click="store.goTo(item.key)"
        >
          <CdxIcon :icon="item.icon" />
          {{ item.label }}
          <span v-if="item.badge" class="rail-item__badge">{{ item.badge }}</span>
        </button>
      </nav>

      <main class="shell__content">
        <div class="view">
          <component :is="VIEWS[store.activeView] || OverviewView" />
        </div>
      </main>
    </div>

    <nav class="bottom-nav" :aria-label="$t('nav.sections')">
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
