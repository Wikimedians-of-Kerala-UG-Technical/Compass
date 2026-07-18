document.addEventListener('DOMContentLoaded', function () {
  $('goBtn').addEventListener('click', function () { start(); });
  $('userInput').addEventListener('keydown', function (e) { if (e.key === 'Enter') start(); });
  $('refreshBtn').addEventListener('click', function () { loadTasksAndTrends(); });
  $('guideBtn').addEventListener('click', function () {
    var title = $('guideInput').value.trim();
    if (title) renderGuide(title);
  });
});

function start() {
  var username = $('userInput').value.trim();
  if (!username) return;
  state.username = username;
  $('navUser').textContent = username;
  show('loading');

  Promise.all([
    getProfile(username),
    getTrends(),
    getTasks()
  ]).then(function (results) {
    state.profile = results[0];
    state.trends = results[1];
    state.tasks = results[2];
    renderProfile();
    renderTrends();
    renderTasks();
    show('dash');
  }).catch(function (err) {
    show('onboard');
    $('errMsg').textContent = err.message || 'Something went wrong.';
  });
}

function loadTasksAndTrends() {
  Promise.all([getTrends(), getTasks()]).then(function (results) {
    state.trends = results[0];
    state.tasks = results[1];
    renderTrends();
    renderTasks();
  });
}
