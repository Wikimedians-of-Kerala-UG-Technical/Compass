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
  clearFeedback,
  getAuthStatus,
  getNewcomerTasks,
  logout as apiLogout,
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

// Votes on someone else's dashboard stay in this browser: they're the visitor's own
// bookmarks and never change that editor's list or what Compass learns.
const localVotesKey = (username, wiki) => `compass-votes:${wiki}:${username}`

function readLocalVotes(username, wiki) {
  try {
    const votes = JSON.parse(localStorage.getItem(localVotesKey(username, wiki)) || '{}')
    return votes && typeof votes === 'object' && !Array.isArray(votes) ? votes : {}
  } catch {
    return {}
  }
}

function writeLocalVotes(username, wiki, votes) {
  try {
    localStorage.setItem(localVotesKey(username, wiki), JSON.stringify(votes))
  } catch {
    /* private mode or storage full: the votes just won't survive a reload */
  }
}

// The ranked tasks plus the ones the server held back because of an earlier vote.
function allTasks(state) {
  const shown = new Set(state.tasks.map((task) => task.title))
  return [...state.tasks, ...state.hiddenTasks.filter((task) => !shown.has(task.title))]
}

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
    onboardSuggestion: '', // an existing username that differs only in capitalisation
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
    hiddenTasks: [], // tasks the server left out because of an earlier vote, kept so they can be restored
    tasksLoading: false,
    tasksError: '',
    newcomerTasks: [], // logged-in newcomers: Growth's list for their Special:Homepage topics

    // feedback on task cards: title -> latest action
    feedback: {},
    feedbackError: '',
    lastHidden: null, // {task, action}: the card that just disappeared, for the Undo bar

    // revisit — the editor's own articles that need attention
    revisit: [],
    revisitWatchlist: 0,
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

    // optional login
    auth: { enabled: false, username: null },

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
    // Logged in as the editor whose dashboard this is (not just anyone who's logged in).
    isSelf: (state) => !!state.auth.username && state.auth.username === state.profile?.username,
    voteWiki: (state) => state.wiki || state.profile?.homeWiki || 'enwiki',
    visibleTasks: (state) => allTasks(state).filter((task) => !HIDDEN_ACTIONS.includes(state.feedback[task.title])),
    // Everything voted out of the list, newest data first; titles known only from old votes
    // (no longer among the candidates) are listed by name so they can still be restored.
    hiddenList: (state) => {
      const known = allTasks(state).filter((task) => HIDDEN_ACTIONS.includes(state.feedback[task.title]))
      const titles = new Set(known.map((task) => task.title))
      const onlyVoted = Object.entries(state.feedback)
        .filter(([title, action]) => HIDDEN_ACTIONS.includes(action) && !titles.has(title))
        .map(([title]) => ({ title, wiki: state.wiki || state.profile?.homeWiki }))
      return [...known, ...onlyVoted].map((task) => ({ ...task, action: state.feedback[task.title] }))
    },
  },

  actions: {
    // -- navigation (the URL is the source of truth; see DashboardRoute.vue) --
    open(rawUsername, wiki) {
      const uname = (rawUsername || '').trim()
      if (!uname) {
        this.onboardError = t('onboard.empty')
        this.onboardSuggestion = ''
        return
      }
      this.onboardError = ''
      this.onboardSuggestion = ''
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
          this.onboardSuggestion = err.suggestion || ''
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
      this.newcomerTasks = []
      this.feedback = {}
      this.hiddenTasks = []
      this.lastHidden = null
      this.revisit = []
      this.revisitWatchlist = 0
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
          this.hiddenTasks = res.hiddenTasks || []
          this.tasksMeta = res
          if (res.mode === 'guided' && this.isSelf) this.loadNewcomerTasks()
        })
        .catch((err) => { if (this.tasksRequestSeq === seq) this.tasksError = err.message })
        .finally(() => { if (this.tasksRequestSeq === seq) this.tasksLoading = false })
    },

    loadNewcomerTasks() {
      const seq = this.sessionSeq
      getNewcomerTasks(this.wiki)
        .then((d) => { if (seq === this.sessionSeq) this.newcomerTasks = d.tasks || [] })
        .catch(() => { /* optional extra; the regular guided tasks are still there */ })
    },

    loadFeedback() {
      if (!this.isSelf) {
        this.feedback = readLocalVotes(this.username, this.voteWiki)
        return
      }
      const seq = this.sessionSeq
      getFeedback(this.username, this.wiki)
        .then((d) => {
          if (seq !== this.sessionSeq) return
          this.feedback = Object.fromEntries((d.items || []).map((i) => [i.title, i.action]))
        })
        .catch(() => { /* votes are optional */ })
    },

    vote(task, action) {
      // Clicking the vote that's already on takes it back.
      if (this.feedback[task.title] === action) return this.unvote(task)
      const before = this.feedback[task.title]
      this.feedback = { ...this.feedback, [task.title]: action }
      this.feedbackError = ''
      this.lastHidden = HIDDEN_ACTIONS.includes(action) ? { task, action } : null
      if (!this.isSelf) {
        writeLocalVotes(this.username, this.voteWiki, this.feedback)
        return Promise.resolve()
      }
      return sendFeedback(task, this.username, action).catch(() => {
        this.feedback = { ...this.feedback, [task.title]: before }
        this.lastHidden = null
        this.feedbackError = t('tasks.voteFailed')
      })
    },

    unvote(task) {
      const before = this.feedback[task.title]
      const rest = { ...this.feedback }
      delete rest[task.title]
      this.feedback = rest
      this.feedbackError = ''
      if (this.lastHidden?.task.title === task.title) this.lastHidden = null
      if (!this.isSelf) {
        writeLocalVotes(this.username, this.voteWiki, this.feedback)
        return Promise.resolve()
      }
      return clearFeedback(this.username, task.wiki || this.wiki || this.profile?.homeWiki, task.title).catch(() => {
        this.feedback = { ...this.feedback, [task.title]: before }
        this.feedbackError = t('tasks.voteFailed')
      })
    },

    fetchRevisit() {
      this.revisitLoading = true
      this.revisitError = ''
      const seq = this.sessionSeq
      getRevisit(this.username, this.wiki, { watchlist: this.isSelf })
        .then((d) => {
          if (seq !== this.sessionSeq) return
          this.revisit = d.tasks || []
          this.revisitWatchlist = d.watchlist || 0
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

    // -- login ---------------------------------------------------------------
    loadAuth() {
      return getAuthStatus()
        .then((a) => { this.auth = a })
        .catch(() => { this.auth = { enabled: false, username: null } })
    },

    logoutAccount() {
      return apiLogout().finally(() => {
        this.auth = { ...this.auth, username: null }
        if (this.profile) this.fetchRevisit()
      })
    },

    // -- live alerts -----------------------------------------------------------
    toggleAlerts() {
      if (!this.isSelf) return // live alerts are only for the editor's own articles
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
        this.onboardSuggestion = ''
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
