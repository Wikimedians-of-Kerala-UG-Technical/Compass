// Backend base URL: set VITE_API_BASE at build time for deployments.
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:5000'

function get(path, params, label) {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params || {})) {
    if (v !== undefined && v !== null && v !== '') q.set(k, v)
  }
  const url = API_BASE + path + (q.toString() ? '?' + q.toString() : '')
  return fetch(url).then((r) => {
    if (!r.ok) {
      return r
        .json()
        .catch(() => ({}))
        .then((e) => {
          throw new Error(e.error || `${label} error ${r.status}`)
        })
    }
    return r.json()
  })
}

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

export function getRevisit(username, wiki) {
  return get('/api/revisit/' + u(username), { wiki }, 'Revisit')
}

export function getContribute(username, { wiki, place } = {}) {
  return get('/api/contribute/' + u(username), { wiki, place: place?.qid, placeName: place?.name }, 'Contribute')
}
