import { defineStore } from 'pinia'
import {
  getProfile,
  getTrends,
  getTasks,
  getDiscover,
  getRevisit,
  getGeo,
  getContribute,
  getStats,
  getFeedback,
  sendFeedback,
  openAlerts,
} from '../api.js'
import { router } from '../router.js'
import { i18n } from '../i18n.js'

const t = (...args) => i18n.global.t(...args)

const RECENT_KEY = 'compass-recent'
const RECENT_MAX = 6
const ALERTS_MAX = 30
const HIDDEN_ACTIONS = ['down', 'done', 'dismiss']
let alertSource = null // the open EventSource; not state, since it can't be serialised

// Usernames go in URLs with underscores, the way Wikipedia writes them.
export const urlName = (name) => (name || '').trim().replace(/ /g, '_')

function readRecent() {
  try {
    const list = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]')
    return Array.isArray(list) ? list.filter((n) => typeof n === 'string') : []
  } catch {
    return []
  }
}

function writeRecent(list) {
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(list))
  } catch {
    /* storage unavailable (private mode): the list just isn't remembered */
  }
}

export const useAppStore = defineStore('app', {
  state: () => ({
    // session
    screen: 'loading', // 'loading' | 'dash' (the start screen is its own route)
    username: '',
    onboardError: '',
    activeView: 'overview', // see VIEWS in router.js
    // Which Wikipedia to work on. null = the editor's home wiki (most edits), chosen by the backend.
    wiki: null,
    requestedWiki: null, // what the URL asked for, to tell a wiki switch from a reload
    recent: readRecent(),

    // profile (gates the transition out of loading)
    profile: null,

    trends: { news: [], trending: [] },
    trendsLoading: false,

    tasks: [],
    tasksMeta: null, // {scopes, candidates, partial, mode, hidden}
    tasksLoading: false,
    tasksError: '',

    // feedback on task cards: title -> latest action
    feedback: {},
    feedbackError: '',

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

    // stats — loaded when the Stats view is first opened
    stats: null,
    statsLoading: false,
    statsError: '',

    // live alerts (EventStreams via the backend)
    alertsOn: false,
    alerts: [],
    alertsWatching: 0,

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
    visibleTasks: (state) => state.tasks.filter((task) => !HIDDEN_ACTIONS.includes(state.feedback[task.title])),
  },

  actions: {
    // -- navigation (the URL is the source of truth; see DashboardRoute.vue) --
    open(rawUsername, wiki) {
      const uname = (rawUsername || '').trim()
      if (!uname) {
        this.onboardError = t('onboard.empty')
        return
      }
      this.onboardError = ''
      router.push({ name: 'dash', params: { username: urlName(uname) }, query: wiki ? { wiki } : {} })
    },

    goTo(view, extraQuery = {}) {
      const query = { ...(this.requestedWiki ? { wiki: this.requestedWiki } : {}), ...extraQuery }
      router.push({ name: 'dash', params: { username: urlName(this.username), view: view === 'overview' ? '' : view }, query })
    },

    switchWiki(dbname) {
      if (!dbname || dbname === this.wiki) return
      router.push({ name: 'dash', params: { username: urlName(this.username), view: this.activeView === 'overview' ? '' : this.activeView }, query: { wiki: dbname } })
    },

    searchGuide(title, wiki) {
      const q = (title || '').trim()
      if (!q) return
      const articleWiki = wiki || this.wiki || 'enwiki'
      this.goTo('guide', { article: q, ...(articleWiki !== this.wiki ? { articleWiki } : {}) })
    },

    // Called from the route. Starts a new session only when the user or wiki changed.
    syncFromRoute(route) {
      const uname = String(route.params.username || '').replace(/_/g, ' ').trim()
      const wiki = route.query.wiki ? String(route.query.wiki) : null
      this.activeView = route.params.view || 'overview'
      if (route.query.article) {
        const article = String(route.query.article)
        const articleWiki = route.query.articleWiki ? String(route.query.articleWiki) : null
        if (article !== this.guideQuery || (articleWiki || this.wiki) !== this.guideWiki) {
          this.guideQuery = article
          this.guideWiki = articleWiki || wiki || this.wiki || 'enwiki'
          this.guideQuerySeq += 1
        }
      }
      const sameUser = this.username && uname.toLowerCase() === this.username.toLowerCase()
      if (!sameUser || wiki !== this.requestedWiki || (!this.profile && this.screen !== 'loading')) {
        this.start(uname, wiki)
      }
      if (this.activeView === 'stats' && !this.stats && !this.statsLoading && this.profile) this.fetchStats()
    },

    start(uname, wiki) {
      this.username = uname
      this.wiki = wiki || null
      this.requestedWiki = wiki || null
      this.screen = 'loading'
      const seq = ++this.sessionSeq
      this.stopAlerts()
      this.resetData()

      getProfile(uname, this.wiki)
        .then((p) => {
          if (seq !== this.sessionSeq) return
          this.profile = p
          this.username = p.username
          this.wiki = p.homeWiki
          this.screen = 'dash'
          this.remember(p.username)
          this.loadFeedback()
          this.loadTrends()
          this.fetchRevisit()
          // Tasks load straight away from the profile; geo is slower and, once it
          // resolves, adds a "near where you edit" source and the place-scoped extras.
          this.loadTasks()
          this.fetchGeo()
          if (this.activeView === 'stats') this.fetchStats()
        })
        .catch((err) => {
          if (seq !== this.sessionSeq) return
          this.onboardError = err.message || t('onboard.failed')
          this.username = ''
          router.replace({ name: 'onboard' })
        })
    },

    remember(name) {
      this.recent = [name, ...this.recent.filter((n) => n !== name)].slice(0, RECENT_MAX)
      writeRecent(this.recent)
    },

    forget(name) {
      this.recent = this.recent.filter((n) => n !== name)
      writeRecent(this.recent)
    },

    resetData() {
      this.profile = null
      this.trends = { news: [], trending: [] }
      this.tasks = []
      this.tasksMeta = null
      this.tasksError = ''
      this.feedback = {}
      this.revisit = []
      this.revisitError = ''
      this.geo = null
      this.geoError = ''
      this.discover = null
      this.discoverError = ''
      this.contribute = null
      this.contributeError = ''
      this.stats = null
      this.statsError = ''
      this.alerts = []
    },

    // -- data --------------------------------------------------------------
    loadTrends() {
      this.trendsLoading = true
      const langs = (this.profile?.languages || []).map((l) => l.lang).filter((l) => l !== this.profile?.homeLang)
      getTrends({ country: this.countryA2, wiki: this.homeWiki, langs })
        .then((tr) => { this.trends = tr })
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

    loadFeedback() {
      const seq = this.sessionSeq
      getFeedback(this.username, this.wiki)
        .then((d) => {
          if (seq !== this.sessionSeq) return
          this.feedback = Object.fromEntries((d.items || []).map((i) => [i.title, i.action]))
        })
        .catch(() => { /* votes are optional */ })
    },

    vote(task, action) {
      const before = this.feedback[task.title]
      this.feedback = { ...this.feedback, [task.title]: action }
      this.feedbackError = ''
      return sendFeedback(task, this.username, action).catch(() => {
        this.feedback = { ...this.feedback, [task.title]: before }
        this.feedbackError = t('tasks.voteFailed')
      })
    },

    fetchRevisit() {
      this.revisitLoading = true
      this.revisitError = ''
      const seq = this.sessionSeq
      getRevisit(this.username, this.wiki)
        .then((d) => {
          if (seq !== this.sessionSeq) return
          this.revisit = d.tasks || []
        })
        .catch((err) => { if (seq === this.sessionSeq) this.revisitError = err.message || t('revisit.failed') })
        .finally(() => { this.revisitLoading = false })
    },

    fetchGeo() {
      this.geoLoading = true
      this.geoError = ''
      const seq = this.sessionSeq
      getGeo(this.username, this.wiki)
        .then((d) => { if (seq === this.sessionSeq) this.geo = d })
        .catch((err) => { if (seq === this.sessionSeq) this.geoError = err.message })
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
        .catch((err) => { if (seq === this.sessionSeq) this.discoverError = err.message || t('discover.failed') })
        .finally(() => { this.discoverLoading = false })
    },

    fetchContribute() {
      this.contributeLoading = true
      this.contributeError = ''
      const seq = this.sessionSeq
      getContribute(this.username, { wiki: this.wiki, place: this.geoLocal || this.geoRegion })
        .then((d) => { if (seq === this.sessionSeq) this.contribute = d })
        .catch((err) => { if (seq === this.sessionSeq) this.contributeError = err.message || t('contribute.failed') })
        .finally(() => { this.contributeLoading = false })
    },

    fetchStats() {
      this.statsLoading = true
      this.statsError = ''
      const seq = this.sessionSeq
      getStats(this.username, this.wiki)
        .then((d) => { if (seq === this.sessionSeq) this.stats = d })
        .catch((err) => { if (seq === this.sessionSeq) this.statsError = err.message || t('stats.failed') })
        .finally(() => { this.statsLoading = false })
    },

    // -- live alerts -----------------------------------------------------------
    toggleAlerts() {
      if (this.alertsOn) {
        this.stopAlerts()
        return
      }
      if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
        Notification.requestPermission().catch(() => {})
      }
      this.startAlerts()
    },

    startAlerts() {
      this.stopAlerts()
      const source = openAlerts(this.username, this.wiki)
      alertSource = source
      this.alertsOn = true
      source.addEventListener('ready', (e) => {
        try { this.alertsWatching = JSON.parse(e.data).watching } catch { /* ignore */ }
      })
      source.addEventListener('alert', (e) => {
        let alert
        try { alert = JSON.parse(e.data) } catch { return }
        this.alerts = [alert, ...this.alerts].slice(0, ALERTS_MAX)
        notify(alert)
      })
      // EventSource reconnects by itself after a dropped connection.
    },

    stopAlerts() {
      if (alertSource) alertSource.close()
      alertSource = null
      this.alertsOn = false
    },

    logout() {
      this.sessionSeq += 1
      this.stopAlerts()
      // Leave the dashboard before clearing its data: the views assume a profile and
      // would crash rendering a null one.
      return router.push({ name: 'onboard' }).finally(() => {
        this.username = ''
        this.onboardError = ''
        this.activeView = 'overview'
        this.wiki = null
        this.requestedWiki = null
        this.resetData()
        this.guideQuery = ''
      })
    },
  },
})

export function alertText(alert) {
  if (alert.kind === 'edit') return t('overview.liveEdit', { user: alert.user, title: alert.title })
  if (alert.kind === 'tagged') return t('overview.liveTagged', { title: alert.title, label: alert.label })
  return t('overview.liveUntagged', { title: alert.title, label: alert.label })
}

function notify(alert) {
  if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return
  if (typeof document !== 'undefined' && document.visibilityState === 'visible') return // it's on screen already
  try {
    const n = new Notification(t('app.name'), { body: alertText(alert), tag: `${alert.wiki}:${alert.title}` })
    n.onclick = () => window.open(alert.diffUrl || alert.url, '_blank', 'noopener')
  } catch {
    /* some browsers only allow notifications from a service worker */
  }
}
