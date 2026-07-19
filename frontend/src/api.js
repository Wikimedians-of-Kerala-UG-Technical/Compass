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

export function getTasks() {
  return fetch(API_BASE + '/api/tasks').then((r) => {
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
