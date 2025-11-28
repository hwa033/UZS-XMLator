// Dashboard JavaScript
// Verantwoordelijk voor real-time updates en test uitvoering

let isTestRunning = false;
// Number of days to aggregate for the chart (default 14)
let chartRangeDays = 14;
// Default chart mode: show counts + Success % (combined bar + line)
let chartMode = 'dual'; // 'stacked' | 'dual' | 'throughput'
// Alert thresholds (can be made configurable later)
const failureThresholdPct = 10; // flag when latest day's failure rate exceeds this
const throughputDropPct = 50;   // flag when throughput drops by this percent vs previous week
// Prevent attaching delegation multiple times
let _uzs_delegation_attached = false;

// Small UI helper functions for chart status (avoid ReferenceErrors)
function showChartLoading(show) {
    try {
        const el = document.getElementById('chart-status');
        const noDataEl = document.getElementById('chart-no-data');
        const errEl = document.getElementById('chart-error');
        if (noDataEl) noDataEl.style.display = 'none';
        if (errEl) errEl.style.display = 'none';
        if (!el) return;
        if (show) {
            el.style.display = 'block';
            el.textContent = 'Laden...';
        } else {
            el.style.display = 'none';
            el.textContent = '';
        }
    } catch (e) { console.debug('showChartLoading failed', e); }
}

function showChartError(msg) {
    try {
        const errEl = document.getElementById('chart-error');
        const statusEl = document.getElementById('chart-status');
        const noDataEl = document.getElementById('chart-no-data');
        if (statusEl) statusEl.style.display = 'none';
        if (noDataEl) noDataEl.style.display = 'none';
        if (!errEl) return;
        errEl.style.display = 'block';
        errEl.textContent = msg || 'Fout bij laden van grafiekgegevens.';
    } catch (e) { console.debug('showChartError failed', e); }
}

function showChartNoData(msg) {
    try {
        const noDataEl = document.getElementById('chart-no-data');
        const statusEl = document.getElementById('chart-status');
        const errEl = document.getElementById('chart-error');
        if (statusEl) statusEl.style.display = 'none';
        if (errEl) errEl.style.display = 'none';
        if (!noDataEl) return;
        noDataEl.style.display = 'block';
        noDataEl.textContent = msg || 'Geen gegevens beschikbaar voor deze periode.';
    } catch (e) { console.debug('showChartNoData failed', e); }
}

// Update huidige tijd
function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('nl-NL', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    const element = document.getElementById('current-time');
    if (element) {
        element.textContent = timeString;
    }
}

function flashMessage(msg) {
    if (window.toastr) { window.toastr.success(msg); return; }
    const el = document.createElement('div');
    el.textContent = msg;
    el.style.position = 'fixed'; el.style.right = '12px'; el.style.bottom = '12px'; el.style.background = '#0b1220'; el.style.color = '#fff'; el.style.padding = '8px 12px'; el.style.borderRadius = '6px'; el.style.zIndex = 9999; el.style.opacity = '0'; el.style.transition = 'opacity 0.18s';
    document.body.appendChild(el);
    requestAnimationFrame(() => el.style.opacity = '1');
    setTimeout(() => { el.style.opacity = '0'; setTimeout(()=>el.remove(),200); }, 2200);
}

async function fetchAndShowDrilldown(dateQ) {
    try {
        const resp = await fetch(`/api/xml/events?date=${encodeURIComponent(dateQ)}`);
        if (!resp.ok) throw new Error('API error');
        const body = await resp.json();
        const events = body.events || [];
        const container = document.getElementById('chart-drilldown');
        if (!container) return;
        if (events.length === 0) {
            container.innerHTML = `<div class="small text-muted">Geen events gevonden voor ${dateQ}</div>`;
            return;
        }
        let html = `<div class="table-responsive"><table class="table table-sm"><thead><tr><th>Tijdstip</th><th>Bestand</th><th>Succes</th><th>Size</th></tr></thead><tbody>`;
        events.forEach(ev => {
            const t = ev.tijdstip || ev.timestamp || ''; const fn = ev.filename || ev.output_path || ''; const ok = ev.success ? 'Ja' : 'Nee'; const size = ev.size ? `${ev.size} B` : '-';
            html += `<tr><td>${t}</td><td>${fn}</td><td>${ok}</td><td>${size}</td></tr>`;
        });
        html += `</tbody></table></div>`;
        container.innerHTML = html;
        container.scrollIntoView({behavior:'smooth', block:'start'});
    } catch (err) {
        console.error('Drilldown failed', err);
        alert('Fout bij ophalen drilldown-gegevens.');
    }
}
// Update recente activiteit sectie
function updateRecentActivity(historie) {
    const activityEl = document.getElementById('recent-activity');
    if (!activityEl) return;

    if (historie.length === 0) {
        activityEl.innerHTML = `
            <p class="text-muted text-center py-3">
                <i class="bi bi-clock-history fs-2 d-block mb-2"></i>
                Geen recente activiteit gevonden.
            </p>
        `;
        return;
    }

    // Toon laatste 5 activiteiten
    const recenteActiviteiten = historie.slice(-5).reverse();
    
    let html = '<div class="list-group">';
    recenteActiviteiten.forEach((item, index) => {
        const statusClass = item.success ? 'success' : 'danger';
        const statusIcon = item.success ? 'check-circle-fill' : 'x-circle-fill';
        const tijdstip = new Date(item.tijdstip).toLocaleString('nl-NL');
        
        html += `
            <div class="list-group-item list-group-item-action">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">
                        <i class="bi bi-${statusIcon} text-${statusClass}"></i>
                        Test Uitvoering ${recenteActiviteiten.length - index}
                    </h6>
                    <small class="text-muted">${tijdstip}</small>
                </div>
                <p class="mb-1">
                    Status: <span class="badge bg-${statusClass}">${item.success ? 'Geslaagd' : 'Gefaald'}</span>
                </p>
            </div>
        `;
    });
    html += '</div>';
    
    activityEl.innerHTML = html;
}

// Toon test resultaten
function displayTestResults(results) {
    const resultsEl = document.getElementById('test-results');
    const noResultsEl = document.getElementById('no-results');
    
    if (!resultsEl) return;

    const statusClass = results.success ? 'success' : 'danger';
    const statusIcon = results.success ? 'check-circle-fill' : 'x-circle-fill';
    const tijdstip = new Date(results.tijdstip).toLocaleString('nl-NL');

    resultsEl.innerHTML = `
        <div class="alert alert-${statusClass}" role="alert">
            <h5 class="alert-heading">
                <i class="bi bi-${statusIcon}"></i>
                ${results.success ? 'Test Geslaagd!' : 'Test Gefaald'}
            </h5>
            <hr>
            <p><strong>Tijdstip:</strong> ${tijdstip}</p>
        </div>
        
        ${results.uitvoer ? `
            <div class="card mb-3">
                <div class="card-header bg-light">
                    <i class="bi bi-terminal"></i> Test Uitvoer
                </div>
                <div class="card-body">
                    <pre class="mb-0" style="max-height: 300px; overflow-y: auto;">${escapeHtml(results.uitvoer)}</pre>
                </div>
            </div>
        ` : ''}
        
        ${results.foutmeldingen ? `
            <div class="card mb-3">
                <div class="card-header bg-danger text-white">
                    <i class="bi bi-exclamation-triangle"></i> Foutmeldingen
                </div>
                <div class="card-body">
                    <pre class="mb-0 text-danger" style="max-height: 300px; overflow-y: auto;">${escapeHtml(results.foutmeldingen)}</pre>
                </div>
            </div>
        ` : ''}
    `;

    resultsEl.classList.remove('d-none');
    if (noResultsEl) {
        noResultsEl.classList.add('d-none');
    }
}

// Escape HTML voor veilige weergave
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Voer test uit
async function runTests() {
    if (isTestRunning) return;
    
    isTestRunning = true;
    
    const runBtn = document.getElementById('run-tests-btn');
    const stopBtn = document.getElementById('stop-tests-btn');
    const progressEl = document.getElementById('test-progress');
    
    if (runBtn) runBtn.classList.add('d-none');
    if (stopBtn) stopBtn.classList.remove('d-none');
    if (progressEl) progressEl.classList.remove('d-none');
    
    try {
        const response = await fetch('/api/test/uitvoeren', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        let results = null;
        // Try to parse JSON if possible
        try {
            results = await response.json();
        } catch (err) {
            // If server returned non-json (HTML error), capture text
            const text = await response.text().catch(() => '');
            console.error('Server returned non-JSON response for test execution:', text);
            alert('Fout bij uitvoeren van testen (server error). Kijk in de serverlogs voor details.');
            return;
        }

        // Toon resultaten (ook wanneer success=false)
        displayTestResults(results);
        
        // Update dashboard
        await updateDashboardStats();
        
        // Scroll naar resultaten
        document.getElementById('test-results').scrollIntoView({ 
            behavior: 'smooth', 
            block: 'nearest' 
        });
        
    } catch (error) {
        console.error('Fout bij uitvoeren test:', error);
        alert('Fout bij uitvoeren van testen. Zie console voor details.');
    } finally {
        isTestRunning = false;
        if (runBtn) runBtn.classList.remove('d-none');
        if (stopBtn) stopBtn.classList.add('d-none');
        if (progressEl) progressEl.classList.add('d-none');
    }
}

// Haal dashboard-statistieken op en update UI-secties
async function updateDashboardStats() {
    // Fuller updater: fetch tiles, last test, throughput and recent activity
    try {
        showChartLoading(true);

        // Parallel fetches for tiles / last test / totals / throughput
        const [laatsteResp, totaalResp, throughputResp] = await Promise.allSettled([
            fetch('/api/test/laatste'),
            fetch('/api/test/totaal'),
            fetch(`/api/xml/throughput?days=${chartRangeDays}`)
        ]);

        // Templates
        // Template feature removed; skip templates fetching

        // Last test status/time
        try {
            if (laatsteResp.status === 'fulfilled' && laatsteResp.value.ok) {
                const lt = await laatsteResp.value.json();
                const statusEl = document.getElementById('last-test-status');
                const timeEl = document.getElementById('last-test-time');
                if (statusEl) statusEl.textContent = lt.status || 'Onbekend';
                if (timeEl) timeEl.textContent = lt.datum || '';
            }
        } catch (e) { console.debug('laatste test update failed', e); }

        // Total tests
        try {
            if (totaalResp.status === 'fulfilled' && totaalResp.value.ok) {
                const tt = await totaalResp.value.json();
                const el = document.getElementById('total-tests');
                if (el) el.textContent = tt.totaal || 0;
            }
        } catch (e) { console.debug('totaal tests update failed', e); }

        // Throughput / chart update
        try {
            if (throughputResp.status === 'fulfilled' && throughputResp.value.ok) {
                const body = await throughputResp.value.json();
                const payload = Array.isArray(body) ? body : (body && Array.isArray(body.aggregated) ? body.aggregated : []);
                if (payload.length > 0) {
                    // reuse existing chart updater
                    try { 
                        // Call fetchAndUpdateChart to keep single-source-of-truth
                        await fetchAndUpdateChart();
                    } catch (e) { console.debug('fetchAndUpdateChart failed', e); }
                    // Compute overall success rate across the returned period and update tile if present
                    try {
                        const totalAcross = payload.reduce((acc, it) => acc + (it.totaal || 0), 0);
                        const successAcross = payload.reduce((acc, it) => acc + (it.geslaagd || 0), 0);
                        const successEl = document.getElementById('success-rate');
                        if (successEl) {
                            if (totalAcross > 0) {
                                const pct = Math.round((successAcross / totalAcross) * 100);
                                successEl.textContent = pct + '%';
                            } else {
                                // leave server-rendered value or show placeholder
                                // do not overwrite with 0 unless explicitly known
                            }
                        }
                    } catch (e) { console.debug('updating success-rate tile failed', e); }
                } else {
                    showChartNoData('Geen gegevens beschikbaar voor de geselecteerde periode.');
                }
            } else {
                showChartError('Kon throughput data niet laden');
            }
        } catch (e) { console.debug('throughput update failed', e); }

        // Recent activity: fall back to fetching historie and update result page tiles if present
        try {
            const histResp = await fetch('/api/test/historie');
            if (histResp.ok) {
                const historie = await histResp.json();
                const histArray = Array.isArray(historie) ? historie : [];
                updateRecentActivity(histArray);
                // Update Resultaten page tiles if present
                try {
                    const elCount = document.getElementById('res-total-generated');
                    if (elCount) elCount.textContent = histArray.length;
                    const elSize = document.getElementById('res-total-size');
                    if (elSize) {
                        const totalSize = histArray.reduce((acc, it) => acc + (parseInt(it.size) || 0), 0);
                        elSize.textContent = totalSize + ' B';
                    }
                    const elLastStatus = document.getElementById('res-last-status');
                    const elLastTime = document.getElementById('res-last-time');
                    if ((elLastStatus || elLastTime) && histArray.length > 0) {
                        const latest = histArray[0];
                        if (elLastStatus) elLastStatus.textContent = latest.status || (latest.success ? 'Geslaagd' : 'Gefaald') || 'Onbekend';
                        if (elLastTime) elLastTime.textContent = latest.tijdstip || latest.datum || '';
                    }
                } catch (inner) { console.debug('result tiles update failed', inner); }
            } else {
                updateRecentActivity([]);
            }
        } catch (e) { console.debug('recent activity fetch failed', e); updateRecentActivity([]); }

        // Attach delegation for stat-card menu actions (copy/drilldown)
        try {
            if (!_uzs_delegation_attached) {
                const container = document.body;
                container.addEventListener('click', function (ev) {
                    const target = ev.target.closest && ev.target.closest('.stat-action-copy');
                    if (target) {
                        const value = target.dataset && (target.dataset.value || target.getAttribute('data-value'));
                        if (value) {
                            navigator.clipboard && navigator.clipboard.writeText(value).then(()=> flashMessage('Gekopieerd naar klembord'));
                        }
                        ev.preventDefault();
                        return;
                    }

                    const drill = ev.target.closest && ev.target.closest('.stat-action-drilldown');
                    if (drill) {
                        const dateQ = drill.dataset && drill.dataset.date;
                        if (dateQ) fetchAndShowDrilldown(dateQ);
                        ev.preventDefault();
                        return;
                    }
                });
                _uzs_delegation_attached = true;
            }
        } catch (e) { console.debug('delegation attach failed', e); }

        // Basic alerts: check latest day failure percentage and throughput drop
        try {
            if (throughputResp.status === 'fulfilled' && throughputResp.value.ok) {
                const body = await throughputResp.value.json();
                const payload = Array.isArray(body) ? body : (body && Array.isArray(body.aggregated) ? body.aggregated : []);
                if (payload.length > 1) {
                    const latest = payload[payload.length - 1];
                    if (latest && typeof latest.succes_percentage === 'number') {
                        const failPct = 100 - latest.succes_percentage;
                        if (failPct >= failureThresholdPct) {
                            flashMessage(`Waarschuwing: hoog faalpercentage (${failPct}% op ${latest.datum})`);
                        }
                    }
                    // throughput drop vs same weekday previous week (approx)
                    const prevIdx = Math.max(0, payload.length - 8);
                    const prev = payload[prevIdx];
                    const latestTotal = latest ? (latest.totaal || 0) : 0;
                    const prevTotal = prev ? (prev.totaal || 0) : 0;
                    if (prevTotal > 0 && latestTotal < prevTotal * (1 - throughputDropPct/100)) {
                        flashMessage('Waarschuwing: significante daling in throughput gedetecteerd.');
                    }
                }
            }
        } catch (e) { console.debug('alert checks failed', e); }

    } catch (err) {
        console.error('updateDashboardStats failed', err);
    } finally {
        showChartLoading(false);
    }
}

// Initialisatie
document.addEventListener('DOMContentLoaded', function() {
    // Update tijd elke seconde
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    
    // Laad initiële statistieken
    updateDashboardStats();
    // Laad initiële chart data
    try { fetchAndUpdateChart(); } catch(e) { console.debug('Chart update init failed:', e); }
    
    // Refresh statistieken elke 30 seconden
    setInterval(updateDashboardStats, 30000);
    // Refresh chart elke 30 seconden
    setInterval(fetchAndUpdateChart, 30000);
    
    // Event listeners
    const runTestsBtn = document.getElementById('run-tests-btn');
    if (runTestsBtn) {
        runTestsBtn.addEventListener('click', runTests);
    }
    
    console.log('📊 Dashboard geïnitialiseerd');
});

// Bind range select change to refresh chart
document.addEventListener('DOMContentLoaded', function() {
    const rangeSelect = document.getElementById('chart-range-select');
    if (rangeSelect) {
        rangeSelect.value = String(chartRangeDays || 14);
        rangeSelect.addEventListener('change', function (ev) {
            const v = parseInt(this.value, 10) || 7;
            chartRangeDays = v;
            // refresh chart with new range
            fetchAndUpdateChart();
        });
    }
});

// Adjust chart configuration to match the screenshot design
function initDashboardChart(initialData) {
    try {
        const ctx = document.getElementById('dashboard-chart');
        if (!ctx) return null;

        const ChartLib = window.Chart || window.chartjs || null;
        const errEl = document.getElementById('chart-error');
        if (!ChartLib) {
            console.debug('Chart.js niet gevonden — chart init uitgesteld.');
            try { if (errEl) errEl.style.display = 'block'; } catch (e) {}
            return null;
        }

        try { if (errEl) errEl.style.display = 'none'; } catch(e){}

        const labels = (initialData && initialData.labels) ? initialData.labels : [];
        const values = (initialData && initialData.values) ? initialData.values : [];

        // Grouped bar (not stacked) + separate line for Success % (y1)
        let config = {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '✅ Geslaagd',
                        data: values.successCounts || [],
                        backgroundColor: 'rgba(40, 167, 69, 0.95)',
                        borderRadius: 6
                    },
                    {
                        label: '❌ Gefaald',
                        data: values.failureCounts || [],
                        backgroundColor: 'rgba(220, 53, 69, 0.95)',
                        borderRadius: 6
                    },
                    {
                        type: 'line',
                        label: '📈 Succes %',
                        data: values.successPercentages || [],
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.12)',
                        tension: 0.3,
                        fill: false,
                        yAxisID: 'y1',
                        pointRadius: 4,
                        spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    },
                    legend: {
                        display: true,
                        position: 'right',
                        align: 'center',
                        labels: {
                            usePointStyle: true,
                            boxWidth: 12,
                            padding: 8,
                            font: { family: "Inter, Roboto, system-ui", size: 12 }
                        }
                    }
                },
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: {
                        stacked: false,
                        grid: { display: true, color: 'rgba(11,27,40,0.04)' },
                        ticks: { font: { family: "Inter, Roboto, system-ui" } }
                    },
                    y: {
                        stacked: false,
                        beginAtZero: true,
                        grid: { display: true, color: 'rgba(11,27,40,0.04)' },
                        ticks: {
                            stepSize: 1,
                            callback: function(value) { return Number(value) % 1 === 0 ? value : null; },
                            font: { family: "Inter, Roboto, system-ui" }
                        }
                    },
                    y1: {
                        position: 'right',
                        beginAtZero: true,
                        min: 0,
                        max: 100,
                        ticks: { callback: v => v + '%', font: { family: "Inter, Roboto, system-ui" } },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        };

        const chart = new ChartLib(ctx, config);
        window._uzs_dashboard_chart = chart;
        return chart;
    } catch (err) {
        console.error('Fout bij initialiseren dashboard chart:', err);
        return null;
    }
}

// Update chart data using app endpoints
async function fetchAndUpdateChart() {
    const loadingTimeoutMs = 7000;
    showChartLoading(true);

    const controller = new AbortController();
    const signal = controller.signal;
    const timeoutId = setTimeout(() => controller.abort(), loadingTimeoutMs);
    let payload = null;

    try {
        // The backend exposes `/api/xml/throughput` which returns
        // { aggregated: [ { datum, totaal, geslaagd, gefaald, succes_percentage }, ... ] }
        // Prefer newer `/api/xml-stats` if available, fall back to `/api/xml/throughput`
        let resp = null;
        try {
            resp = await fetch(`/api/xml-stats?days=${chartRangeDays}`, { signal });
            if (!resp.ok) throw new Error('not-found');
        } catch (e) {
            // fallback
            resp = await fetch(`/api/xml/throughput?days=${chartRangeDays}`, { signal });
        }
        clearTimeout(timeoutId);
        if (!resp.ok) throw new Error(`API responded with status ${resp.status}`);
        const body = await resp.json();
        // Normalize payload to an array for the chart logic
        if (Array.isArray(body)) {
            payload = body;
        } else if (body && Array.isArray(body.aggregated)) {
            payload = body.aggregated;
        } else {
            payload = [];
        }
    } catch (err) {
        clearTimeout(timeoutId);
        showChartError('Error loading chart data.');
        console.error('Error fetching chart data:', err);
        showChartLoading(false);
        return;
    }
    if (payload && Array.isArray(payload)) {
        // Backend items use Dutch keys: 'datum','totaal','geslaagd','gefaald','succes_percentage'
        // Format labels as MM-DD to match requested example (11-08)
        const labels = payload.map(item => {
            const d = item.datum || '';
            if (d.length === 10) return d.slice(5); // 'MM-DD'
            return d;
        });
        const successCounts = payload.map(item => item.geslaagd || 0);
        const failureCounts = payload.map(item => item.gefaald || 0);
        const totals = payload.map(item => item.totaal || 0);
        const successPercentages = payload.map(item => (item.succes_percentage == null) ? null : item.succes_percentage);

        if (totals.every(value => value === 0)) {
            const noDataEl = document.getElementById('chart-no-data');
            if (noDataEl) {
                noDataEl.style.display = 'block';
                noDataEl.textContent = 'Geen gegevens beschikbaar voor deze periode.';
            }
            showChartLoading(false);
            return;
        }

        const chart = window._uzs_dashboard_chart;
        if (!chart) {
            const initialData = {
                labels: labels,
                values: {
                    successCounts: successCounts,
                    failureCounts: failureCounts,
                    totals: totals,
                    successPercentages: successPercentages
                }
            };
            initDashboardChart(initialData);
        } else {
            chart.data.labels = labels;
            chart.data.datasets = [
                {
                    label: '✅ Geslaagd',
                    data: successCounts,
                    backgroundColor: 'rgba(40, 167, 69, 0.95)',
                    borderRadius: 6
                },
                {
                    label: '❌ Gefaald',
                    data: failureCounts,
                    backgroundColor: 'rgba(220, 53, 69, 0.95)',
                    borderRadius: 6
                },
                {
                    type: 'line',
                    label: '📈 Succes %',
                    data: successPercentages,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.12)',
                    tension: 0.3,
                    fill: false,
                    yAxisID: 'y1',
                    pointRadius: 4,
                    spanGaps: true
                }
            ];
            chart.options.scales = {
                x: { stacked: false, grid: { display: true, color: 'rgba(11,27,40,0.04)' } },
                y: { stacked: false, beginAtZero: true, grid: { display: true, color: 'rgba(11,27,40,0.04)' }, ticks: { stepSize: 1 } },
                y1: { position: 'right', beginAtZero: true, min: 0, max: 100, ticks: { callback: v => v + '%' }, grid: { drawOnChartArea: false } }
            };
            chart.update();
            // Ensure tile heights match the chart's viewport after update
            try { syncTileHeightsToChart(); } catch(e) { console.debug('syncTileHeightsToChart after update failed', e); }
        }
    }

    showChartLoading(false);
}

// Voeg een functie toe om data op te halen en de grafiek bij te werken
// Template/tile fetching removed — templates feature is not available in this build.

// Voeg een functie toe om data voor de tiles op te halen
async function fetchAndUpdateTestTiles() {
    // show spinners on relevant cards
    const lastCard = document.querySelector('#last-test-status') && document.querySelector('#last-test-status').closest('.stat-card');
    const totalCard = document.querySelector('#total-tests') && document.querySelector('#total-tests').closest('.stat-card');
    try {
        if (lastCard) lastCard.classList.add('loading');
        if (totalCard) totalCard.classList.add('loading');

        // Haal data op voor de laatste test
        const laatsteResponse = await fetch('/api/test/laatste');
        if (laatsteResponse && laatsteResponse.ok) {
            const laatsteTest = await laatsteResponse.json();
            const statusEl = document.getElementById('last-test-status');
            const timeEl = document.getElementById('last-test-time');
            if (statusEl) statusEl.textContent = laatsteTest.status || (laatsteTest.success ? 'Geslaagd' : 'Gefaald') || 'Onbekend';
            if (timeEl) timeEl.textContent = laatsteTest.datum || laatsteTest.tijdstip || '';
        } else {
            const statusEl = document.getElementById('last-test-status'); if (statusEl) statusEl.textContent = 'Niet beschikbaar';
        }

        // Haal data op voor totaal aantal tests
        const totaalResponse = await fetch('/api/test/totaal');
        if (totaalResponse && totaalResponse.ok) {
            const totaalTests = await totaalResponse.json();
            const el = document.getElementById('total-tests');
            if (el) el.textContent = totaalTests.totaal || 0;
        } else {
            const el = document.getElementById('total-tests'); if (el) el.textContent = 'Niet beschikbaar';
        }
    } catch (err) {
        console.error('Fout bij ophalen en bijwerken van test tiles:', err);
        const statusEl = document.getElementById('last-test-status'); if (statusEl) statusEl.textContent = 'Niet beschikbaar';
        const el = document.getElementById('total-tests'); if (el) el.textContent = 'Niet beschikbaar';
    } finally {
        if (lastCard) lastCard.classList.remove('loading');
        if (totalCard) totalCard.classList.remove('loading');
    }
}

// Format bytes into human-readable string
function formatBytes(bytes) {
    if (bytes == null || isNaN(bytes)) return 'Niet beschikbaar';
    bytes = Number(bytes);
    if (bytes === 0) return '0 B';
    const units = ['B','KB','MB','GB','TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    const value = parseFloat((bytes / Math.pow(1024, i)).toFixed(i ? 1 : 0));
    return `${value} ${units[i]}`;
}

// Roep de functie aan na DOMContentLoaded
try {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            fetchAndUpdateTestTiles();
        });
    } else {
        fetchAndUpdateTestTiles();
    }
} catch (e) {
    console.debug('Test tile update overslaan:', e);
}
// Note: template-related tiles have been removed; only test tiles are updated.

// Helper: debounce utility
function debounce(fn, wait) {
    let t = null;
    return function(...args) {
        if (t) clearTimeout(t);
        t = setTimeout(() => { fn.apply(this, args); t = null; }, wait);
    };
}

// Sync function: set chart-tile heights to match the chart-area viewport height
function syncTileHeightsToChart() {
    try {
        const chartArea = document.querySelector('.chart-area');
        const tiles = Array.from(document.querySelectorAll('.chart-tiles .chart-tile'));
        if (!chartArea || tiles.length === 0) return;

        // Prefer clientHeight (includes padding) to match visual height
        const areaHeight = chartArea.clientHeight || chartArea.offsetHeight || 0;
        // If the computed height is too small or zero, don't override
        if (!areaHeight || areaHeight < 40) return;

        // Mobile screens should stack; don't force heights there
        const isMobile = window.matchMedia('(max-width: 575.98px)').matches;
        tiles.forEach(tile => {
            if (isMobile) {
                tile.style.height = '';
            } else {
                // Keep a small breathing room so the tiles look visually balanced
                tile.style.height = areaHeight + 'px';
            }
        });
    } catch (err) {
        console.debug('syncTileHeightsToChart error', err);
    }
}

// Attach resize listener to keep tiles in sync as viewport / chart changes
try {
    window.addEventListener('resize', debounce(syncTileHeightsToChart, 120));
    // Also call once on DOM ready to initialize heights (chart may be rendered a bit later)
    document.addEventListener('DOMContentLoaded', function() {
        // Run a couple of times with small delays to cover async chart render timing
        setTimeout(syncTileHeightsToChart, 120);
        setTimeout(syncTileHeightsToChart, 800);
    });
} catch (e) { console.debug('Failed to attach resize listener for tile sync', e); }

// Log whether local Chart.js is being used
console.debug('Chart.js fallback mechanism triggered. Using local copy.');

// Report generation helpers
function csvEscape(val) {
    if (val == null) return '';
    const s = String(val);
    if (s.includes(',') || s.includes('"') || s.includes('\n')) {
        return '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
}

async function generateReport() {
    const days = document.getElementById('report-days') ? parseInt(document.getElementById('report-days').value, 10) : 7;
    const includeGeslaagd = document.getElementById('report-geslaagd') ? document.getElementById('report-geslaagd').checked : true;
    const includeGefaald = document.getElementById('report-gefaald') ? document.getElementById('report-gefaald').checked : true;
    const includeTotaal = document.getElementById('report-totaal') ? document.getElementById('report-totaal').checked : true;

    try {
        const resp = await fetch(`/api/xml/throughput?days=${days}`);
        if (!resp.ok) throw new Error('API error');
        const body = await resp.json();
        const payload = Array.isArray(body) ? body : (body && Array.isArray(body.aggregated) ? body.aggregated : []);
        if (!payload || payload.length === 0) {
            alert('Geen gegevens beschikbaar voor geselecteerde periode.');
            return;
        }

        // Build CSV header
        const headers = ['Datum'];
        if (includeGeslaagd) headers.push('Geslaagd');
        if (includeGefaald) headers.push('Gefaald');
        if (includeTotaal) headers.push('Totaal');
        headers.push('Succes %');

        const rows = [headers.join(',')];
        payload.forEach(item => {
            const cols = [csvEscape(item.datum || '')];
            if (includeGeslaagd) cols.push(csvEscape(item.geslaagd || 0));
            if (includeGefaald) cols.push(csvEscape(item.gefaald || 0));
            if (includeTotaal) cols.push(csvEscape(item.totaal || 0));
            cols.push(csvEscape(item.succes_percentage != null ? item.succes_percentage : ''));
            rows.push(cols.join(','));
        });

        const csv = rows.join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        // bestandsnaam CSV-rapport (gebruikelijk Engels bestandsextractie name kept)
        a.download = `uzs_report_${days}d_${new Date().toISOString().slice(0,10)}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        // Close modal if present
        try { var rb = document.getElementById('reportModal'); if (rb) { var modal = bootstrap.Modal.getInstance(rb); if (modal) modal.hide(); } } catch(e){}

    } catch (err) {
        console.error('Report generation failed', err);
        alert('Kon rapport niet genereren. Kijk in console voor details.');
    }
}

// Wire report button after DOM ready
document.addEventListener('DOMContentLoaded', function() {
    const openReport = document.getElementById('open-report-btn');
    if (openReport) {
        openReport.addEventListener('click', function() {
            const modalEl = document.getElementById('reportModal');
            if (modalEl) {
                const m = new bootstrap.Modal(modalEl, {});
                m.show();
            }
        });
    }

    const genBtn = document.getElementById('generate-report-btn');
    if (genBtn) genBtn.addEventListener('click', generateReport);
});