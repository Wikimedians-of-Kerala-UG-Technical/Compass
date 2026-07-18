function $(id) { return document.getElementById(id); }
function show(id) {
  document.querySelectorAll('.screen').forEach(function (s) { s.classList.remove('active'); });
  $(id).classList.add('active');
}
function setStage(n) {
  for (var i = 1; i <= 6; i++) {
    $('s' + i).className = 'stg' + (i < n ? ' done' : i === n ? ' now' : '');
  }
}

document.addEventListener('DOMContentLoaded', function () {
  $('goBtn').addEventListener('click', startProfileLookup);
  $('userInput').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') startProfileLookup();
  });
});

function startProfileLookup() {
  var username = $('userInput').value.trim();
  if (!username) { $('errMsg').textContent = 'Please enter a username'; return; }
  $('errMsg').textContent = '';
  $('goBtn').disabled = true;
  $('navUser').textContent = username;

  show('loading');
  $('progFill').style.width = '0%';
  setStage(1);
  $('loadStatus').textContent = 'Fetching edit history…';

  setTimeout(function () {
    setStage(2);
    $('progFill').style.width = '50%';
    $('loadStatus').textContent = 'Building profile…';
  }, 300);

  getProfile(username)
    .then(function (profile) {
      $('progFill').style.width = '100%';
      renderProfileCard(profile);
      show('dash');
      $('goBtn').disabled = false;
    })
    .catch(function (e) {
      show('onboard');
      $('goBtn').disabled = false;
      $('errMsg').textContent = 'Error: ' + e.message;
    });
}

function renderProfileCard(p) {
  var topEditTypes = Object.entries(p.editTypes || {})
    .sort(function (a, b) { return b[1] - a[1]; })
    .slice(0, 5)
    .map(function (e) { return e[0] + ' (' + e[1] + ')'; })
    .join(', ');

  $('profileCard').innerHTML =
    '<div class="profile-card">' +
      '<div class="pc-row">' +
        '<div class="pc-stat"><div class="pc-num">' + p.total + '</div><div class="pc-label">Edits</div></div>' +
        '<div class="pc-stat"><div class="pc-num">' + p.uniqueArticles + '</div><div class="pc-label">Articles</div></div>' +
      '</div>' +
      '<div class="pc-section"><div class="pc-section-title">Top Topics</div>' +
        '<div class="pref-row">' + (p.topTopics || []).map(function (t) { return '<span class="pref-item">' + t + '</span>'; }).join('') + '</div>' +
      '</div>' +
      '<div class="pc-section"><div class="pc-section-title">Edit Types</div><div class="pref-row">' + topEditTypes + '</div></div>' +
    '</div>';
}