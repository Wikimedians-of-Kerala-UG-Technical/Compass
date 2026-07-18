function getProfile(username) { /* TODO: Contributor A */ }
function getTrends() { /* TODO: Contributor B */ }
function getTasks() { /* TODO: Contributor B */ }
function getGuide(title) {
  return fetch('http://localhost:5000/api/article/' + encodeURIComponent(title) + '/guide')
    .then(res => res.json());
}
function getReferences(title, offset = 0) {
  return fetch('http://localhost:5000/api/article/' + encodeURIComponent(title) + '/references?offset=' + offset)
    .then(res => res.json());
}
