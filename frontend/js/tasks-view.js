var SRC_LABEL = { current_events: 'News', recent_deaths: 'Obit', ongoing: 'Live', dyk: 'DYK', wiki_trending: 'trending' };

function renderTrends() {
  var trends = state.trends || { news: [], trending: [] };
  var news = trends.news || [];
  var trending = trends.trending || [];

  var newsToShow = news.filter(function (n) { return n.source === 'current_events'; }).slice(0, 4);
  if (newsToShow.length) {
    $('newsBox').innerHTML = '<div class="news-box fade"><div class="news-title">Today\'s News</div><div class="news-items">' +
      newsToShow.map(function (ni) {
        var label = SRC_LABEL[ni.source] || 'news';
        return '<div class="news-item"><div class="ni-head"><div class="ni-title">' + ni.text + '</div>' +
          '<span class="ni-badge">' + label + '</span></div>' +
          '<div class="ni-articles">' + ni.articles.slice(0, 4).map(function (a) {
            return '<a class="ni-art" href="https://en.wikipedia.org/wiki/' + encodeURIComponent(a.replace(/ /g, '_')) + '" target="_blank">' + a + '</a>';
          }).join('') + '</div></div>';
      }).join('') + '</div></div>';
  } else {
    $('newsBox').innerHTML = '';
  }

  if (trending.length) {
    $('trendingBox').innerHTML = '<div class="trending-box fade"><div class="tb-title">Trending Now</div><div class="trend-pills">' +
      trending.slice(0, 12).map(function (t) {
        var label = (t.title || '').length > 30 ? t.title.slice(0, 28) + '…' : (t.title || '');
        var sub = t.views ? (t.views / 1000).toFixed(0) + 'k' : (SRC_LABEL[t.source] || '');
        return '<span class="tp">' + label + '<span class="tp-s">' + sub + '</span></span>';
      }).join('') + '</div></div>';
  } else {
    $('trendingBox').innerHTML = '';
  }
}

function renderTasks() {
  var tasks = state.tasks || [];
  $('taskCount').textContent = '(' + tasks.length + ')';
  if (!tasks.length) {
    $('tasksList').innerHTML = '<div class="empty">No tasks found</div>';
    return;
  }
  $('tasksList').innerHTML = tasks.map(function (t, i) {
    var wiki = 'https://en.wikipedia.org/wiki/' + encodeURIComponent(t.title.replace(/ /g, '_'));
    var edit = 'https://en.wikipedia.org/w/index.php?title=' + encodeURIComponent(t.title.replace(/ /g, '_')) + '&action=edit';
    return '<div class="task fade" style="animation-delay:' + (i * 0.025) + 's">' +
      '<div class="task-rank">' + (i + 1) + '</div>' +
      '<div class="task-head"><div class="task-title"><a href="' + wiki + '" target="_blank">' + t.title + '</a></div>' +
      '<span class="badge">' + t.type + '</span></div>' +
      '<div class="task-reason">' + (t.reason || '') + '</div>' +
      '<div class="task-actions"><a href="' + edit + '" target="_blank" class="tbtn tbtn-edit">Edit</a>' +
      '<a href="' + wiki + '" target="_blank" class="tbtn tbtn-view">View</a></div></div>';
  }).join('');
}
