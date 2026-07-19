/* main.js — application bootstrap and event wiring */

document.addEventListener('DOMContentLoaded', function () {

  /* ── Onboarding ──────────────────────────────────────── */
  document.getElementById('goBtn').addEventListener('click', start);
  document.getElementById('userInput').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') start();
  });

  /* ── Dashboard toolbar ───────────────────────────────── */
  var refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) refreshBtn.addEventListener('click', refreshDash);

  var logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) logoutBtn.addEventListener('click', function () {
    state.username = '';
    state.profile  = null;
    state.tasks    = [];
    state.trends   = {};
    document.getElementById('userInput').value = '';
    document.getElementById('navUser').textContent = '';
    document.getElementById('errMsg').style.display = 'none';
    show('onboard');
  });

  /* ── Article guide ───────────────────────────────────── */
  var guideBtn   = document.getElementById('guideBtn');
  var guideInput = document.getElementById('guideInput');
  if (guideBtn && guideInput) {
    guideBtn.addEventListener('click', function () {
      var title = guideInput.value.trim();
      if (title) renderGuide(title);
    });
    guideInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        var title = guideInput.value.trim();
        if (title) renderGuide(title);
      }
    });
  }
});

/* ── STAGE HELPERS ───────────────────────────────────────── */
function setStage(n) {
  var stages = document.querySelectorAll('.loading-stage');
  stages.forEach(function (el, idx) {
    var stageNum = idx + 1;
    el.classList.remove('is-done', 'is-active');
    if (stageNum < n)  el.classList.add('is-done');
    if (stageNum === n) el.classList.add('is-active');
  });
}

function setProgress(pct, title, sub) {
  var fill = document.getElementById('progFill');
  var stat = document.getElementById('loadStatus');
  var sub_ = document.getElementById('loadSub');
  if (fill) fill.style.width = pct + '%';
  if (stat && title) stat.textContent = title;
  if (sub_ && sub)   sub_.textContent = sub;
}

function showError(msg) {
  var box = document.getElementById('errMsg');
  var txt = document.getElementById('errMsgText');
  if (box) box.style.display = 'flex';
  if (txt) txt.textContent = msg || 'Something went wrong.';
}

/* ── START FLOW ──────────────────────────────────────────── */
function start() {
  var username = document.getElementById('userInput').value.trim();
  if (!username) {
    showError('Please enter a Wikipedia username.');
    return;
  }
  document.getElementById('errMsg').style.display = 'none';
  state.username = username;
  document.getElementById('navUser').textContent = username;

  show('loading');
  setProgress(5, 'Connecting…', 'Establishing connection to Wikipedia API');
  setStage(1);

  /* Stagger the UI stages while we wait for real data */
  var stageTimers = [
    setTimeout(function () { setStage(2); setProgress(20, 'Building profile…', 'Analysing your edit history'); }, 400),
    setTimeout(function () { setStage(3); setProgress(45, 'Scanning trends…', 'Fetching current events & trending articles'); }, 1200),
    setTimeout(function () { setStage(4); setProgress(65, 'Finding gaps…', 'Searching for articles needing attention'); }, 2200),
    setTimeout(function () { setStage(5); setProgress(85, 'Scoring tasks…', 'Ranking recommendations for you'); }, 3200)
  ];

  /* Task personalization needs the profile's topics/edit-history first, so fetch it
     before tasks — trends stay independent and load alongside. */
  getProfile(username).then(function (profile) {
    stageTimers.forEach(clearTimeout);
    setStage(3);
    setProgress(60, 'Finding gaps…', 'Searching for articles needing attention');
    state.profile = profile;
    renderProfile();

    return Promise.all([getTrends(), getTasksForProfile(profile)]);
  }).then(function (results) {
    setProgress(100, 'Done!', 'Loading your dashboard…');
    setStage(6);

    state.trends = results[0];
    state.tasks  = results[1];

    renderTrends();
    renderTasks();

    setTimeout(function () { show('dash'); }, 350);

  }).catch(function (err) {
    stageTimers.forEach(clearTimeout);
    show('onboard');
    showError(err.message || 'Failed to load data. Please try again.');
  });
}

/* Top N edit-type keys by count, e.g. {references: 40, minor: 12} -> ['references', 'minor'] */
function topEditTypes(editTypes, n) {
  if (!editTypes) return [];
  return Object.keys(editTypes)
    .sort(function (a, b) { return editTypes[b] - editTypes[a]; })
    .slice(0, n);
}

/* Builds the personalized getTasks() call from a profile: topics, edit-type affinity,
   heavily-edited articles (watchlist), self-created articles (follow-ups), and geo focus. */
function getTasksForProfile(profile) {
  profile = profile || {};
  var editTypes = topEditTypes(profile.editTypes, 3);
  var watchItems = (profile.heavilyEdited || []).slice(0, 10);
  var mineTitles = (profile.createdArticles || []).slice(0, 8);
  var geo = (profile.topGeo || [])[0];
  return getTasks(profile.topTopics, editTypes, watchItems, mineTitles, geo);
}

/* ── REFRESH ─────────────────────────────────────────────── */
function refreshDash() {
  var refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) { refreshBtn.disabled = true; refreshBtn.textContent = 'Refreshing…'; }

  Promise.all([getTrends(), getTasksForProfile(state.profile)]).then(function (results) {
    state.trends = results[0];
    state.tasks  = results[1];
    renderTrends();
    renderTasks();
  }).catch(function () {
    /* silent fail — show stale data */
  }).finally(function () {
    if (refreshBtn) { refreshBtn.disabled = false; refreshBtn.textContent = '↻ Refresh'; }
  });
}
