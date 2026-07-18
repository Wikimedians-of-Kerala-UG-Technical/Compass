// guide-view.js
// Contributor C - Article Guide & Reference Discovery

function getGuide(title) {
    return fetch('http://localhost:5000/api/article/' + encodeURIComponent(title) + '/guide')
        .then(res => res.json());
}

function getReferences(title) {
    return fetch('http://localhost:5000/api/article/' + encodeURIComponent(title) + '/references')
        .then(res => res.json());
}

function generateRefsHtml(results) {
    let html = '';
    results.forEach(r => {
        html += `
            <div style="padding: 12px; border: 1px solid var(--cdx-color-border--subtle); border-radius: var(--cdx-border-radius-base);">
                <a href="${r.url || '#'}" target="_blank" style="text-decoration: none; color: inherit; display: block;">
                    <div style="color: var(--cdx-color-primary); font-weight: bold; margin-bottom: 4px;">${r.title}</div>
                    <div style="font-size: 0.9em; color: var(--cdx-color-base--subtle); margin-bottom: 4px;">
                        ${r.authors || '?'} &middot; ${r.year || 'n.d.'}${r.venue ? ' &middot; ' + r.venue : ''}${r.citations ? ' &middot; Word count ' + r.citations : ''}
                    </div>
                </a>
        `;
        
        // Show What to edit and Missing sections for this specific reference
        if (r.whatToEdit && r.whatToEdit.length) {
            html += `<div style="margin-top: 8px; font-size: 0.85em;"><strong>What to Edit in ${r.title}:</strong> <ul style="padding-left: 16px; margin: 4px 0;">`;
            r.whatToEdit.forEach(s => html += `<li>${s.text}</li>`);
            html += `</ul></div>`;
        }
        
        if (r.missingSections && r.missingSections.length) {
             html += `<div style="margin-top: 4px; font-size: 0.85em; color: var(--cdx-color-destructive);"><strong>Missing Sections:</strong> ${r.missingSections.join(', ')}</div>`;
        }
        
        html += `</div>`;
    });
    return html;
}

function renderGuide(el, a, refsData, title) {
    const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
    
    // Overview Card (using Codex classes from UI_UX_Design.md)
    let html = `
        <div class="cdx-card" style="margin-bottom: 16px;">
            <h3 style="margin-bottom: 8px;">Edit Guide: ${title}</h3>
            <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                <span class="cdx-badge cdx-badge--progressive">${cap(a.articleType || 'general')}</span>
                <span class="cdx-badge">${Math.round((a.currentSize || 0) / 1000)}k chars</span>
                <span class="cdx-badge">${a.totalRefs || 0} refs</span>
                ${!a.hasInfobox ? '<span class="cdx-badge cdx-badge--warning">No infobox</span>' : ''}
                ${!a.hasImages ? '<span class="cdx-badge cdx-badge--warning">No images</span>' : ''}
            </div>
        </div>
    `;

    // Suggestions Card
    if (a.suggestions && a.suggestions.length) {
        html += `
        <div class="cdx-card" style="margin-bottom: 16px;">
            <h4 style="margin-bottom: 8px; color: var(--cdx-color-base);">What to Edit</h4>
            <ul style="padding-left: 20px;">
        `;
        a.suggestions.forEach(s => html += `<li style="margin-bottom: 4px;">${s.text}</li>`);
        html += `</ul></div>`;
    }

    // Missing Sections Card
    if (a.missingExpected && a.missingExpected.length) {
        html += `
        <div class="cdx-card" style="margin-bottom: 16px;">
            <h4 style="margin-bottom: 8px; color: var(--cdx-color-base);">Missing Sections</h4>
            <div style="display: flex; flex-direction: column; gap: 8px;">
        `;
        a.missingExpected.forEach(s => {
            html += `
                <div style="display: flex; justify-content: space-between; padding: 8px; background: var(--cdx-color-background--interactive); border-radius: var(--cdx-border-radius-base);">
                    <span style="font-weight: bold; color: var(--cdx-color-destructive);">+ ${s}</span>
                    <span style="color: var(--cdx-color-base--subtle); font-size: 0.9em;">Expected for ${cap(a.articleType)} articles</span>
                </div>
            `;
        });
        html += `</div></div>`;
    }

    // Suggested References Card (Paginated + Inner Analysis)
    let refsHtml = '';
    if (refsData && refsData.results && refsData.results.length) {
        refsHtml += `
        <div class="cdx-card" style="margin-bottom: 16px;">
            <h4 style="margin-bottom: 8px; color: var(--cdx-color-base);">Suggested References (${refsData.total || refsData.results.length} total)</h4>
            <div id="refs-container" style="display: flex; flex-direction: column; gap: 8px;">
        `;
        
        refsHtml += generateRefsHtml(refsData.results);
        
        refsHtml += `</div>`;
        
        if (refsData.nextOffset) {
            refsHtml += `<button id="loadMoreBtn" class="cdx-button" style="margin-top: 12px; width: 100%;">Load More References...</button>`;
        }
        
        refsHtml += `</div>`;
    }
    
    html += refsHtml;
    
    // Action Buttons
    html += `
        <div style="display: flex; gap: 8px; margin-top: 16px;">
            <a href="https://en.wikipedia.org/w/index.php?title=${encodeURIComponent(title.replace(/ /g,'_'))}&action=edit" target="_blank" class="cdx-button cdx-button--action-progressive">Open Editor</a>
            <a href="https://en.wikipedia.org/wiki/${encodeURIComponent(title.replace(/ /g,'_'))}" target="_blank" class="cdx-button cdx-button--weight-primary">Read Article</a>
        </div>
    `;

    el.innerHTML = html;
    
    // Bind Load More
    const loadMoreBtn = document.getElementById('loadMoreBtn');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', () => {
            loadMoreBtn.innerText = 'Loading...';
            loadMoreBtn.disabled = true;
            getReferences(title, refsData.nextOffset).then(newData => {
                const container = document.getElementById('refs-container');
                container.insertAdjacentHTML('beforeend', generateRefsHtml(newData.results));
                refsData.nextOffset = newData.nextOffset;
                if (!refsData.nextOffset) {
                    loadMoreBtn.remove();
                } else {
                    loadMoreBtn.innerText = 'Load More References...';
                    loadMoreBtn.disabled = false;
                }
            }).catch(err => {
                loadMoreBtn.innerText = 'Error loading more';
            });
        });
    }
}

// Standalone Test Panel Injection (For independent demoability as requested in PLan.md)
document.addEventListener('DOMContentLoaded', () => {
    // Only inject if it doesn't already exist
    if (document.getElementById('guide-test-panel')) return;

    const panelHtml = `
        <div id="guide-test-panel" class="cdx-card" style="max-width: 600px; margin: 40px auto; border: 2px solid var(--cdx-color-primary);">
            <h2 style="border-bottom: 1px solid var(--cdx-color-border); padding-bottom: 8px; margin-bottom: 16px;">Contributor C: Article Guide & References (Standalone Demo)</h2>
            <div class="cdx-text-input" style="display: flex; gap: 8px; margin-bottom: 16px;">
                <input type="text" id="guideInput" class="cdx-text-input__input" style="flex: 1;" placeholder="Enter a Wikipedia article title (e.g. Python (programming language))">
                <button id="guideBtn" class="cdx-button cdx-button--action-progressive">Analyze & Get References</button>
            </div>
            <div id="guidePanel">
                <p style="color: var(--cdx-color-base--subtle);">Enter an article title above to test the backend endpoints independently.</p>
            </div>
        </div>
    `;

    // Append to body
    const div = document.createElement('div');
    div.innerHTML = panelHtml;
    document.body.prepend(div.firstElementChild);

    const guideBtn = document.getElementById('guideBtn');
    const guideInput = document.getElementById('guideInput');
    const guidePanel = document.getElementById('guidePanel');
    
    guideBtn.addEventListener('click', () => {
        const title = guideInput.value.trim();
        if (!title) return;
        
        guidePanel.innerHTML = '<p style="color: var(--cdx-color-base--subtle);">Analyzing article & finding references (Hitting Flask Backend)...</p>';
        guideBtn.disabled = true;
        guideBtn.style.opacity = '0.7';
        
        Promise.all([getGuide(title), getReferences(title)])
            .then(([guideData, refsData]) => {
                guideBtn.disabled = false;
                guideBtn.style.opacity = '1';
                
                if (guideData.error && !guideData.sections) {
                    guidePanel.innerHTML = `<p style="color: var(--cdx-color-destructive);">Error: ${guideData.error}</p>`;
                    return;
                }
                renderGuide(guidePanel, guideData, refsData, title);
            })
            .catch(err => {
                guideBtn.disabled = false;
                guideBtn.style.opacity = '1';
                guidePanel.innerHTML = `<p style="color: var(--cdx-color-destructive);">Network Error: ${err.message}</p>`;
            });
    });

    // Support pressing Enter
    guideInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') guideBtn.click();
    });
});
