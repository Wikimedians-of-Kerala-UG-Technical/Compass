function getProfile(username) {
  return fetch('http://127.0.0.1:5000/api/profile/' + encodeURIComponent(username))
    .then(function (r) {
      if (!r.ok) return r.json().then(function (e) { throw new Error(e.error || ('API ' + r.status)); });
      return r.json();
    });
}

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

function getGuide(title) {
  return fetch('http://localhost:5000/api/article/' + encodeURIComponent(title) + '/guide')
    .then(res => res.json());
}
function getReferences(title, offset = 0) {
  return fetch('http://localhost:5000/api/article/' + encodeURIComponent(title) + '/references?offset=' + offset)
    .then(res => res.json());
}

