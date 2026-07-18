/* tasks-view.js — Contributor B rendering */

var SRC_LABEL = {
  current_events: 'Current Events',
  recent_deaths:  'Recent Deaths',
  ongoing:        'Ongoing',
  dyk:            'Did You Know',
  wiki_trending:  'Trending'
};

var SRC_ICON = {
  current_events: '📰',
  recent_deaths:  '🕊️',
  ongoing:        '🔴',
  dyk:            '💡',
  wiki_trending:  '📈'
};

/* ── active filter state ────────────────────────────────── */
var activeFilter = 'all';

function renderTrends() {
  var trends   = state.trends || { news: [], trending: [] };
  var news     = trends.news || [];
  var trending = trends.trending || [];

  /* Trending pills */
  var trendEl = document.getElementById('trendingBox');
  if (trendEl) {
    if (trending.length) {
      var pillsHtml = trending.slice(0, 15).map(function (t) {
        var label = (t.title || '');
        if (label.length > 32) label = label.slice(0, 30) + '…';
        var views = t.views ? ' <span class="trend-pill__views">' + Math.round(t.views / 1000) + 'k</span>' : '';
        var href = 'https://en.wikipedia.org/wiki/' + encodeURIComponent((t.title || '').replace(/ /g, '_'));
        return '<a class="trend-pill" href="' + href + '" target="_blank" rel="noopener">' + label + views + '</a>';
      }).join('');
      trendEl.innerHTML =
        '<div class="trending-title">' + SRC_ICON['wiki_trending'] + ' Trending Now</div>' +
        '<div class="trend-pills fade-in">' + pillsHtml + '</div>';
    } else {
      trendEl.innerHTML = '<div class="empty-state"><div class="empty-state__icon">📈</div>No trending data</div>';
    }
  }

  /* News items */
  var newsEl = document.getElementById('newsBox');
  if (newsEl) {
    var newsToShow = news.slice(0, 5);
    if (newsToShow.length) {
      var newsHtml = newsToShow.map(function (ni) {
        var icon  = SRC_ICON[ni.source] || '📰';
        var label = SRC_LABEL[ni.source] || 'News';
        var artsHtml = (ni.articles || []).slice(0, 4).map(function (a) {
          var href = 'https://en.wikipedia.org/wiki/' + encodeURIComponent(a.replace(/ /g, '_'));
          return '<a class="news-item__art" href="' + href + '" target="_blank" rel="noopener">' + a + '</a>';
        }).join('');
        return '<div class="news-item">' +
          '<div class="news-item__text">' + ni.text + '</div>' +
          '<div class="news-item__source">' +
            '<span class="wtp-badge wtp-badge--neutral">' + icon + ' ' + label + '</span>' +
          '</div>' +
          (artsHtml ? '<div class="news-item__articles">' + artsHtml + '</div>' : '') +
        '</div>';
      }).join('');
      newsEl.innerHTML =
        '<div class="news-title">📰 Today\'s News</div>' +
        '<div class="news-items fade-in">' + newsHtml + '</div>';
    } else {
      newsEl.innerHTML = '<div class="empty-state"><div class="empty-state__icon">📰</div>No news data</div>';
    }
  }
}

function renderTasks() {
  var tasks  = state.tasks || [];
  var countEl = document.getElementById('taskCount');
  if (countEl) countEl.textContent = tasks.length ? '(' + tasks.length + ')' : '';

  var listEl = document.getElementById('tasksList');
  if (!listEl) return;

  /* Apply filter */
  var filtered = activeFilter === 'all'
    ? tasks
    : tasks.filter(function (t) { return t.type === activeFilter; });

  if (!filtered.length) {
    listEl.innerHTML = '<div class="empty-state"><div class="empty-state__icon">✅</div>' +
      (tasks.length ? 'No tasks match this filter.' : 'No tasks found.') + '</div>';
    return;
  }

  listEl.innerHTML = filtered.map(function (t, i) {
    var wiki = 'https://en.wikipedia.org/wiki/' + encodeURIComponent((t.title || '').replace(/ /g, '_'));
    var edit = 'https://en.wikipedia.org/w/index.php?title=' + encodeURIComponent((t.title || '').replace(/ /g, '_')) + '&action=edit';
    var delay = 'style="animation-delay:' + (i * 0.03) + 's"';
    return '<div class="task-item fade-in" ' + delay + '>' +
      '<div class="task-item__head">' +
        '<span class="task-item__num">#' + (i + 1) + '</span>' +
        '<span class="task-item__title"><a href="' + wiki + '" target="_blank" rel="noopener">' + (t.title || '') + '</a></span>' +
        '<span class="wtp-badge wtp-badge--notice">' + (t.type || '') + '</span>' +
      '</div>' +
      (t.topic ? '<div class="task-item__topic">🏷 ' + t.topic + '</div>' : '') +
      '<div class="task-item__reason">' + (t.reason || '') + '</div>' +
      '<div class="task-item__actions">' +
        '<a href="' + edit + '" target="_blank" rel="noopener" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary" style="text-decoration:none">Edit on Wikipedia</a>' +
        '<a href="' + wiki + '" target="_blank" rel="noopener" class="cdx-button" style="text-decoration:none">View</a>' +
      '</div>' +
    '</div>';
  }).join('');
}

/* ── Filter button wiring ────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
  var filtersEl = document.getElementById('taskFilters');
  if (filtersEl) {
    filtersEl.addEventListener('click', function (e) {
      var btn = e.target.closest('.filter-btn');
      if (!btn) return;
      filtersEl.querySelectorAll('.filter-btn').forEach(function (b) {
        b.classList.remove('filter-btn--active');
      });
      btn.classList.add('filter-btn--active');
      activeFilter = btn.dataset.filter || 'all';
      renderTasks();
    });
  }
});
