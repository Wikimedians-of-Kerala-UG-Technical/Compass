/* profile-view.js — Contributor A rendering */

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}

function renderProfile() {
  var p = state.profile;
  var el = document.getElementById('profileCard');
  if (!p || !el) return;

  /* ── Stats ─────────────────────────────────────────────── */
  var initials = state.username ? state.username.slice(0, 2).toUpperCase() : '?';

  /* ── Edit types (top 5) ──────────────────────────────── */
  var editTypeEntries = Object.entries(p.editTypes || {})
    .sort(function (a, b) { return b[1] - a[1]; })
    .slice(0, 5);
  var editTypeBadges = editTypeEntries.map(function (e) {
    return '<span class="wtp-badge wtp-badge--neutral" style="margin:2px">' +
      escapeHtml(e[0]) + ' <strong>' + e[1] + '</strong></span>';
  }).join('');

  /* ── Topics ─────────────────────────────────────────── */
  var topicBadges = (p.topTopics || []).map(function (t) {
    return '<span class="wtp-badge wtp-badge--notice" style="margin:2px">' + escapeHtml(t) + '</span>';
  }).join('');

  /* ── Geo focus ──────────────────────────────────────── */
  var geoBadges = (p.topGeo || []).map(function (g) {
    return '<span class="wtp-badge wtp-badge--neutral" style="margin:2px">🌍 ' + escapeHtml(g) + '</span>';
  }).join('');

  /* ── Quality tier ───────────────────────────────────── */
  var qualityVariant = p.qualityTier === 'high' ? 'wtp-badge--success'
    : p.qualityTier === 'medium' ? 'wtp-badge--warning' : 'wtp-badge--neutral';
  var qualityBadge = p.qualityTier
    ? '<span class="wtp-badge ' + qualityVariant + '" style="margin:2px">Quality: ' + escapeHtml(p.qualityTier) + '</span>'
    : '';

  /* ── Recent edits ────────────────────────────────────── */
  var recentHtml = (p.recentEdits || []).slice(0, 5).map(function (e) {
    var diffClass = e.sizediff > 0 ? 'diff-pos' : 'diff-neg';
    var sign = e.sizediff > 0 ? '+' : '';
    var diffLink = e.diffUrl
      ? ' <a href="' + escapeHtml(e.diffUrl) + '" target="_blank" class="wtp-badge wtp-badge--neutral">diff</a>'
      : '';
    return '<div class="recent-edit">' +
      '<div class="recent-edit__title">' +
        '<a href="' + escapeHtml(e.articleUrl || '#') + '" target="_blank">' + escapeHtml(e.title) + '</a>' +
        ' <span class="' + diffClass + '">(' + sign + e.sizediff + ')</span>' + diffLink +
      '</div>' +
      '<div class="recent-edit__meta">' + escapeHtml(e.comment || '(no summary)') + '</div>' +
    '</div>';
  }).join('');

  el.innerHTML =
    '<div class="wtp-card__header">' +
      '<div class="profile-header">' +
        '<div class="profile-avatar">' + escapeHtml(initials) + '</div>' +
        '<div>' +
          '<div class="profile-username">' + escapeHtml(state.username) + '</div>' +
          '<div class="profile-label">Wikipedia contributor</div>' +
        '</div>' +
      '</div>' +
    '</div>' +

    '<div class="profile-stats">' +
      '<div class="profile-stat">' +
        '<span class="profile-stat__num">' + (p.total || 0).toLocaleString() + '</span>' +
        '<span class="profile-stat__label">Edits</span>' +
      '</div>' +
      '<div class="profile-stat">' +
        '<span class="profile-stat__num">' + (p.uniqueArticles || 0).toLocaleString() + '</span>' +
        '<span class="profile-stat__label">Articles</span>' +
      '</div>' +
    '</div>' +

    (qualityBadge || geoBadges ? (
      '<div class="profile-section">' +
        '<div class="profile-tags">' + qualityBadge + geoBadges + '</div>' +
      '</div>'
    ) : '') +

    (topicBadges ? (
      '<div class="profile-section">' +
        '<div class="profile-section__title">Top topics</div>' +
        '<div class="profile-tags">' + topicBadges + '</div>' +
      '</div>'
    ) : '') +

    (editTypeBadges ? (
      '<div class="profile-section">' +
        '<div class="profile-section__title">Edit types</div>' +
        '<div class="profile-tags">' + editTypeBadges + '</div>' +
      '</div>'
    ) : '') +

    (recentHtml ? (
      '<div class="profile-section">' +
        '<div class="profile-section__title">Recent contributions</div>' +
        recentHtml +
      '</div>'
    ) : '');
}