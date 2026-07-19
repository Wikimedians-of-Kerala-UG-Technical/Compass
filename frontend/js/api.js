/* api.js — all fetch wrappers */

function getProfile(username) {
  return fetch(API_BASE + '/api/profile/' + encodeURIComponent(username))
    .then(function (r) {
      if (!r.ok) return r.json().then(function (e) { throw new Error(e.error || 'Profile API error ' + r.status); });
      return r.json();
    });
}

function getTrends() {
  return fetch(API_BASE + '/api/trends')
    .then(function (r) {
      if (!r.ok) throw new Error('Failed to load trends (' + r.status + ')');
      return r.json();
    });
}

function getTasks(topics, editTypes, watchItems, mineTitles, geo) {
  var params = new URLSearchParams();
  if (topics && topics.length) params.set('topics', topics.join(','));
  if (editTypes && editTypes.length) params.set('editTypes', editTypes.join(','));
  if (watchItems && watchItems.length) params.set('watch', JSON.stringify(watchItems));
  if (mineTitles && mineTitles.length) params.set('mine', JSON.stringify(mineTitles));
  if (geo) params.set('geo', geo);
  var qs = params.toString();
  return fetch(API_BASE + '/api/tasks' + (qs ? '?' + qs : ''))
    .then(function (r) {
      if (!r.ok) throw new Error('Failed to load tasks (' + r.status + ')');
      return r.json();
    });
}

function getGuide(title) {
  return fetch(API_BASE + '/api/article/' + encodeURIComponent(title) + '/guide')
    .then(function (r) { return r.json(); });
}

function getReferences(title, offset) {
  var off = offset || 0;
  return fetch(API_BASE + '/api/article/' + encodeURIComponent(title) + '/references?offset=' + off)
    .then(function (r) { return r.json(); });
}

function getExternalReferences(title) {
  return fetch(API_BASE + '/api/article/' + encodeURIComponent(title) + '/external-references')
    .then(function (r) { return r.json(); });
}
