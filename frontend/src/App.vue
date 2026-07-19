<script setup>
import { ref } from 'vue'
import ProfileView from './components/ProfileView.vue'
import LoadingScreen from './components/LoadingScreen.vue'
import TrendingBox from './components/TrendingBox.vue'
import NewsBox from './components/NewsBox.vue'
import TaskList from './components/TaskList.vue'
import GuidePanel from './components/GuidePanel.vue'
import { getProfile, getTrends, getTasks } from './api.js'

const screen = ref('onboard') // 'onboard' | 'loading' | 'dash'
const username = ref('')
const profile = ref(null)
const trends = ref({ news: [], trending: [] })
const tasks = ref([])
const errorMsg = ref('')
const refreshing = ref(false)

const loadStatus = ref('Starting…')
const loadSub = ref('Connecting to Wikipedia…')
const loadProgress = ref(0)
const stageNum = ref(1)

function setProgress(pct, title, sub) {
  loadProgress.value = pct
  loadStatus.value = title
  loadSub.value = sub
}

function start(rawUsername) {
  const uname = (rawUsername || '').trim()
  if (!uname) {
    errorMsg.value = 'Please enter a Wikipedia username.'
    return
  }
  errorMsg.value = ''
  username.value = uname

  screen.value = 'loading'
  setProgress(5, 'Connecting…', 'Establishing connection to Wikipedia API')
  stageNum.value = 1

  const stageTimers = [
    setTimeout(() => {
      stageNum.value = 2
      setProgress(20, 'Building profile…', 'Analysing your edit history')
    }, 400),
    setTimeout(() => {
      stageNum.value = 3
      setProgress(45, 'Scanning trends…', 'Fetching current events & trending articles')
    }, 1200),
    setTimeout(() => {
      stageNum.value = 4
      setProgress(65, 'Finding gaps…', 'Searching for articles needing attention')
    }, 2200),
    setTimeout(() => {
      stageNum.value = 5
      setProgress(85, 'Scoring tasks…', 'Ranking recommendations for you')
    }, 3200),
  ]

  Promise.all([getProfile(uname), getTrends(), getTasks()])
    .then(([p, t, ts]) => {
      stageTimers.forEach(clearTimeout)
      setProgress(100, 'Done!', 'Loading your dashboard…')
      stageNum.value = 6

      profile.value = p
      trends.value = t
      tasks.value = ts

      setTimeout(() => {
        screen.value = 'dash'
      }, 350)
    })
    .catch((err) => {
      stageTimers.forEach(clearTimeout)
      screen.value = 'onboard'
      errorMsg.value = err.message || 'Failed to load data. Please try again.'
    })
}

function refreshDash() {
  refreshing.value = true
  Promise.all([getTrends(), getTasks()])
    .then(([t, ts]) => {
      trends.value = t
      tasks.value = ts
    })
    .catch(() => {
      /* silent fail — show stale data */
    })
    .finally(() => {
      refreshing.value = false
    })
}

function logout() {
  username.value = ''
  profile.value = null
  tasks.value = []
  trends.value = { news: [], trending: [] }
  errorMsg.value = ''
  screen.value = 'onboard'
}
</script>

<template>
  <header class="wtp-header">
    <div class="wtp-header__inner">
      <div class="wtp-header__brand">
        <svg class="wtp-logo" viewBox="0 0 36 36" aria-hidden="true">
          <circle cx="18" cy="18" r="17" fill="#fff" stroke="#a2a9b1" stroke-width="1" />
          <text
            x="18"
            y="23"
            text-anchor="middle"
            font-family="'Linux Libertine',Georgia,serif"
            font-size="18"
            font-weight="bold"
            fill="#202122"
          >W</text>
        </svg>
        <span class="wtp-header__title">WikiTask Pro</span>
      </div>
      <div class="wtp-header__right">
        <span class="wtp-header__user">{{ username }}</span>
      </div>
    </div>
  </header>

  <main v-if="screen === 'onboard'" class="screen active" id="onboard" role="main">
    <ProfileView :error-msg="errorMsg" @submit="start" />
  </main>

  <main v-else-if="screen === 'loading'" class="screen active" id="loading" role="main" aria-live="polite">
    <LoadingScreen :status="loadStatus" :sub="loadSub" :progress="loadProgress" :stage="stageNum" />
  </main>

  <main v-else class="screen active" id="dash" role="main">
    <div class="dash-toolbar">
      <div class="dash-toolbar__inner">
        <h2 class="dash-toolbar__title">Dashboard</h2>
        <div class="dash-toolbar__actions">
          <button class="cdx-button" :disabled="refreshing" title="Refresh trends and tasks" @click="refreshDash">
            {{ refreshing ? 'Refreshing…' : '↻ Refresh' }}
          </button>
          <button class="cdx-button cdx-button--action-destructive" @click="logout">← New user</button>
        </div>
      </div>
    </div>

    <div class="dash-grid">
      <aside class="dash-sidebar">
        <ProfileView :profile="profile" :username="username" />
        <TrendingBox :trending="trends.trending" />
        <NewsBox :news="trends.news" />
      </aside>

      <div class="dash-main">
        <TaskList :tasks="tasks" />
        <GuidePanel />
      </div>
    </div>
  </main>
</template>
