import { defineStore } from 'pinia'
import { getProfile, getTrends, getTasks, getDiscover, getRevisit, getGeo } from '../api.js'

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

    // geo focus — dynamic place hierarchy (city/district/state/country) resolved via
    // Wikidata from the user's edited articles (prefetched in background, like discover)
    geo: null,
    geoLoading: false,
    geoError: '',

    // universal top-bar search -> Guide view
    guideQuery: '',
    guideQuerySeq: 0, // bumped on every dispatch so GuideView can react even to a repeated query

    tasksRequestSeq: 0, // guards against an older loadTasks() call resolving after a newer one
  }),

  getters: {
    // The most useful search term for region-specific tasks: the most-specific resolved
    // place that isn't just the top-level country itself (e.g. "Kerala" over "India") --
    // country-level alone is too broad to be an interesting regional signal. Falls back
    // to the country if nothing more specific resolved.
    geoFocusName(state) {
      const places = state.geo?.topPlaces || []
      const countryNames = new Set((state.geo?.topCountries || []).map((c) => c.name))
      const specific = places.find((p) => !countryNames.has(p.name))
      return specific?.name || state.geo?.topCountries?.[0]?.name || null
    },

    // The profile's edit-type histogram ({general: 788, references: 363, ...}) reduced to
    // the labels the backend's AFFINITY map is keyed on, strongest first.
    topEditTypes(state) {
      const counts = state.profile?.editTypes || {}
      return Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 6)
        .map(([name]) => name)
    },
  },

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
          this.loadTrends()
          this.fetchDiscover()
          this.fetchRevisit()
          // Load tasks immediately using the profile's own topics + edit types — those
          // alone already personalize the feed. Geo resolution is slow (many batched
          // Wikidata round-trips), so waiting on it meant a failed/empty geo left the
          // user permanently on the hardcoded generic feed. fetchGeo() re-runs this
          // once a place resolves; tasksRequestSeq keeps the later result authoritative.
          this.loadTasks()
          this.fetchGeo()
        })
        .catch((err) => {
          this.screen = 'onboard'
          this.onboardError = err.message || 'Failed to load profile. Please try again.'
        })
    },

    loadTrends() {
      this.trendsLoading = true
      getTrends()
        .then((t) => { this.trends = t })
        .catch(() => { /* keep last-known trends, if any */ })
        .finally(() => { this.trendsLoading = false })
    },

    loadTasks() {
      this.tasksLoading = true
      // loadTasks() can be called again (manual refresh) before an earlier call's request
      // has finished — whichever request completes last would otherwise silently win, even
      // if it was the older one. Guard against that by only applying a response if no newer
      // call has started since it went out.
      const seq = ++this.tasksRequestSeq
      getTasks({
        topics: this.profile?.topTopics,
        editTypes: this.topEditTypes,
        geo: this.geoFocusName,
      })
        .then((ts) => { if (this.tasksRequestSeq === seq) this.tasks = ts })
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

    fetchGeo() {
      this.geoLoading = true
      this.geoError = ''
      getGeo(this.username)
        .then((d) => { this.geo = d })
        .catch((err) => { this.geoError = err.message || 'Failed to load geographic focus.' })
        .finally(() => {
          this.geoLoading = false
          // Only re-fetch when a place actually resolved — the profile-based feed from
          // start() already stands, so a geo failure costs the regional bonus but never
          // triggers a redundant second request.
          if (this.geoFocusName) this.loadTasks()
        })
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
      this.geo = null
      this.geoError = ''
      this.guideQuery = ''
    },
  },
})
