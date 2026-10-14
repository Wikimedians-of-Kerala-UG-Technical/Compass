import { defineStore } from 'pinia'
import {
  getProfile,
  getTrends,
  getTasks,
  getDiscover,
  getRevisit,
  getGeo,
  getContribute,
} from '../api.js'

export const useAppStore = defineStore('app', {
  state: () => ({
    // session
    screen: 'onboard', // 'onboard' | 'loading' | 'dash'
    username: '',
    onboardError: '',
    activeView: 'overview', // 'overview' | 'tasks' | 'revisit' | 'discover' | 'contribute' | 'guide'
    // Which Wikipedia to work on. null = the editor's home wiki (most edits), chosen by the backend.
    wiki: null,

    // profile (gates the transition out of onboarding)
    profile: null,

    trends: { news: [], trending: [] },
    trendsLoading: false,

    tasks: [],
    tasksMeta: null, // {scopes, candidates, partial}
    tasksLoading: false,
    tasksError: '',

    // revisit — the editor's own articles that need attention
    revisit: [],
    revisitLoading: false,
    revisitError: '',

    // geo focus — place hierarchy resolved via Wikidata from the edited articles
    geo: null,
    geoLoading: false,
    geoError: '',

    // discover — translation suggestions into the editor's languages
    discover: null,
    discoverLoading: false,
    discoverError: '',

    // contribute — Commons and Wikidata tasks
    contribute: null,
    contributeLoading: false,
    contributeError: '',

    // universal top-bar search -> Guide view
    guideQuery: '',
    guideWiki: '',
    guideQuerySeq: 0, // bumped on every dispatch so GuideView can react even to a repeated query

    tasksRequestSeq: 0, // guards against an older loadTasks() call resolving after a newer one
    sessionSeq: 0, // guards against responses for a previous user/wiki landing after a switch
  }),

  getters: {
    homeWiki: (state) => state.profile?.homeWiki || 'enwiki',
    // The district/city the editor works around most (inside their main region), used for
    // "near where you edit" tasks. Chosen by the backend from counts, not list order.
    geoLocal: (state) => state.geo?.focus?.local || null,
    geoRegion: (state) => state.geo?.focus?.region || null,
    countryA2: (state) => state.profile?.countries?.[0]?.a2 || null,
  },

  actions: {
    start(rawUsername, wiki) {
      const uname = (rawUsername || '').trim()
      if (!uname) {
        this.onboardError = 'Please enter a Wikipedia username.'
        return
      }
      this.onboardError = ''
      this.username = uname
      this.wiki = wiki || null
      this.screen = 'loading'
      const seq = ++this.sessionSeq
      this.resetData()

      getProfile(uname, this.wiki)
        .then((p) => {
          if (seq !== this.sessionSeq) return
          this.profile = p
          this.wiki = p.homeWiki
          this.screen = 'dash'
          this.loadTrends()
          this.fetchRevisit()
          // Tasks load straight away from the profile; geo is slower and, once it
          // resolves, adds a "near where you edit" source and the place-scoped extras.
          this.loadTasks()
          this.fetchGeo()
        })
        .catch((err) => {
          if (seq !== this.sessionSeq) return
          this.screen = 'onboard'
          this.onboardError = err.message || 'Failed to load profile. Please try again.'
        })
    },

    switchWiki(dbname) {
      if (!dbname || dbname === this.wiki) return
      const view = this.activeView
      this.start(this.username, dbname)
      this.activeView = view
    },

    resetData() {
      this.profile = null
      this.trends = { news: [], trending: [] }
      this.tasks = []
      this.tasksMeta = null
      this.tasksError = ''
      this.revisit = []
      this.revisitError = ''
      this.geo = null
      this.geoError = ''
      this.discover = null
      this.discoverError = ''
      this.contribute = null
      this.contributeError = ''
    },

    loadTrends() {
      this.trendsLoading = true
      const langs = (this.profile?.languages || []).map((l) => l.lang).filter((l) => l !== this.profile?.homeLang)
      getTrends({ country: this.countryA2, wiki: this.homeWiki, langs })
        .then((t) => { this.trends = t })
        .catch(() => { /* keep last-known trends, if any */ })
        .finally(() => { this.trendsLoading = false })
    },

    loadTasks() {
      this.tasksLoading = true
      this.tasksError = ''
      const seq = ++this.tasksRequestSeq
      getTasks(this.username, { wiki: this.wiki, place: this.geoLocal })
        .then((res) => {
          if (this.tasksRequestSeq !== seq) return
          this.tasks = res.tasks || []
          this.tasksMeta = res
        })
        .catch((err) => { if (this.tasksRequestSeq === seq) this.tasksError = err.message })
        .finally(() => { if (this.tasksRequestSeq === seq) this.tasksLoading = false })
    },

    fetchRevisit() {
      this.revisitLoading = true
      this.revisitError = ''
      const seq = this.sessionSeq
      getRevisit(this.username, this.wiki)
        .then((d) => { if (seq === this.sessionSeq) this.revisit = d.tasks || [] })
        .catch((err) => { if (seq === this.sessionSeq) this.revisitError = err.message || 'Failed to load your articles.' })
        .finally(() => { this.revisitLoading = false })
    },

    fetchGeo() {
      this.geoLoading = true
      this.geoError = ''
      const seq = this.sessionSeq
      getGeo(this.username, this.wiki)
        .then((d) => { if (seq === this.sessionSeq) this.geo = d })
        .catch((err) => { if (seq === this.sessionSeq) this.geoError = err.message || 'Failed to load geographic focus.' })
        .finally(() => {
          if (seq !== this.sessionSeq) return
          this.geoLoading = false
          if (this.geoLocal) this.loadTasks()
          this.fetchDiscover()
          this.fetchContribute()
        })
    },

    fetchDiscover() {
      this.discoverLoading = true
      this.discoverError = ''
      const seq = this.sessionSeq
      getDiscover(this.username, { wiki: this.wiki, region: this.geoRegion, local: this.geoLocal })
        .then((d) => { if (seq === this.sessionSeq) this.discover = d })
        .catch((err) => { if (seq === this.sessionSeq) this.discoverError = err.message || 'Failed to load suggestions.' })
        .finally(() => { this.discoverLoading = false })
    },

    fetchContribute() {
      this.contributeLoading = true
      this.contributeError = ''
      const seq = this.sessionSeq
      getContribute(this.username, { wiki: this.wiki, place: this.geoLocal || this.geoRegion })
        .then((d) => { if (seq === this.sessionSeq) this.contribute = d })
        .catch((err) => { if (seq === this.sessionSeq) this.contributeError = err.message || 'Failed to load Commons and Wikidata tasks.' })
        .finally(() => { this.contributeLoading = false })
    },

    goTo(view) {
      this.activeView = view
    },

    searchGuide(title, wiki) {
      this.guideQuery = (title || '').trim()
      this.guideWiki = wiki || this.wiki || 'enwiki'
      this.guideQuerySeq += 1
      this.activeView = 'guide'
    },

    logout() {
      this.sessionSeq += 1
      this.screen = 'onboard'
      this.username = ''
      this.onboardError = ''
      this.activeView = 'overview'
      this.wiki = null
      this.resetData()
      this.guideQuery = ''
    },
  },
})
