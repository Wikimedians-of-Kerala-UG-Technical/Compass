const API_BASE = 'http://127.0.0.1:5000'

export function getProfile(username) {
  return fetch(API_BASE + '/api/profile/' + encodeURIComponent(username)).then((r) => {
    if (!r.ok) {
      return r.json().then((e) => {
        throw new Error(e.error || 'Profile API error ' + r.status)
      })
    }
    return r.json()
  })
}

export function getTrends() {
  return fetch(API_BASE + '/api/trends').then((r) => {
    if (!r.ok) throw new Error('Failed to load trends (' + r.status + ')')
    return r.json()
  })
}

export function getTasks({ topics, editTypes, geo } = {}) {
  // The backend falls back to a hardcoded generic topic list when `topics` is absent, and
  // its topic-weight / affinity scoring terms go inert without `topics` + `editTypes` — so
  // all three signals are forwarded, not just geo.
  const q = new URLSearchParams()
  if (topics && topics.length) q.set('topics', topics.join(','))
  if (editTypes && editTypes.length) q.set('editTypes', editTypes.join(','))
  if (geo) q.set('geo', geo)
  const params = q.toString() ? '?' + q.toString() : ''
  return fetch(API_BASE + '/api/tasks' + params).then((r) => {
    if (!r.ok) throw new Error('Failed to load tasks (' + r.status + ')')
    return r.json()
  })
}

export function getGuide(title) {
  return fetch(API_BASE + '/api/article/' + encodeURIComponent(title) + '/guide').then((r) => r.json())
}

export function getReferences(title, offset) {
  const off = offset || 0
  return fetch(
    API_BASE + '/api/article/' + encodeURIComponent(title) + '/references?offset=' + off
  ).then((r) => r.json())
}

export function getExternalReferences(title) {
  return fetch(
    API_BASE + '/api/article/' + encodeURIComponent(title) + '/external-references'
  ).then((r) => r.json())
}

export function getDiscover(username) {
  return fetch(API_BASE + '/api/discover/' + encodeURIComponent(username)).then((r) => {
    if (!r.ok) {
      return r.json().then((e) => {
        throw new Error(e.error || 'Discover API error ' + r.status)
      })
    }
    return r.json()
  })
}

export function getGeo(username) {
  return fetch(API_BASE + '/api/geo/' + encodeURIComponent(username)).then((r) => {
    if (!r.ok) {
      return r.json().then((e) => {
        throw new Error(e.error || 'Geo API error ' + r.status)
      })
    }
    return r.json()
  })
}

export function getRevisit(username, heavilyEdited, createdArticles) {
  const params = new URLSearchParams({
    watch: JSON.stringify(heavilyEdited || []),
    mine: JSON.stringify(createdArticles || []),
  })
  return fetch(API_BASE + '/api/revisit/' + encodeURIComponent(username) + '?' + params.toString()).then((r) => {
    if (!r.ok) {
      return r.json().then((e) => {
        throw new Error(e.error || 'Revisit API error ' + r.status)
      })
    }
    return r.json()
  })
}
