// Backend base URL: set VITE_API_BASE at build time for deployments. An empty value
// means "same origin" (the Docker image serves the API and the app together).
export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:5000'

function query(params) {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params || {})) {
    if (v !== undefined && v !== null && v !== '') q.set(k, v)
  }
  const s = q.toString()
  return s ? '?' + s : ''
}

function request(method, path, { params, body, label, headers } = {}) {
  const init = { method, credentials: 'include', headers: { ...(headers || {}) } }
  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json'
    init.body = JSON.stringify(body)
  }
  return fetch(API_BASE + path + query(params), init).then((r) => {
    if (!r.ok) {
      return r
        .json()
        .catch(() => ({}))
        .then((e) => {
          const err = new Error(e.error || `${label || 'Request'} error ${r.status}`)
          err.status = r.status
          err.suggestion = e.suggestion // e.g. the correctly capitalised username
          throw err
        })
    }
    return r.json()
  })
}

const get = (path, params, label) => request('GET', path, { params, label })
const u = encodeURIComponent

export function getProfile(username, wiki) {
  return get('/api/profile/' + u(username), { wiki }, 'Profile')
}

export function getTrends({ country, wiki, langs } = {}) {
  return get('/api/trends', { country, wiki, langs: (langs || []).join(',') }, 'Trends')
}

export function getTasks(username, { wiki, place } = {}) {
  return get(
    '/api/tasks/' + u(username),
    { wiki, lat: place?.coord?.lat, lon: place?.coord?.lon, place: place?.name },
    'Tasks'
  )
}

export function getGuide(title, wiki) {
  return get('/api/article/' + u(title) + '/guide', { wiki }, 'Guide')
}

export function getExternalReferences(title, wiki) {
  return get('/api/article/' + u(title) + '/external-references', { wiki }, 'References')
}

export function getDiscover(username, { wiki, region, local } = {}) {
  return get(
    '/api/discover/' + u(username),
    { wiki, region: region?.qid, local: local?.qid, regionName: region?.name },
    'Discover'
  )
}

export function getGeo(username, wiki) {
  return get('/api/geo/' + u(username), { wiki }, 'Geo')
}

export function getRevisit(username, wiki, { watchlist } = {}) {
  return watchlist
    ? get('/api/me/revisit', { wiki }, 'Revisit')
    : get('/api/revisit/' + u(username), { wiki }, 'Revisit')
}

export function getContribute(username, { wiki, place } = {}) {
  return get('/api/contribute/' + u(username), { wiki, place: place?.qid, placeName: place?.name }, 'Contribute')
}

export function getStats(username, wiki) {
  return get('/api/stats/' + u(username), { wiki }, 'Stats')
}

// Feedback on a task card: action is up | down | done | dismiss.
export function sendFeedback(task, username, action) {
  return request('POST', '/api/feedback', {
    label: 'Feedback',
    body: {
      username,
      wiki: task.wiki,
      title: task.title,
      action,
      type: task.type,
      scope: task.scope,
      signals: task.signals,
      score: task.score,
    },
  })
}

// Undo a vote: the editor's feedback on that article is removed.
export function clearFeedback(username, wiki, title) {
  return request('DELETE', '/api/feedback/' + u(username), { params: { wiki, title }, label: 'Undo' })
}

export function getFeedback(username, wiki) {
  return get('/api/feedback/' + u(username), { wiki }, 'Feedback')
}

// Login (optional; the server reports whether it's configured).
export function getAuthStatus() {
  return get('/api/auth/status', null, 'Login')
}

export function loginUrl(returnTo) {
  return API_BASE + '/api/auth/login' + query({ return: returnTo })
}

export function logout() {
  return request('POST', '/api/auth/logout', { label: 'Logout' })
}

export function getNewcomerTasks(wiki) {
  return get('/api/me/newcomer-tasks', { wiki }, 'Newcomer tasks')
}

// Live alerts (server-sent events). Returns the EventSource; the caller closes it.
export function openAlerts(username, wiki) {
  return new EventSource(API_BASE + '/api/alerts/' + u(username) + '/stream' + query({ wiki }), {
    withCredentials: true,
  })
}

// Events (Wikimedia Event Registration), with the worklist ranked per participant
export function resolveEvent(ref) {
  return get('/api/events/resolve', { ref }, 'Event')
}

export function getEvent(id) {
  return get('/api/events/' + u(id), null, 'Event')
}

export function rankEvent(id, username, wiki) {
  return get('/api/events/' + u(id) + '/rank/' + u(username), { wiki }, 'Ranking')
}
