function getProfile(username) {
  return fetch('http://127.0.0.1:5000/api/profile/' + encodeURIComponent(username))
    .then(function (r) {
      if (!r.ok) return r.json().then(function (e) { throw new Error(e.error || ('API ' + r.status)); });
      return r.json();
    });
}