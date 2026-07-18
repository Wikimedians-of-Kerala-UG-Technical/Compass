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

function getTasks() {
  return fetch(API_BASE + '/api/tasks')
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
