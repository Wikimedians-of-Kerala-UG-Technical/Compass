import { defineStore } from 'pinia'
import { getProfile, getTrends, getTasks, getDiscover, getRevisit } from '../api.js'

export const useAppStore = defineStore('app', {
  state: () => ({
    // session
    screen: 'onboard', // 'onboard' | 'loading' | 'dash'
    username: '',
    onboardError: '',
    activeView: 'overview', // 'overview' | 'tasks' | 'revisit' | 'discover' | 'guide'

    // profile (gates the transition out of onboarding)
    profile: null,

    // trends + tasks (loaded independently, in parallel, after profile resolves)
    trends: { news: [], trending: [] },
    trendsLoading: false,
    tasks: [],
    tasksLoading: false,

    // discover (prefetched in background right after profile resolves)
    discover: null,
    discoverLoading: false,
    discoverError: '',

    // revisit — the user's own heavily-edited/created articles that have picked up
    // maintenance issues (prefetched in background right after profile resolves)
    revisit: [],
    revisitLoading: false,
    revisitError: '',

    // universal top-bar search -> Guide view
    guideQuery: '',
    guideQuerySeq: 0, // bumped on every dispatch so GuideView can react even to a repeated query
  }),

  actions: {
    start(rawUsername) {
      const uname = (rawUsername || '').trim()
      if (!uname) {
        this.onboardError = 'Please enter a Wikipedia username.'
        return
      }
      this.onboardError = ''
      this.username = uname
      this.screen = 'loading'

      getProfile(uname)
        .then((p) => {
          this.profile = p
          this.screen = 'dash'
          this.activeView = 'overview'
          this.loadTrendsAndTasks()
          this.fetchDiscover()
          this.fetchRevisit()
        })
        .catch((err) => {
          this.screen = 'onboard'
          this.onboardError = err.message || 'Failed to load profile. Please try again.'
        })
    },

    loadTrendsAndTasks() {
      this.trendsLoading = true
      this.tasksLoading = true
      getTrends()
        .then((t) => { this.trends = t })
        .catch(() => { /* keep last-known trends, if any */ })
        .finally(() => { this.trendsLoading = false })
      getTasks()
        .then((ts) => { this.tasks = ts })
        .catch(() => { /* keep last-known tasks, if any */ })
        .finally(() => { this.tasksLoading = false })
    },

    fetchDiscover() {
      this.discoverLoading = true
      this.discoverError = ''
      getDiscover(this.username)
        .then((d) => { this.discover = d })
        .catch((err) => { this.discoverError = err.message || 'Failed to load suggestions.' })
        .finally(() => { this.discoverLoading = false })
    },

    fetchRevisit() {
      this.revisitLoading = true
      this.revisitError = ''
      getRevisit(this.username, this.profile?.heavilyEdited, this.profile?.createdArticles)
        .then((d) => { this.revisit = d.tasks || [] })
        .catch((err) => { this.revisitError = err.message || 'Failed to load your articles.' })
        .finally(() => { this.revisitLoading = false })
    },

    goTo(view) {
      this.activeView = view
    },

    searchGuide(title) {
      this.guideQuery = (title || '').trim()
      this.guideQuerySeq += 1
      this.activeView = 'guide'
    },

    logout() {
      this.screen = 'onboard'
      this.username = ''
      this.onboardError = ''
      this.activeView = 'overview'
      this.profile = null
      this.trends = { news: [], trending: [] }
      this.tasks = []
      this.discover = null
      this.discoverError = ''
      this.revisit = []
      this.revisitError = ''
      this.guideQuery = ''
    },
  },
})
