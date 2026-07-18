/* guide-view.js — Contributor C rendering
   NOTE: This file ONLY exports renderGuide().
   The standalone demo panel has been removed — the guide is
   now embedded inside the dashboard (index.html #guideResult).
*/

function renderGuide(title) {
  var resultEl = document.getElementById('guideResult');
  if (!resultEl) return;

  /* Loading state */
  resultEl.innerHTML =
    '<div style="display:flex;align-items:center;gap:10px;padding:16px;color:#54595d;">' +
      '<div class="loading-card__spinner" style="width:24px;height:24px;border-width:2px;flex-shrink:0"></div>' +
      'Analysing <strong>' + esc(title) + '</strong>…' +
    '</div>';

  Promise.all([
    getGuide(title).catch(function () { return null; }),
    getReferences(title).catch(function () { return null; }),
    getExternalReferences(title).catch(function () { return null; })
  ]).then(function (results) {
    var guideData = results[0];
    var refsData  = results[1];
    var extRefsData = results[2];
    renderGuideResult(title, guideData, refsData, extRefsData);
  });
}

function renderGuideResult(title, g, refs, extRefs) {
  var resultEl = document.getElementById('guideResult');
  if (!resultEl) return;

  if (!g || g.error) {
    resultEl.innerHTML =
      '<div class="cdx-message cdx-message--error" style="margin-top:8px">' +
        '<span class="cdx-message__icon"></span>' +
        '<div class="cdx-message__content">Could not load article guide. Make sure the title is exact.</div>' +
      '</div>';
    return;
  }

  var cap = function (s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''; };

  /* ── Meta badges ──────────────────────────────────────── */
  var metaBadges =
    '<span class="wtp-badge wtp-badge--notice">' + cap(g.articleType || 'general') + '</span> ' +
    '<span class="wtp-badge wtp-badge--neutral">' + Math.round((g.currentSize || 0) / 1000) + 'k chars</span> ' +
    '<span class="wtp-badge wtp-badge--neutral">' + (g.totalRefs || 0) + ' refs</span>' +
    (!g.hasInfobox ? ' <span class="wtp-badge wtp-badge--warning">No infobox</span>' : '') +
    (!g.hasImages  ? ' <span class="wtp-badge wtp-badge--warning">No images</span>' : '');

  /* ── Suggestions (Overall Analysis) ───────────────────── */
  var suggestHtml = '';
  if (g.suggestions && g.suggestions.length) {
    suggestHtml =
      '<div class="guide-col-title" style="margin-top:16px;">Overall Analysis: What to Edit</div>' +
      '<div class="guide-suggestions">' +
        g.suggestions.map(function (s) {
          return '<div class="guide-suggestion">' + esc(s.text || s) + '</div>';
        }).join('') +
      '</div>';
  }

  /* ── Missing sections ─────────────────────────────────── */
  var sectionsHtml = '';
  if ((g.missingExpected && g.missingExpected.length) || (g.sections && g.sections.length)) {
    var allSections = (g.sections || []);
    var sectionItems = allSections.slice(0, 8).map(function (s) {
      var cls = s.status === 'missing' ? 'is-missing' : s.status === 'short' ? 'is-short' : 'is-ok';
      var statusText = s.status === 'missing' ? '✗ Missing'
        : s.status === 'short' ? '△ Thin section'
        : '✓ Present';
      return '<div class="guide-section-item ' + cls + '">' +
        '<div class="guide-section-name">' + esc(s.name || s) + '</div>' +
        '<div class="guide-section-status">' + statusText + (s.tip ? ' — ' + esc(s.tip) : '') + '</div>' +
      '</div>';
    }).join('');

    if (!sectionItems && g.missingExpected && g.missingExpected.length) {
      sectionItems = g.missingExpected.map(function (s) {
        return '<div class="guide-section-item is-missing">' +
          '<div class="guide-section-name">' + esc(s) + '</div>' +
          '<div class="guide-section-status">✗ Missing — expected for ' + cap(g.articleType || 'general') + ' articles</div>' +
        '</div>';
      }).join('');
    }

    if (sectionItems) {
      sectionsHtml =
        '<div class="guide-col-title" style="margin-top:16px;">Section Analysis</div>' +
        '<div class="guide-section-list" style="display:grid; grid-template-columns: 1fr 1fr; gap: 6px;">' + sectionItems + '</div>';
    }
  }

  /* ── References (Wikimedia / internal) ───────────────── */
  function generateRefsHtml(results) {
    return results.map(function(r) {
      var editHtml = '';
      if (r.whatToEdit && r.whatToEdit.length) {
          editHtml += '<div style="margin-top: 8px; font-size: 0.85em; color: #202122;"><strong>What to Edit:</strong> <ul style="padding-left: 16px; margin: 4px 0;">' + 
            r.whatToEdit.map(function(s) { return '<li>' + esc(s.text) + '</li>'; }).join('') + 
            '</ul></div>';
      }
      if (r.missingSections && r.missingSections.length) {
           editHtml += '<div style="margin-top: 4px; font-size: 0.85em; color: #d33;"><strong>Missing Sections:</strong> ' + esc(r.missingSections.join(', ')) + '</div>';
      }
      
      var dropdownHtml = editHtml ? 
        '<details style="margin-top: 8px; cursor: pointer;">' +
          '<summary style="font-size: 0.8125rem; color: #3366cc; font-weight: bold; outline: none; user-select: none;">View missing items & suggestions</summary>' +
          '<div style="padding: 8px 12px; background: #f8f9fa; border-radius: 2px; border: 1px solid #eaecf0; margin-top: 6px;">' + editHtml + '</div>' +
        '</details>' : '';

      return '<div class="guide-ref-item" style="cursor: default;">' +
        '<a href="' + esc(r.url || '#') + '" target="_blank" rel="noopener" style="text-decoration:none; color:inherit; display:block;">' +
          '<div class="guide-ref-title">' + esc(r.title || 'Untitled') + '</div>' +
          '<div class="guide-ref-meta">' + esc(r.authors || '') + (r.year ? ' · ' + r.year : '') + (r.venue ? ' · ' + r.venue : '') + '</div>' +
          (r.citations ? '<div class="guide-ref-source">' + r.citations + ' citations</div>' : '') +
        '</a>' +
        dropdownHtml +
      '</div>';
    }).join('');
  }

  var wikiRefsHtml = '';
  if (refs && refs.results && refs.results.length) {
    wikiRefsHtml =
      '<div class="guide-col-title" style="margin-bottom:12px;">Suggested Wikimedia References</div>' +
      '<div id="wikiRefsContainer" style="display: flex; flex-direction: column; gap: 6px;">' + generateRefsHtml(refs.results.slice(0, 10)) + '</div>' +
      (refs.nextOffset ? '<button class="cdx-button" id="guideLoadMore" style="width:100%;margin-top:8px;">Load more references…</button>' : '');
  } else {
    wikiRefsHtml =
      '<div class="guide-col-title" style="margin-bottom:12px;">Suggested Wikimedia References</div>' +
      '<div class="empty-state"><div class="empty-state__icon">📄</div>No internal references found.</div>';
  }

  /* ── External References ───────────────── */
  var extRefsHtml = '';
  if (extRefs && extRefs.results && extRefs.results.length) {
    extRefsHtml =
      '<div class="guide-col-title" style="margin-bottom:12px;">External Academic Research</div>' +
      '<div style="display: flex; flex-direction: column; gap: 6px;">' +
      extRefs.results.slice(0, 10).map(function(r) {
        return '<a class="guide-ref-item" href="' + esc(r.url || '#') + '" target="_blank" rel="noopener" style="text-decoration:none; color:inherit; display:block;">' +
          '<div class="guide-ref-title">' + esc(r.title || 'Untitled') + '</div>' +
          '<div class="guide-ref-meta" style="margin-top: 6px;"><span class="wtp-badge wtp-badge--neutral" style="margin-right: 4px;">' + esc(r.source) + '</span> ' + 
          (r.citations !== null && r.citations !== undefined ? r.citations + ' citations' : '') + 
          '</div>' +
        '</a>';
      }).join('') + '</div>';
  } else {
    extRefsHtml =
      '<div class="guide-col-title" style="margin-bottom:12px;">External Academic Research</div>' +
      '<div class="empty-state"><div class="empty-state__icon">📄</div>No external research found.</div>';
  }

  /* ── Assemble ─────────────────────────────────────────── */
  resultEl.innerHTML =
    '<div style="margin-top:8px">' +
      '<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;border-bottom:1px solid #eaecf0;padding-bottom:12px;">' +
        '<a href="https://en.wikipedia.org/wiki/' + encodeURIComponent(title.replace(/ /g,'_')) + '" target="_blank" style="font-family:\'Linux Libertine\',Georgia,serif;font-size:1.125rem;font-weight:bold">' + esc(title) + '</a>' +
        metaBadges +
        '<a href="https://en.wikipedia.org/w/index.php?title=' + encodeURIComponent(title.replace(/ /g,'_')) + '&action=edit" target="_blank" class="cdx-button cdx-button--action-progressive cdx-button--weight-primary" style="text-decoration:none;margin-left:auto">Edit article</a>' +
      '</div>' +
      '<div style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #eaecf0;">' +
         suggestHtml + sectionsHtml +
      '</div>' +
      '<div class="guide-result-grid">' +
        '<div>' + wikiRefsHtml + '</div>' +
        '<div>' + extRefsHtml + '</div>' +
      '</div>' +
    '</div>';

  /* Load-more button */
  var lmBtn = document.getElementById('guideLoadMore');
  if (lmBtn && refs && refs.nextOffset) {
    lmBtn.addEventListener('click', function () {
      lmBtn.textContent = 'Loading…';
      lmBtn.disabled = true;
      getReferences(title, refs.nextOffset).then(function (more) {
        if (more && more.results) {
          refs.nextOffset = more.nextOffset;
          var container = document.getElementById('wikiRefsContainer');
          if (container) {
              container.insertAdjacentHTML('beforeend', generateRefsHtml(more.results));
          }
          if (!more.nextOffset) lmBtn.remove();
          else { lmBtn.textContent = 'Load more references…'; lmBtn.disabled = false; }
        }
      }).catch(function () { lmBtn.textContent = 'Error — try again'; lmBtn.disabled = false; });
    });
  }
}

function esc(s) {
  return String(s || '').replace(/[&<>"']/g, function (c) {
    return { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c];
  });
}
