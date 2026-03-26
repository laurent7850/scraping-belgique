/**
 * Scraping Professions — Frontend Logic (Belgique + France)
 */

// ============================================================
// State
// ============================================================
let selectedCountry = 'BE';
let currentJobId = null;
let eventSource = null;
let allResults = [];
let currentPage = 1;
const PAGE_SIZE = 25;
let sortCol = '';
let sortDir = 'asc';

// Step definitions per country
const STEPS_BE = [
    { key: 'kbo',      icon: 'bi-building',        label: 'KBO/BCE' },
    { key: 'pagesdor', icon: 'bi-book',             label: "Pages d'Or" },
    { key: 'fusion',   icon: 'bi-arrows-collapse',  label: 'Fusion' },
    { key: 'cbeapi',   icon: 'bi-cloud-download',   label: 'CBEAPI' },
    { key: 'email',    icon: 'bi-envelope',          label: 'Email' },
];
const STEPS_FR = [
    { key: 'entreprises_api', icon: 'bi-building',       label: 'API Entreprises' },
    { key: 'pagesjaunes',     icon: 'bi-book',            label: 'Pages Jaunes' },
    { key: 'fusion',          icon: 'bi-arrows-collapse', label: 'Fusion' },
    { key: 'email',           icon: 'bi-envelope',         label: 'Email' },
];

function getSteps() {
    return selectedCountry === 'FR' ? STEPS_FR : STEPS_BE;
}

function getStepKeys() {
    return getSteps().map(s => s.key).concat(['done']);
}

// ============================================================
// DOM Elements
// ============================================================
const searchSection = document.getElementById('search-section');
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');
const errorSection = document.getElementById('error-section');

const searchForm = document.getElementById('search-form');
const btnSearch = document.getElementById('btn-search');
const maxResultsSlider = document.getElementById('max-results');
const maxResultsValue = document.getElementById('max-results-value');
const professionCustom = document.getElementById('profession-custom');

const progressBar = document.getElementById('progress-bar');
const progressMessage = document.getElementById('progress-message');
const progressLog = document.getElementById('progress-log');
const progressSpinner = document.getElementById('progress-spinner');

const resultsBody = document.getElementById('results-body');
const resultsCount = document.getElementById('results-count');
const btnDownload = document.getElementById('btn-download');
const btnNewSearch = document.getElementById('btn-new-search');
const tableFilter = document.getElementById('table-filter');
const btnErrorRetry = document.getElementById('btn-error-retry');

// ============================================================
// Country Switching
// ============================================================

function updateFormForCountry(country) {
    selectedCountry = country;
    document.getElementById('selected-country').value = country;

    // Toggle active state on buttons
    document.querySelectorAll('.country-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.country === country);
    });

    // Toggle profession selects
    document.getElementById('profession-be').classList.toggle('d-none', country !== 'BE');
    document.getElementById('profession-fr').classList.toggle('d-none', country !== 'FR');

    // Toggle province/region selects
    document.getElementById('province-be').classList.toggle('d-none', country !== 'BE');
    document.getElementById('province-fr').classList.toggle('d-none', country !== 'FR');

    // Update label
    document.getElementById('label-region').textContent = country === 'FR' ? 'R\u00e9gion' : 'Province';

    // Update placeholders
    const villeInput = document.getElementById('ville');
    villeInput.placeholder = country === 'FR'
        ? 'Ex: Paris, Lyon, 75001...'
        : 'Ex: Bruxelles, Li\u00e8ge, 5000...';

    // Update enrichment labels
    const labelEnrich = document.getElementById('label-enrich');
    const labelDeepEmail = document.getElementById('label-deep-email');
    if (country === 'FR') {
        labelEnrich.innerHTML = 'Enrichissement Pages Jaunes <small class="text-muted">(t\u00e9l\u00e9phone, email, site web)</small>';
        labelDeepEmail.innerHTML = 'Enrichissement email approfondi <small class="text-muted">(site web + Google)</small>';
    } else {
        labelEnrich.innerHTML = 'Enrichissement Pages d\'Or + CBEAPI <small class="text-muted">(t\u00e9l\u00e9phone, email, site web)</small>';
        labelDeepEmail.innerHTML = 'Enrichissement email approfondi <small class="text-muted">(Pages d\'Or d\u00e9tail + site web + Google)</small>';
    }

    // Update navbar sources
    const navSources = document.getElementById('navbar-sources');
    if (navSources) {
        navSources.innerHTML = country === 'FR'
            ? '<i class="bi bi-database me-1"></i> API Entreprises + Pages Jaunes'
            : '<i class="bi bi-database me-1"></i> KBO + Pages d\'Or + CBEAPI';
    }

    // Reset select values
    document.getElementById('profession-be').value = '';
    document.getElementById('profession-fr').value = '';
    document.getElementById('province-be').value = '';
    document.getElementById('province-fr').value = '';
    professionCustom.value = '';
}

// Country button listeners
document.querySelectorAll('.country-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        updateFormForCountry(btn.dataset.country);
    });
});

// ============================================================
// Event Listeners
// ============================================================

// Slider value display
maxResultsSlider.addEventListener('input', () => {
    maxResultsValue.textContent = maxResultsSlider.value;
});

// Profession select / custom sync (both BE and FR)
document.querySelectorAll('.profession-select').forEach(sel => {
    sel.addEventListener('change', () => {
        if (sel.value) {
            professionCustom.value = '';
        }
    });
});
professionCustom.addEventListener('input', () => {
    if (professionCustom.value.trim()) {
        document.getElementById('profession-be').value = '';
        document.getElementById('profession-fr').value = '';
    }
});

// Form submit
searchForm.addEventListener('submit', (e) => {
    e.preventDefault();
    startSearch();
});

// New search button
btnNewSearch.addEventListener('click', () => {
    showSection('search');
});

// Error retry
btnErrorRetry.addEventListener('click', () => {
    showSection('search');
});

// Download CSV
btnDownload.addEventListener('click', () => {
    if (currentJobId) {
        window.location.href = `/api/download/${currentJobId}`;
    }
});

// Table filter
tableFilter.addEventListener('input', () => {
    currentPage = 1;
    renderResults();
});

// Column sorting
document.querySelectorAll('.sortable').forEach(th => {
    th.addEventListener('click', () => {
        const col = th.dataset.col;
        if (sortCol === col) {
            sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        } else {
            sortCol = col;
            sortDir = 'asc';
        }
        document.querySelectorAll('.sortable').forEach(h => {
            h.classList.remove('sorted-asc', 'sorted-desc');
        });
        th.classList.add(sortDir === 'asc' ? 'sorted-asc' : 'sorted-desc');
        renderResults();
    });
});

// ============================================================
// Section Management
// ============================================================

function showSection(name) {
    searchSection.classList.toggle('d-none', name !== 'search');
    progressSection.classList.toggle('d-none', name !== 'progress');
    resultsSection.classList.toggle('d-none', name !== 'results');
    errorSection.classList.toggle('d-none', name !== 'error');
}

// ============================================================
// Step Indicators (dynamic)
// ============================================================

function buildStepIndicators() {
    const container = document.getElementById('steps-container');
    container.innerHTML = '';
    const steps = getSteps();

    steps.forEach((step, i) => {
        // Step item
        const div = document.createElement('div');
        div.className = 'step-item';
        div.dataset.step = step.key;
        div.innerHTML = `
            <div class="step-icon"><i class="bi ${step.icon}"></i></div>
            <div class="step-label">${step.label}</div>
        `;
        container.appendChild(div);

        // Connector (except after last)
        if (i < steps.length - 1) {
            const conn = document.createElement('div');
            conn.className = 'step-connector';
            container.appendChild(conn);
        }
    });
}

// ============================================================
// Search
// ============================================================

async function startSearch() {
    // Get profession from active select
    const profSelectId = selectedCountry === 'FR' ? 'profession-fr' : 'profession-be';
    const profSelect = document.getElementById(profSelectId);

    let profession = '';
    if (professionCustom.value.trim()) {
        profession = professionCustom.value.trim();
    } else if (profSelect.value) {
        profession = profSelect.value;
    } else {
        alert('Veuillez choisir une profession ou entrer un mot-cl\u00e9.');
        return;
    }

    // Get location from active region select
    const ville = document.getElementById('ville').value.trim();
    const regionSelectId = selectedCountry === 'FR' ? 'province-fr' : 'province-be';
    const region = document.getElementById(regionSelectId).value;
    const location = ville || region;

    // Options
    const maxResults = parseInt(maxResultsSlider.value);
    const useEnrich = document.getElementById('use-enrich').checked;
    const useDeepEmail = document.getElementById('use-deep-email').checked;

    // Build step indicators for selected country
    buildStepIndicators();

    // Reset UI
    resetProgress();
    showSection('progress');

    // Disable button
    btnSearch.disabled = true;
    btnSearch.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Lancement...';

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profession,
                location,
                max_results: maxResults,
                use_enrich: useEnrich,
                use_deep_email: useDeepEmail,
                country: selectedCountry,
            }),
        });

        const data = await response.json();
        if (data.error) {
            showError(data.error);
            return;
        }

        currentJobId = data.job_id;
        connectSSE(data.job_id);

    } catch (err) {
        showError(`Erreur de connexion : ${err.message}`);
    } finally {
        btnSearch.disabled = false;
        btnSearch.innerHTML = '<i class="bi bi-search me-2"></i> Lancer la recherche';
    }
}

// ============================================================
// SSE Progress
// ============================================================

function connectSSE(jobId) {
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource(`/api/progress/${jobId}`);

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.error) {
            eventSource.close();
            showError(data.error);
            return;
        }

        // Final status
        if (data.status === 'completed') {
            eventSource.close();
            onJobCompleted(jobId, data);
            return;
        }

        if (data.status === 'error') {
            eventSource.close();
            showError(data.error || 'Erreur inconnue');
            return;
        }

        // Progress update
        if (data.step && data.message) {
            updateProgress(data);
        }
    };

    eventSource.onerror = () => {
        eventSource.close();
        setTimeout(() => {
            if (progressSection.classList.contains('d-none')) return;
            fetch(`/api/results/${jobId}`)
                .then(r => r.json())
                .then(data => {
                    if (data.results) {
                        onJobCompleted(jobId, { stats: data.stats, email_stats: data.email_stats, result_count: data.results.length });
                    }
                })
                .catch(() => {});
        }, 2000);
    };
}

function updateProgress(data) {
    const { step, current, total, message } = data;
    const stepKeys = getStepKeys();
    const stepIndex = stepKeys.indexOf(step);
    const numSteps = stepKeys.length - 1; // exclude 'done'

    // Update step indicators
    document.querySelectorAll('.step-item').forEach(el => {
        const elStep = el.dataset.step;
        const elIndex = stepKeys.indexOf(elStep);
        if (elIndex < stepIndex) {
            el.classList.add('completed');
            el.classList.remove('active');
        } else if (elIndex === stepIndex) {
            el.classList.add('active');
            el.classList.remove('completed');
        } else {
            el.classList.remove('active', 'completed');
        }
    });

    // Update connectors
    document.querySelectorAll('.step-connector').forEach((el, i) => {
        if (i < stepIndex) {
            el.classList.add('completed');
        } else {
            el.classList.remove('completed');
        }
    });

    // Update progress bar
    if (total > 0) {
        const stepPct = (stepIndex / numSteps) * 100;
        const withinStepPct = (current / total) * (100 / numSteps);
        const totalPct = Math.min(Math.round(stepPct + withinStepPct), 100);
        progressBar.style.width = `${totalPct}%`;
        progressBar.textContent = `${totalPct}%`;
    }

    // Update message
    progressMessage.innerHTML = `<i class="bi bi-hourglass-split me-1"></i> ${escapeHtml(message)}`;

    // Add to log
    addLogEntry(message, step, current, total);
}

function addLogEntry(message, step, current, total) {
    const now = new Date();
    const time = now.toLocaleTimeString('fr-BE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const isDone = total > 0 && current >= total;

    const entry = document.createElement('div');
    entry.className = `log-entry${isDone ? ' step-done' : ''}`;
    entry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-msg">${isDone ? '<i class="bi bi-check-circle-fill text-success me-1"></i>' : ''}${escapeHtml(message)}</span>
    `;

    progressLog.appendChild(entry);
    progressLog.scrollTop = progressLog.scrollHeight;
}

function resetProgress() {
    progressBar.style.width = '0%';
    progressBar.textContent = '0%';
    progressBar.classList.add('progress-bar-animated');
    progressMessage.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Initialisation...';
    progressLog.innerHTML = '';
    progressSpinner.classList.remove('d-none');

    document.querySelectorAll('.step-item').forEach(el => {
        el.classList.remove('active', 'completed');
    });
    document.querySelectorAll('.step-connector').forEach(el => {
        el.classList.remove('completed');
    });
}

// ============================================================
// Job Completed
// ============================================================

async function onJobCompleted(jobId, summary) {
    // Mark all steps as completed
    document.querySelectorAll('.step-item').forEach(el => {
        el.classList.add('completed');
        el.classList.remove('active');
    });
    document.querySelectorAll('.step-connector').forEach(el => {
        el.classList.add('completed');
    });
    progressBar.style.width = '100%';
    progressBar.textContent = '100%';
    progressBar.classList.remove('progress-bar-animated');
    progressSpinner.classList.add('d-none');

    // Show stats
    const stats = summary.stats || {};
    document.getElementById('stat-total').textContent = stats.total || 0;
    document.getElementById('stat-phone').textContent = stats.with_phone || 0;
    document.getElementById('stat-email').textContent = stats.with_email || 0;
    document.getElementById('stat-website').textContent = stats.with_website || 0;

    // Fetch full results
    try {
        const resp = await fetch(`/api/results/${jobId}`);
        const data = await resp.json();

        if (data.results) {
            allResults = data.results;
            currentPage = 1;
            renderResults();
        }
    } catch (err) {
        console.error('Failed to fetch results:', err);
    }

    // Show results section after a short delay
    setTimeout(() => {
        showSection('results');
    }, 1000);
}

// ============================================================
// Results Rendering
// ============================================================

function renderResults() {
    const filter = tableFilter.value.toLowerCase().trim();

    // Filter
    let filtered = allResults;
    if (filter) {
        filtered = allResults.filter(r => {
            return Object.values(r).some(v =>
                String(v).toLowerCase().includes(filter)
            );
        });
    }

    // Sort
    if (sortCol) {
        filtered.sort((a, b) => {
            const va = String(a[sortCol] || '').toLowerCase();
            const vb = String(b[sortCol] || '').toLowerCase();
            const cmp = va.localeCompare(vb, 'fr');
            return sortDir === 'asc' ? cmp : -cmp;
        });
    }

    // Paginate
    const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
    const start = (currentPage - 1) * PAGE_SIZE;
    const pageItems = filtered.slice(start, start + PAGE_SIZE);

    // Render rows
    resultsBody.innerHTML = '';
    pageItems.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="fw-semibold">${escapeHtml(r.nom || '-')}</td>
            <td>${escapeHtml(r.ville || '')} ${r.code_postal ? `<small class="text-muted">(${escapeHtml(r.code_postal)})</small>` : ''}</td>
            <td>${r.telephone ? `<a href="tel:${r.telephone}">${escapeHtml(r.telephone)}</a>` : '<span class="text-muted">-</span>'}</td>
            <td>${r.email ? `<a href="mailto:${r.email}">${escapeHtml(r.email)}</a>` : '<span class="text-muted">-</span>'}</td>
            <td>${r.site_web ? `<a href="${escapeHtml(r.site_web)}" target="_blank" rel="noopener">${truncate(r.site_web, 30)}</a>` : '<span class="text-muted">-</span>'}</td>
            <td class="text-muted small">${escapeHtml(r.adresse || '')}</td>
        `;
        resultsBody.appendChild(tr);
    });

    // Results count
    resultsCount.textContent = `${filtered.length} r\u00e9sultat${filtered.length > 1 ? 's' : ''} affich\u00e9${filtered.length > 1 ? 's' : ''}`;

    // Pagination
    renderPagination(totalPages);
}

function renderPagination(totalPages) {
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    if (totalPages <= 1) return;

    // Previous
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#">&laquo;</a>`;
    prevLi.addEventListener('click', (e) => { e.preventDefault(); if (currentPage > 1) { currentPage--; renderResults(); } });
    pagination.appendChild(prevLi);

    // Page numbers
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${i === currentPage ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#">${i}</a>`;
        li.addEventListener('click', (e) => { e.preventDefault(); currentPage = i; renderResults(); });
        pagination.appendChild(li);
    }

    // Next
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#">&raquo;</a>`;
    nextLi.addEventListener('click', (e) => { e.preventDefault(); if (currentPage < totalPages) { currentPage++; renderResults(); } });
    pagination.appendChild(nextLi);
}

// ============================================================
// Error
// ============================================================

function showError(message) {
    document.getElementById('error-message').textContent = message;
    showSection('error');
}

// ============================================================
// Utilities
// ============================================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function truncate(text, maxLen) {
    if (!text) return '';
    text = text.replace(/^https?:\/\//, '').replace(/\/$/, '');
    if (text.length > maxLen) {
        return escapeHtml(text.substring(0, maxLen) + '...');
    }
    return escapeHtml(text);
}
