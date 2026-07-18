// guide-view.js
// Contributor C - Article Guide & Reference Discovery

function getGuide(title) {
    return fetch('http://localhost:5000/api/article/' + encodeURIComponent(title) + '/guide')
        .then(res => res.json());
}

function getReferences(title, offset=0) {
    return fetch('http://localhost:5000/api/article/' + encodeURIComponent(title) + '/references?offset=' + offset)
        .then(res => res.json());
}

function getExternalReferences(title) {
    return fetch('http://localhost:5000/api/article/' + encodeURIComponent(title) + '/external-references')
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

function generateExtRefsHtml(results) {
    let html = '';
    results.forEach(r => {
        html += `
            <div style="padding: 12px; border: 1px solid var(--cdx-color-border--subtle); border-radius: var(--cdx-border-radius-base); margin-bottom: 8px;">
                <a href="${r.url || '#'}" target="_blank" style="text-decoration: none; color: inherit; display: block;">
                    <div style="color: var(--cdx-color-primary); font-weight: bold; margin-bottom: 4px;">${r.title}</div>
                    <div style="font-size: 0.9em; color: var(--cdx-color-base--subtle); margin-bottom: 4px;">
                        <span class="cdx-badge">${r.source}</span> &middot; ${r.citations !== null && r.citations !== undefined ? r.citations + ' citations' : 'Citation data N/A'}
                    </div>
                </a>
            </div>
        `;
    });
    return html;
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('guide-test-panel')) return;

    const panelHtml = `
        <div id="guide-test-panel" class="cdx-card" style="max-width: 1200px; margin: 40px auto; border: 2px solid var(--cdx-color-primary);">
            <h2 style="border-bottom: 1px solid var(--cdx-color-border); padding-bottom: 8px; margin-bottom: 16px;">Contributor C: Article Guide & References (Standalone Demo)</h2>
            <div class="cdx-text-input" style="display: flex; gap: 8px; margin-bottom: 16px;">
                <input type="text" id="testGuideInput" class="cdx-text-input__input" style="flex: 1;" placeholder="Enter a Wikipedia article title (e.g. Python (programming language))">
                <button id="testGuideBtn" class="cdx-button cdx-button--action-progressive">Analyze & Get References</button>
            </div>
            <div id="testGuidePanel">
                <p style="color: var(--cdx-color-base--subtle);">Enter an article title above to test the backend endpoints independently.</p>
            </div>
        </div>
    `;

    const div = document.createElement('div');
    div.innerHTML = panelHtml;
    document.body.prepend(div.firstElementChild);

    const guideBtn = document.getElementById('testGuideBtn');
    const guideInput = document.getElementById('testGuideInput');
    const guidePanel = document.getElementById('testGuidePanel');
    
    guideBtn.addEventListener('click', () => {
        const title = guideInput.value.trim();
        if (!title) return;
        
        guideBtn.disabled = true;
        guideBtn.style.opacity = '0.7';
        
        // Render empty scaffold immediately
        guidePanel.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; align-items: start;">
                <div id="wiki-col"><p style="color: var(--cdx-color-base--subtle);">Analyzing Wikipedia structure...</p></div>
                <div id="ext-col"><p style="color: var(--cdx-color-base--subtle);">Searching external academic papers...</p></div>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 16px;">
                <a href="https://en.wikipedia.org/w/index.php?title=${encodeURIComponent(title.replace(/ /g,'_'))}&action=edit" target="_blank" class="cdx-button cdx-button--action-progressive">Open Editor</a>
                <a href="https://en.wikipedia.org/wiki/${encodeURIComponent(title.replace(/ /g,'_'))}" target="_blank" class="cdx-button cdx-button--weight-primary">Read Article</a>
            </div>
        `;
        
        // Fetch Wikipedia Data
        Promise.all([getGuide(title), getReferences(title)])
            .then(([guideData, refsData]) => {
                const wikiCol = document.getElementById('wiki-col');
                if (guideData.error && !guideData.sections) {
                    wikiCol.innerHTML = `<p style="color: var(--cdx-color-destructive);">Error: ${guideData.error}</p>`;
                    return;
                }
                
                const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
                let leftHtml = `
                    <div class="cdx-card" style="margin-bottom: 16px;">
                        <h3 style="margin-bottom: 8px;">Edit Guide: ${title}</h3>
                        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
                            <span class="cdx-badge cdx-badge--progressive">${cap(guideData.articleType || 'general')}</span>
                            <span class="cdx-badge">${Math.round((guideData.currentSize || 0) / 1000)}k chars</span>
                            <span class="cdx-badge">${guideData.totalRefs || 0} refs</span>
                            ${!guideData.hasInfobox ? '<span class="cdx-badge cdx-badge--warning">No infobox</span>' : ''}
                            ${!guideData.hasImages ? '<span class="cdx-badge cdx-badge--warning">No images</span>' : ''}
                        </div>
                    </div>
                `;

                if (guideData.suggestions && guideData.suggestions.length) {
                    leftHtml += `
                    <div class="cdx-card" style="margin-bottom: 16px;">
                        <h4 style="margin-bottom: 8px; color: var(--cdx-color-base);">What to Edit</h4>
                        <ul style="padding-left: 20px;">
                    `;
                    guideData.suggestions.forEach(s => leftHtml += `<li style="margin-bottom: 4px;">${s.text}</li>`);
                    leftHtml += `</ul></div>`;
                }

                if (guideData.missingExpected && guideData.missingExpected.length) {
                    leftHtml += `
                    <div class="cdx-card" style="margin-bottom: 16px;">
                        <h4 style="margin-bottom: 8px; color: var(--cdx-color-base);">Missing Sections</h4>
                        <div style="display: flex; flex-direction: column; gap: 8px;">
                    `;
                    guideData.missingExpected.forEach(s => {
                        leftHtml += `
                            <div style="display: flex; justify-content: space-between; padding: 8px; background: var(--cdx-color-background--interactive); border-radius: var(--cdx-border-radius-base);">
                                <span style="font-weight: bold; color: var(--cdx-color-destructive);">+ ${s}</span>
                                <span style="color: var(--cdx-color-base--subtle); font-size: 0.9em;">Expected for ${cap(guideData.articleType || 'general')} articles</span>
                            </div>
                        `;
                    });
                    leftHtml += `</div></div>`;
                }

                if (refsData && refsData.results && refsData.results.length) {
                    leftHtml += `
                    <div class="cdx-card" style="margin-bottom: 16px;">
                        <h4 style="margin-bottom: 8px; color: var(--cdx-color-base);">Suggested Wikimedia References (${refsData.total || refsData.results.length} total)</h4>
                        <div id="refs-container" style="display: flex; flex-direction: column; gap: 8px;">
                    `;
                    leftHtml += generateRefsHtml(refsData.results);
                    leftHtml += `</div>`;
                    
                    if (refsData.nextOffset) {
                        leftHtml += `<button id="loadMoreBtn" class="cdx-button" style="margin-top: 12px; width: 100%;">Load More References...</button>`;
                    }
                    leftHtml += `</div>`;
                }
                wikiCol.innerHTML = leftHtml;
                
                const loadMoreBtn = document.getElementById('loadMoreBtn');
                if (loadMoreBtn) {
                    loadMoreBtn.addEventListener('click', () => {
                        loadMoreBtn.innerText = 'Loading...';
                        loadMoreBtn.disabled = true;
                        
                        getReferences(title, refsData.nextOffset)
                        .then(newData => {
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
            })
            .catch(err => {
                document.getElementById('wiki-col').innerHTML = `<p style="color: var(--cdx-color-destructive);">Network Error: ${err.message}</p>`;
            })
            .finally(() => {
                guideBtn.disabled = false;
                guideBtn.style.opacity = '1';
            });
            
        // Fetch External Academic Data Independently
        getExternalReferences(title)
            .then(extRefsData => {
                const extCol = document.getElementById('ext-col');
                let rightHtml = `
                    <div class="cdx-card" style="margin-bottom: 16px; height: 100%;">
                        <h3 style="margin-bottom: 8px; color: var(--cdx-color-base);">External Academic Research</h3>
                        <p style="font-size: 0.9em; color: var(--cdx-color-base--subtle); margin-bottom: 12px;">Top cited papers from Semantic Scholar, CrossRef, and PubMed</p>
                `;
                if (extRefsData && extRefsData.results && extRefsData.results.length) {
                    rightHtml += generateExtRefsHtml(extRefsData.results);
                } else {
                    rightHtml += `<p style="color: var(--cdx-color-base--subtle);">No external research found.</p>`;
                }
                rightHtml += `</div>`;
                extCol.innerHTML = rightHtml;
            })
            .catch(err => {
                document.getElementById('ext-col').innerHTML = `<p style="color: var(--cdx-color-destructive);">Error: ${err.message}</p>`;
            });
    });

    guideInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') guideBtn.click();
    });
});
