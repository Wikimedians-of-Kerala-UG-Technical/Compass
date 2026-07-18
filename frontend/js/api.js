function getProfile(username) { /* TODO: Contributor A */ }
function getTrends() {
  return fetch(API_BASE + '/api/trends').then(function (r) {
    if (!r.ok) throw new Error('Failed to load trends');
    return r.json();
  });
}
function getTasks() {
  return fetch(API_BASE + '/api/tasks').then(function (r) {
    if (!r.ok) throw new Error('Failed to load tasks');
    return r.json();
  });
}
function getGuide(title) { /* TODO: Contributor C */ }
function getReferences(title) { /* TODO: Contributor C */ }
