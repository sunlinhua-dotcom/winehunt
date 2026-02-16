/* ===== Wine Deal Hunter — App Logic ===== */

const API = '';

// ===== Navigation =====
function initNav() {
    const sidebarItems = document.querySelectorAll('.sidebar .nav-item');
    const mobileItems = document.querySelectorAll('.mobile-nav-item');
    const allNavItems = [...sidebarItems, ...mobileItems];

    allNavItems.forEach(item => {
        item.addEventListener('click', () => navigateTo(item.dataset.page));
        item.addEventListener('keypress', e => {
            if (e.key === 'Enter') navigateTo(item.dataset.page);
        });
    });
}

function navigateTo(page) {
    // Update nav items
    document.querySelectorAll('.nav-item, .mobile-nav-item').forEach(el => {
        el.classList.toggle('active', el.dataset.page === page);
    });

    // Update pages
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const target = document.getElementById('page-' + page);
    if (target) target.classList.add('active');

    // Load data
    switch (page) {
        case 'dashboard': loadDashboard(); break;
        case 'opportunities': loadOpportunities(); break;
        case 'wines': loadWineList(); break;
        case 'logs': loadLogs(); break;
        case 'watchlist': loadWatchlist(); break;
    }
}

// ===== Dashboard =====
async function loadDashboard() {
    try {
        const res = await fetch(API + '/api/stats');
        if (!res.ok) throw new Error('Failed to fetch stats');
        const data = await res.json();

        document.getElementById('todayOpps').textContent = data.today_opportunities || 0;
        document.getElementById('totalOpps').textContent = data.total_opportunities || 0;

        const maxP = data.max_profit_rate;
        const maxEl = document.getElementById('maxProfit');
        if (maxP && maxP > 0) {
            maxEl.textContent = maxP.toFixed(1) + '%';
            maxEl.className = 'stat-value ' + (maxP >= 30 ? 'success' : 'gold');
        } else {
            maxEl.textContent = '—';
        }

        const lastScanEl = document.getElementById('lastScan');
        if (data.last_scan_time) {
            lastScanEl.textContent = formatRelativeTime(data.last_scan_time);
        }

        // Load latest opportunities
        const oppsRes = await fetch(API + '/api/opportunities?limit=5');
        if (oppsRes.ok) {
            const data = await oppsRes.json();
            renderLatestOpps(data.opportunities || data || []);
        }
    } catch (e) {
        console.warn('Dashboard load error:', e);
    }
}

function renderLatestOpps(opps) {
    const container = document.getElementById('latestOpps');
    if (!opps || opps.length === 0) {
        container.innerHTML = `
            <div class="empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M8 22h8M12 18v4M12 2v7"/>
                    <path d="M7.5 9h9l-1 3.5c-.3 1-.8 1.9-1.5 2.6L12 17l-2-1.9A7.5 7.5 0 0 1 8.5 12.5L7.5 9z"/>
                </svg>
                <p>尚无捡漏机会</p>
                <p class="hint">点击「立即扫描」开始发现交易机会</p>
            </div>`;
        return;
    }
    container.innerHTML = opps.map(op => renderDealCard(op)).join('');
}

function renderDealCard(op) {
    const profitClass = op.profit_rate >= 30 ? 'fire' : (op.profit_rate >= 20 ? 'hot' : '');
    return `
        <div class="deal-card">
            <div class="deal-row">
                <div class="deal-info">
                    <div class="deal-name">${escHtml(op.wine_name)}</div>
                    <div class="deal-meta">
                        <span class="deal-meta-item">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                                <circle cx="12" cy="10" r="3"/>
                            </svg>
                            ${escHtml(op.source_region || '—')}
                        </span>
                        <span class="deal-meta-item">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                            </svg>
                            买入 <strong>$${(op.source_price || 0).toFixed(0)}</strong>
                        </span>
                        <span class="deal-meta-item">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                            </svg>
                            港卖 <strong>$${(op.hk_price || 0).toFixed(0)}</strong>
                        </span>
                    </div>
                    <div class="deal-badges">
                        <span class="badge badge-profit ${profitClass}">利润 ${op.profit_rate?.toFixed(1)}%</span>
                        ${op.source_region ? `<span class="badge badge-region">${escHtml(op.source_region)}</span>` : ''}
                        ${op.score ? `<span class="badge badge-score">评分 ${op.score}</span>` : ''}
                    </div>
                </div>
                <div class="deal-right">
                    <div class="deal-profit ${profitClass}">+${op.profit_rate?.toFixed(1)}%</div>
                </div>
            </div>
        </div>`;
}

// ===== Scan =====
let scanState = { running: false, timer: null, elapsed: 0 };

async function triggerScan() {
    const btn = document.getElementById('btnScan');
    if (scanState.running) return;

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>启动中…`;

    try {
        const res = await fetch(API + '/api/scan', { method: 'POST' });
        if (!res.ok) throw new Error('Scan failed');
        const data = await res.json();
        showToast('扫描已启动', 'info');
        startScanTracking(data.total || 50);
    } catch (e) {
        showToast('扫描启动失败: ' + e.message, 'error');
        btn.disabled = false;
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>立即扫描`;
    }
}

function startScanTracking(total) {
    scanState.running = true;
    scanState.elapsed = 0;

    const panel = document.getElementById('scanPanel');
    panel.classList.add('active');

    document.getElementById('scanTotal').textContent = total;
    document.getElementById('scanScanned').textContent = '0';
    document.getElementById('scanFound').textContent = '0';
    document.getElementById('scanErrors').textContent = '0';
    document.getElementById('scanProgressBar').style.width = '0%';
    document.getElementById('scanLog').innerHTML = '';

    // Update sidebar status
    updateSidebarStatus(true);

    // Timer
    scanState.timer = setInterval(() => {
        scanState.elapsed++;
        document.getElementById('scanTimer').textContent = formatDuration(scanState.elapsed);
    }, 1000);

    // Poll status
    pollScanStatus();
}

async function pollScanStatus() {
    if (!scanState.running) return;

    try {
        const res = await fetch(API + '/api/scan/status');
        if (res.ok) {
            const data = await res.json();
            updateScanUI(data);

            if (data.status === 'completed' || data.status === 'idle') {
                endScan(data);
                return;
            }
        }
    } catch (e) { /* ignore poll errors */ }

    setTimeout(pollScanStatus, 2000);
}

function updateScanUI(data) {
    const total = data.total || parseInt(document.getElementById('scanTotal').textContent) || 50;
    const scanned = data.scanned || 0;
    const found = data.found || 0;
    const errors = data.errors || 0;

    document.getElementById('scanScanned').textContent = scanned;
    document.getElementById('scanFound').textContent = found;
    document.getElementById('scanErrors').textContent = errors;

    const pct = Math.min((scanned / total) * 100, 100);
    document.getElementById('scanProgressBar').style.width = pct + '%';

    // Add log entries
    if (data.current_wine) {
        addScanLog('info', `正在扫描: ${data.current_wine}`);
    }
    if (data.last_result) {
        const cls = data.last_result.profit_rate > 0 ? 'found' : 'info';
        addScanLog(cls, data.last_result.message || `${data.last_result.wine}: ${data.last_result.profit_rate?.toFixed(1)}%`);
    }
}

function addScanLog(type, msg) {
    const container = document.getElementById('scanLog');
    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const div = document.createElement('div');
    div.className = 'scan-log-entry ' + type;
    div.textContent = `[${time}] ${msg}`;
    container.insertBefore(div, container.firstChild);

    // Keep only last 50 entries
    while (container.children.length > 50) {
        container.removeChild(container.lastChild);
    }
}

function endScan(data) {
    scanState.running = false;
    if (scanState.timer) clearInterval(scanState.timer);

    document.getElementById('scanProgressBar').style.width = '100%';
    addScanLog('found', `扫描完成，耗时 ${formatDuration(scanState.elapsed)}，发现 ${data?.found || 0} 条机会`);

    updateSidebarStatus(false);

    const btn = document.getElementById('btnScan');
    btn.disabled = false;
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>立即扫描`;

    // Reload dashboard
    setTimeout(() => {
        loadDashboard();
        showToast(`扫描完成，发现 ${data?.found || 0} 条机会`, 'success');
    }, 500);
}

function updateSidebarStatus(scanning) {
    const el = document.getElementById('sidebarStatus');
    if (scanning) {
        el.innerHTML = `<span class="scan-dot active"></span><span>扫描中…</span>`;
    } else {
        el.innerHTML = `<span class="scan-dot"></span><span>待命中</span>`;
    }
}

// ===== Opportunities =====
async function loadOpportunities() {
    const filter = document.getElementById('profitFilter')?.value || 0;
    const container = document.getElementById('oppsList');
    container.innerHTML = `<div class="loading"><span class="spinner"></span>加载中…</div>`;

    try {
        const res = await fetch(API + `/api/opportunities?min_profit=${filter}`);
        if (!res.ok) throw new Error('Failed');
        const opps = await res.json();
        const items = opps.opportunities || opps || [];

        if (items.length === 0) {
            container.innerHTML = `
                <div class="empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/></svg>
                    <p>未找到符合条件的机会</p>
                </div>`;
            return;
        }
        container.innerHTML = items.map(op => renderDealCard(op)).join('');
    } catch (e) {
        container.innerHTML = `<div class="empty"><p>加载失败</p></div>`;
    }
}

// ===== Search =====
async function searchWine() {
    const name = document.getElementById('searchInput').value.trim();
    if (!name) { showToast('请输入酒名', 'error'); return; }

    const region = document.getElementById('searchRegion').value;
    const container = document.getElementById('searchResults');
    container.innerHTML = `<div class="loading"><span class="spinner"></span>搜索中…（需爬取 Wine-Searcher，约 10 秒）</div>`;

    try {
        const res = await fetch(API + '/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                wine_name: name,
                region: region || 'default',
                category: '',
                profit_threshold: 15
            })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || '搜索失败');
        }
        const data = await res.json();
        renderSearchResult(container, data);
    } catch (e) {
        container.innerHTML = `<div class="empty"><p>搜索失败: ${escHtml(e.message)}</p></div>`;
    }
}

function renderSearchResult(container, data) {
    if (!data || data.error) {
        container.innerHTML = `<div class="empty"><p>${escHtml(data?.error || '无结果')}</p></div>`;
        return;
    }

    if (!data.found) {
        container.innerHTML = `
            <div class="empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <p>未找到「${escHtml(data.wine_name || '')}」的数据</p>
                <p class="hint">Wine-Searcher 可能暂时无法访问，或酒名需要调整</p>
            </div>`;
        return;
    }

    const profitRate = data.profit_rate || 0;
    const profitClass = profitRate > 0 ? 'positive' : 'negative';
    const profitBadge = profitRate >= 15 ? (profitRate >= 30 ? 'fire' : 'hot') : '';

    container.innerHTML = `
        <div class="result-card">
            <div class="result-header">
                <h3 class="result-title">${escHtml(data.wine_name || '—')}</h3>
                ${profitRate > 0 ? `<span class="badge badge-profit ${profitBadge}">${profitRate.toFixed(1)}%</span>` : ''}
            </div>
            <div class="result-grid">
                <div class="result-item">
                    <span class="result-label">全球最低价</span>
                    <span class="result-value">$${(data.global_lowest || 0).toFixed(2)}</span>
                </div>
                <div class="result-item">
                    <span class="result-label">香港均价</span>
                    <span class="result-value">${data.hk_average ? '$' + data.hk_average.toFixed(2) : '暂无数据'}</span>
                </div>
                <div class="result-item">
                    <span class="result-label">总采购成本</span>
                    <span class="result-value">$${(data.total_cost || 0).toFixed(2)}</span>
                </div>
                <div class="result-item">
                    <span class="result-label">利润率</span>
                    <span class="result-value ${profitClass}">${profitRate.toFixed(1)}%</span>
                </div>
                ${data.source_region ? `<div class="result-item"><span class="result-label">来源国家</span><span class="result-value">${escHtml(data.source_region)}</span></div>` : ''}
                ${data.source_merchant ? `<div class="result-item"><span class="result-label">最低价酒商</span><span class="result-value">${escHtml(data.source_merchant)}</span></div>` : ''}
                ${data.shipping_cost ? `<div class="result-item"><span class="result-label">运费/瓶</span><span class="result-value">$${data.shipping_cost.toFixed(2)}</span></div>` : ''}
            </div>
            ${data.buy_url ? `<div style="margin-top:12px;text-align:center"><a href="${escHtml(data.buy_url)}" target="_blank" rel="noopener" class="btn btn-primary" style="display:inline-flex;gap:6px;align-items:center"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>查看酒商</a></div>` : ''}
        </div>`;
}

// ===== Wine List =====
async function loadWineList() {
    const container = document.getElementById('winesList');
    try {
        const res = await fetch(API + '/api/wines');
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();
        renderWineGroups(container, data.categories || data);
    } catch (e) {
        container.innerHTML = `<div class="empty"><p>加载失败</p></div>`;
    }
}

function renderWineGroups(container, groups) {
    if (!groups || Object.keys(groups).length === 0) {
        container.innerHTML = `<div class="empty"><p>暂无数据</p></div>`;
        return;
    }

    const wineIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 22h8M12 18v4M12 2v7"/><path d="M7.5 9h9l-1 3.5c-.3 1-.8 1.9-1.5 2.6L12 17l-2-1.9A7.5 7.5 0 0 1 8.5 12.5L7.5 9z"/></svg>`;

    container.innerHTML = Object.entries(groups).map(([category, wines]) => `
        <div class="wine-group">
            <div class="wine-group-title">${escHtml(category)} (${wines.length})</div>
            <div class="wine-grid">
                ${wines.map(w => `
                    <div class="wine-chip" onclick="quickSearch('${escAttr(w.name)}')" title="搜索 ${escAttr(w.name)}">
                        ${wineIcon}
                        <div class="wine-chip-info">
                            <span class="wine-chip-name">${escHtml(w.name)}</span>
                            <span class="wine-chip-region">${escHtml(w.region || '')}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

function quickSearch(name) {
    navigateTo('search');
    document.getElementById('searchInput').value = name;
    searchWine();
}

// ===== Watchlist =====
async function loadWatchlist() {
    const container = document.getElementById('watchlistItems');
    try {
        const res = await fetch(API + '/api/watchlist');
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();
        const items = data.watchlist || data || [];

        if (!items || items.length === 0) {
            container.innerHTML = `
                <div class="empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
                    <p>监控酒单为空</p>
                    <p class="hint">添加您关注的酒款到这里</p>
                </div>`;
            return;
        }

        container.innerHTML = items.map(item => `
            <div class="deal-card">
                <div class="deal-row">
                    <div class="deal-info">
                        <div class="deal-name">${escHtml(item.wine_name)}</div>
                        <div class="deal-meta">
                            ${item.target_price ? `<span class="deal-meta-item">目标 <strong>$${item.target_price}</strong></span>` : ''}
                            <span class="deal-meta-item" style="color:var(--text-muted)">添加于 ${formatDate(item.created_at)}</span>
                        </div>
                    </div>
                    <div class="deal-right">
                        <button class="btn btn-danger btn-sm" onclick="removeWatchlist(${item.id})" aria-label="移除">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                                <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                            </svg>
                            移除
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<div class="empty"><p>加载失败</p></div>`;
    }
}

function toggleWatchlistForm() {
    document.getElementById('watchForm').classList.toggle('show');
}

async function addWatchlist() {
    const name = document.getElementById('watchName').value.trim();
    if (!name) { showToast('请输入酒名', 'error'); return; }

    const price = parseFloat(document.getElementById('watchPrice').value) || null;

    try {
        const res = await fetch(API + '/api/watchlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ wine_name: name, target_price: price })
        });
        if (!res.ok) throw new Error('Failed');

        document.getElementById('watchName').value = '';
        document.getElementById('watchPrice').value = '';
        document.getElementById('watchForm').classList.remove('show');

        showToast(`已添加: ${name}`, 'success');
        loadWatchlist();
    } catch (e) {
        showToast('添加失败', 'error');
    }
}

async function removeWatchlist(id) {
    try {
        const res = await fetch(API + `/api/watchlist/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed');
        showToast('已移除', 'success');
        loadWatchlist();
    } catch (e) {
        showToast('移除失败', 'error');
    }
}

// ===== Logs =====
async function loadLogs() {
    const container = document.getElementById('logsList');
    container.innerHTML = `<div class="loading"><span class="spinner"></span>加载中…</div>`;

    try {
        const res = await fetch(API + '/api/logs');
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();
        const logs = data.logs || data || [];

        if (!logs || logs.length === 0) {
            container.innerHTML = `<div class="empty"><p>暂无扫描记录</p></div>`;
            return;
        }

        container.innerHTML = logs.map(log => `
            <div class="log-entry">
                <div class="log-left">
                    <span class="log-dot ${log.found > 0 ? '' : 'empty'}"></span>
                    <span class="log-time">${formatDate(log.scan_time || log.created_at)}</span>
                </div>
                <div class="log-right">
                    <span class="log-metric">扫描 <strong>${log.scanned || 0}</strong> 款</span>
                    <span class="log-metric">发现 <strong>${log.found || 0}</strong> 条</span>
                    <span class="log-metric">耗时 <strong>${log.duration || '—'}</strong></span>
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<div class="empty"><p>加载失败</p></div>`;
    }
}

// ===== Utilities =====
function showToast(msg, type = 'info') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = 'toast ' + type + ' show';
    setTimeout(() => { el.classList.remove('show'); }, 3500);
}

function escHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function escAttr(str) {
    return (str || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

function formatDate(ts) {
    if (!ts) return '—';
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function formatRelativeTime(ts) {
    if (!ts) return '—';
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    const diff = Math.floor((Date.now() - d.getTime()) / 1000);
    if (diff < 60) return '刚刚';
    if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
    if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
    return Math.floor(diff / 86400) + ' 天前';
}

function formatDuration(s) {
    if (s < 60) return s + 's';
    const m = Math.floor(s / 60);
    return m + 'm ' + (s % 60) + 's';
}

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
    initNav();
    loadDashboard();
});
