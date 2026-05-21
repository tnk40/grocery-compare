const API_URL = 'https://grocery-compare-production-394e.up.railway.app';

// ── State ─────────────────────────────────────────────────────────────────────
let token = localStorage.getItem('token');
let basket = [];
let preferredStore = localStorage.getItem('preferredStore') || '';
let switchThreshold = parseInt(localStorage.getItem('switchThreshold') || '15');
let stickToStore = localStorage.getItem('stickToStore') === 'true';

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatStoreName(store) {
    const names = {
        'aldi': 'Aldi',
        'asda': 'ASDA',
        'morrisons': 'Morrisons',
        'sainsburys': "Sainsbury's",
        'waitrose': 'Waitrose'
    };
    return names[store] || (store ? store.charAt(0).toUpperCase() + store.slice(1) : '');
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    if (token) showMainApp();
});

// ── Auth ──────────────────────────────────────────────────────────────────────
async function register() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    try {
        const res = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok) { token = data.access_token; localStorage.setItem('token', token); showMainApp(); }
        else showAuthError(data.detail || 'Registration failed');
    } catch { showAuthError('Connection error.'); }
}

async function login() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    try {
        const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok) { token = data.access_token; localStorage.setItem('token', token); showMainApp(); }
        else showAuthError(data.detail || 'Login failed');
    } catch { showAuthError('Connection error.'); }
}

function logout() {
    token = null;
    localStorage.removeItem('token');
    basket = [];
    document.getElementById('login-section').style.display = 'flex';
    document.getElementById('main-section').style.display = 'none';
}

function showAuthError(msg) {
    document.getElementById('auth-message').textContent = msg;
}

// ── Main App ──────────────────────────────────────────────────────────────────
async function showMainApp() {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('main-section').style.display = 'block';

    try {
        const res = await fetch(`${API_URL}/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const user = await res.json();
            document.getElementById('user-email').textContent = user.email;
        } else { logout(); return; }
    } catch { logout(); return; }

    // Restore slider state
    const slider = document.getElementById('threshold-slider');
    if (slider) {
        slider.value = switchThreshold;
        document.getElementById('threshold-label').textContent = `${switchThreshold}%`;
    }

    // Restore stick-to-store toggle
    const stickToggle = document.getElementById('stick-to-store');
    if (stickToggle) stickToggle.checked = stickToStore;
    applyStickToStoreUI();

    // Enter key → smart match
    document.getElementById('search-input').addEventListener('keypress', e => {
        if (e.key === 'Enter') smartMatch();
    });

    await Promise.all([loadStores(), loadSavedLists()]);
}

// ── Store Preferences ─────────────────────────────────────────────────────────
async function loadStores() {
    try {
        const res = await fetch(`${API_URL}/stores`);
        const stores = await res.json();
        const select = document.getElementById('preferred-store');
        select.innerHTML = '<option value="">No preference</option>';
        stores.forEach(store => {
            const opt = document.createElement('option');
            opt.value = store;
            opt.textContent = formatStoreName(store);
            if (store === preferredStore) opt.selected = true;
            select.appendChild(opt);
        });
    } catch { console.error('Failed to load stores'); }
}

function updatePreferredStore(value) {
    preferredStore = value;
    localStorage.setItem('preferredStore', value);
    calculatePrices();
}

function updateSwitchThreshold(value) {
    switchThreshold = parseInt(value);
    localStorage.setItem('switchThreshold', value);
    document.getElementById('threshold-label').textContent = `${value}%`;
    calculatePrices();
}

function updateStickToStore(checked) {
    stickToStore = checked;
    localStorage.setItem('stickToStore', checked ? 'true' : 'false');
    applyStickToStoreUI();
    calculatePrices();
}

function applyStickToStoreUI() {
    const slider = document.getElementById('threshold-slider');
    const sliderPref = document.querySelector('.pref-slider');
    if (slider) slider.disabled = stickToStore;
    if (sliderPref) sliderPref.style.opacity = stickToStore ? '0.4' : '';
}

// ── Search helpers ────────────────────────────────────────────────────────────
function showSearchStatus(msg) {
    const el = document.getElementById('search-results');
    el.style.display = 'block';
    el.innerHTML = `<p class="search-status">${msg}</p>`;
}

function clearSearch() {
    document.getElementById('search-input').value = '';
    document.getElementById('quantity').value = 1;
    const el = document.getElementById('search-results');
    el.style.display = 'none';
    el.innerHTML = '';
}

// ── Smart Match (ML) ──────────────────────────────────────────────────────────
async function smartMatch() {
    const query = document.getElementById('search-input').value.trim();
    if (!query) return;
    const quantity = parseInt(document.getElementById('quantity').value) || 1;
    showSearchStatus('Matching…');

    try {
        const storeFilter = stickToStore && preferredStore ? `&store=${encodeURIComponent(preferredStore)}` : '';
        const res = await fetch(`${API_URL}/match-best?q=${encodeURIComponent(query)}${storeFilter}`);
        const products = await res.json();

        if (!products.length) {
            showSearchStatus('No match found. Try Search for manual lookup.');
            return;
        }

        const cleanName = products[0].name_clean;
        const existing = basket.find(b => b.name_clean === cleanName);
        if (existing) {
            existing.quantity += quantity;
        } else {
            const newItem = { name_clean: cleanName, query, products, quantity, type: 'matched' };
            // In stick-to-store mode, auto-select the top match as the active product
            if (stickToStore && preferredStore && products.length > 1) {
                newItem.selectedProduct = products[0];
            }
            basket.push(newItem);
        }

        clearSearch();
        renderBasket();
        calculatePrices();
    } catch { showSearchStatus('Error connecting to server.'); }
}

// ── Manual Search ─────────────────────────────────────────────────────────────
async function manualSearch() {
    const query = document.getElementById('search-input').value.trim();
    if (!query) return;
    showSearchStatus('Searching…');

    try {
        const res = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}&top_k=30`);
        const results = await res.json();
        if (!results.length) { showSearchStatus('No products found.'); return; }
        renderSearchResults(results);
    } catch { showSearchStatus('Error connecting to server.'); }
}

function renderSearchResults(results) {
    const container = document.getElementById('search-results');
    container.style.display = 'block';
    container.innerHTML = results.map(r =>
        `<div class="search-result-item" onclick='addSpecificToBasket(${JSON.stringify(r).replace(/'/g, "&#39;")})'>
            <div class="result-info">
                <span class="result-name">${r.name}</span>
                <span class="result-store">${formatStoreName(r.store)}</span>
            </div>
            <span class="result-price">£${r.price.toFixed(2)}</span>
        </div>`
    ).join('');
}

// ── Basket ────────────────────────────────────────────────────────────────────
function addSpecificToBasket(product) {
    const quantity = parseInt(document.getElementById('quantity').value) || 1;
    basket.push({ name: product.name, store: product.store, price: product.price, quantity, type: 'specific' });
    clearSearch();
    renderBasket();
    calculatePrices();
}

function removeFromBasket(index) {
    basket.splice(index, 1);
    renderBasket();
    calculatePrices();
}

function clearBasket() {
    basket = [];
    renderBasket();
    calculatePrices();
}

function renderBasket() {
    const tbody = document.getElementById('basket-body');
    const tfoot = document.getElementById('basket-tfoot');
    if (!basket.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-basket">Your basket is empty</td></tr>';
        if (tfoot) tfoot.style.display = 'none';
        return;
    }
    tbody.innerHTML = '';
    let basketTotal = 0;
    basket.forEach((item, index) => {
        const row = document.createElement('tr');
        if (item.type === 'matched') {
            const confident = item.products.filter(p => p.confident || p.similarity >= 0.85);
            const pool = confident.length ? confident : item.products;
            const displayProduct = item.selectedProduct || pool.reduce((min, p) => p.price < min.price ? p : min);
            const unitPrice = displayProduct.price;
            const lineTotal = unitPrice * item.quantity;
            basketTotal += lineTotal;
            const safeName = displayProduct.name.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            const safeStore = displayProduct.store.replace(/'/g, "\\'");
            row.innerHTML = `
                <td class="basket-item-name" onclick="showMatchAlternatives(${index})">
                    ${displayProduct.name}
                    <span class="basket-item-tag matched">${formatStoreName(displayProduct.store)}</span>
                </td>
                <td>${item.quantity}</td>
                <td>\u00a3${unitPrice.toFixed(2)}</td>
                <td>\u00a3${lineTotal.toFixed(2)}</td>
                <td><button class="sub-btn" title="Find cheaper alternatives" onclick="event.stopPropagation();showSubstitutes('${safeName}','${safeStore}')">&#8597;</button></td>
                <td><button class="remove-btn" onclick="removeFromBasket(${index})">&#215;</button></td>`;
        } else {
            const lineTotal = (item.price || 0) * item.quantity;
            basketTotal += lineTotal;
            const safeName = item.name.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            const safeStore = (item.store || '').replace(/'/g, "\\'");
            row.innerHTML = `
                <td class="basket-item-name" onclick="showSubstitutes('${safeName}','${safeStore}')">
                    ${item.name}
                    <span class="basket-item-tag specific">${formatStoreName(item.store || '')}</span>
                </td>
                <td>${item.quantity}</td>
                <td>${item.price ? '\u00a3' + item.price.toFixed(2) : '\u2014'}</td>
                <td>${item.price ? '\u00a3' + lineTotal.toFixed(2) : '\u2014'}</td>
                <td></td>
                <td><button class="remove-btn" onclick="removeFromBasket(${index})">&#215;</button></td>`;
        }
        tbody.appendChild(row);
    });
    if (tfoot) {
        tfoot.style.display = '';
        document.getElementById('basket-total-value').textContent = `\u00a3${basketTotal.toFixed(2)}`;
    }
    updateSyncStoreOptions();
    const syncBar = document.getElementById('sync-store-bar');
    if (syncBar) syncBar.style.display = basket.length ? '' : 'none';
}

// ── Match Alternatives ────────────────────────────────────────────────────────
async function showMatchAlternatives(basketIndex) {
    const item = basket[basketIndex];
    if (item.type !== 'matched') {
        showSubstitutes(item.name, item.store);
        return;
    }
    const panel = document.getElementById('substitutes-panel');
    const overlay = document.getElementById('substitutes-overlay');
    const content = document.getElementById('substitutes-content');
    panel.querySelector('.sub-panel-header h3').textContent = 'Store Alternatives';

    // Open immediately with store alternatives from cached products
    content.innerHTML = '';
    panel.classList.add('open');
    overlay.classList.add('open');

    const allSameStore = item.products.length > 0 &&
        item.products.every(p => p.store === item.products[0].store);

    let sorted;
    if (allSameStore) {
        // Same-store mode: show all variants sorted by similarity (best match first)
        sorted = [...item.products].sort((a, b) => b.similarity - a.similarity);
    } else {
        const confident = item.products.filter(p => p.confident || p.similarity >= 0.85);
        const pool = confident.length ? confident : item.products;
        sorted = [...pool].sort((a, b) => a.price - b.price);
    }

    // Section 1: product options
    const storesCtx = document.createElement('p');
    storesCtx.className = 'sub-context';
    storesCtx.innerHTML = allSameStore
        ? `Options at ${formatStoreName(item.products[0].store)}`
        : `Same product at other stores`;
    content.appendChild(storesCtx);

    sorted.forEach(p => {
        const isSelected = item.selectedProduct?.store === p.store;
        const div = document.createElement('div');
        div.className = 'sub-item' + (isSelected ? ' selected' : '');
        div.innerHTML = `
            <div class="sub-info">
                <div>
                    <div class="sub-name">${p.name}</div>
                    <div class="sub-store">${formatStoreName(p.store)}</div>
                </div>
                <div class="sub-pricing">
                    <div class="sub-price">\u00a3${p.price.toFixed(2)}</div>
                </div>
            </div>`;
        const btn = document.createElement('button');
        btn.className = 'btn btn-small swap-btn ' + (isSelected ? 'btn-primary' : 'btn-outline');
        btn.textContent = isSelected ? '\u2713 Selected' : 'Use this';
        btn.onclick = (e) => { e.stopPropagation(); swapBasketItem(basketIndex, p); };
        div.querySelector('.sub-pricing').appendChild(btn);
        content.appendChild(div);
    });

    // Section 2: cheaper substitute products from API
    const subsCtx = document.createElement('p');
    subsCtx.className = 'sub-context alt-section';
    subsCtx.textContent = 'Cheaper alternatives';
    content.appendChild(subsCtx);

    const loadingEl = document.createElement('p');
    loadingEl.className = 'search-status';
    loadingEl.textContent = 'Loading\u2026';
    content.appendChild(loadingEl);

    const refProduct = item.selectedProduct || sorted[0];
    try {
        const res = await fetch(
            `${API_URL}/substitutes?product=${encodeURIComponent(refProduct.name)}&store=${encodeURIComponent(refProduct.store)}&top_k=5`
        );
        const subs = await res.json();
        loadingEl.remove();
        if (!subs.length) {
            const none = document.createElement('p');
            none.className = 'search-status';
            none.textContent = 'No cheaper alternatives found.';
            content.appendChild(none);
        } else {
            subs.forEach(s => {
                const div = document.createElement('div');
                div.className = 'sub-item';
                div.innerHTML = `
                    <div class="sub-info">
                        <div>
                            <div class="sub-name">${s.substitute_name}</div>
                            <div class="sub-store">${formatStoreName(s.substitute_store)}</div>
                        </div>
                        <div class="sub-pricing">
                            <div class="sub-price">\u00a3${s.substitute_price.toFixed(2)}</div>
                            <div class="sub-saving">Save \u00a3${s.saving.toFixed(2)} (${s.saving_pct.toFixed(0)}%)</div>
                        </div>
                    </div>`;
                const btn = document.createElement('button');
                btn.className = 'btn btn-small btn-outline swap-btn';
                btn.textContent = 'Swap';
                const subProduct = {
                    name: s.substitute_name,
                    store: s.substitute_store,
                    price: s.substitute_price,
                    similarity: s.cosine_similarity || 0,
                    confident: false
                };
                btn.onclick = (e) => { e.stopPropagation(); swapBasketItem(basketIndex, subProduct); };
                div.querySelector('.sub-pricing').appendChild(btn);
                content.appendChild(div);
            });
        }
    } catch {
        loadingEl.textContent = 'Could not load cheaper alternatives.';
    }
}

function swapBasketItem(basketIndex, product) {
    basket[basketIndex].selectedProduct = product;
    closeSubstitutesPanel();
    renderBasket();
    calculatePrices();
}

function updateSyncStoreOptions() {
    const select = document.getElementById('sync-store-select');
    if (!select) return;
    const stores = new Set();
    basket.forEach(item => {
        if (item.type === 'matched') item.products.forEach(p => stores.add(p.store));
        else if (item.store) stores.add(item.store);
    });
    const current = select.value;
    select.innerHTML = '<option value="">Auto-pick</option>' +
        [...stores].sort().map(s => `<option value="${s}"${s === current ? ' selected' : ''}>${formatStoreName(s)}</option>`).join('');
}

function syncToOneStore(storeOverride) {
    if (!basket.length) return;
    let targetStore = storeOverride;
    if (!targetStore) {
        const selectEl = document.getElementById('sync-store-select');
        targetStore = selectEl ? selectEl.value : '';
    }
    if (!targetStore) {
        // Auto-detect: store whose cheapest product appears most across basket items
        const storeCounts = {};
        basket.forEach(item => {
            if (item.type !== 'matched') return;
            const conf = item.products.filter(p => p.confident || p.similarity >= 0.85);
            const pool = conf.length ? conf : item.products;
            if (!pool.length) return;
            const cheapest = pool.reduce((min, p) => p.price < min.price ? p : min);
            storeCounts[cheapest.store] = (storeCounts[cheapest.store] || 0) + 1;
        });
        const best = Object.entries(storeCounts).sort((a, b) => b[1] - a[1])[0];
        targetStore = best ? best[0] : '';
        if (!targetStore) return;
    }

    let synced = 0, skipped = 0;
    basket.forEach(item => {
        if (item.type !== 'matched') return;
        const storeProduct = item.products.find(p => p.store === targetStore);
        if (storeProduct) {
            item.selectedProduct = storeProduct;
            synced++;
        } else {
            skipped++;
        }
    });

    renderBasket();
    calculatePrices();

    const msg = document.getElementById('sync-message');
    if (msg) {
        let text = `Synced to ${formatStoreName(targetStore)}`;
        if (skipped) text += ` · ${skipped} item${skipped > 1 ? 's' : ''} unavailable, kept as-is`;
        msg.textContent = text;
        setTimeout(() => { msg.textContent = ''; }, 4000);
    }
}

// ── Price Calculation ─────────────────────────────────────────────────────────
function clearPriceComparison() {
    document.getElementById('recommendations-body').innerHTML = '';
    document.getElementById('totals-body').innerHTML = '';
    document.getElementById('savings-text').textContent = '';
    document.getElementById('savings').style.display = 'none';
}

function calculatePrices() {
    if (!basket.length) { clearPriceComparison(); return; }

    // cheapestOptions: one row per basket item — lowest-price confident match
    const cheapestOptions = [];
    // storeData: per-store totals and item breakdown
    const storeData = {}; // store → { total, items:[{name,price,qty}], unavailableCount }

    basket.forEach(item => {
        if (item.type === 'matched') {
            const activeProducts = (stickToStore && preferredStore)
                ? item.products.filter(p => p.store === preferredStore)
                : item.products;
            if (!activeProducts.length) {
                cheapestOptions.push({ label: item.name_clean, store: preferredStore, price: 0, uncertain: true });
                return;
            }
            // Best product per store: products are sorted by similarity desc, so first seen = best
            const bestPerStore = {};
            activeProducts.forEach(p => {
                if (!bestPerStore[p.store]) bestPerStore[p.store] = p;
            });
            // In stick-to-store mode, respect the user's selected variant
            if (stickToStore && preferredStore && item.selectedProduct) {
                bestPerStore[preferredStore] = item.selectedProduct;
            }
            const storeList = Object.values(bestPerStore);

            const confident = storeList.filter(p => p.confident || p.similarity >= 0.85);
            const pool = confident.length ? confident : storeList;
            const cheapest = pool.reduce((min, p) => p.price < min.price ? p : min);
            cheapestOptions.push({
                label: item.name_clean,
                store: cheapest.store,
                price: cheapest.price * item.quantity,
                uncertain: !confident.length
            });

            // One product per store → add to store total
            storeList.forEach(p => {
                if (!storeData[p.store]) storeData[p.store] = { total: 0, items: [], unavailableCount: 0 };
                const isConfident = p.confident || p.similarity >= 0.85;
                if (isConfident) {
                    storeData[p.store].total += p.price * item.quantity;
                    storeData[p.store].items.push({ name: p.name, price: p.price, qty: item.quantity });
                } else {
                    storeData[p.store].unavailableCount++;
                    storeData[p.store].items.push({ name: p.name, price: null, qty: item.quantity });
                }
            });
        } else {
            cheapestOptions.push({
                label: item.name,
                store: item.store || '\u2014',
                price: (item.price || 0) * item.quantity
            });
            const st = item.store;
            if (st) {
                if (!storeData[st]) storeData[st] = { total: 0, items: [], unavailableCount: 0 };
                storeData[st].total += (item.price || 0) * item.quantity;
                storeData[st].items.push({ name: item.name, price: item.price, qty: item.quantity });
            }
        }
    });

    // Render cheapest options table
    const recBody = document.getElementById('recommendations-body');
    recBody.innerHTML = cheapestOptions.map(opt => `
        <tr>
            <td>${opt.label}</td>
            <td>${formatStoreName(opt.store)}</td>
            <td>\u00a3${opt.price.toFixed(2)}${opt.uncertain ? ' <span class="unavail-note">(low confidence)</span>' : ''}</td>
        </tr>`).join('');

    // Render store totals with expandable rows
    const totalsBody = document.getElementById('totals-body');
    const sorted = Object.entries(storeData).sort((a, b) => a[1].total - b[1].total);
    if (!sorted.length) return;

    const cheapestTotal = sorted[0][1].total;
    const mostExpensive = sorted[sorted.length - 1][1].total;

    totalsBody.innerHTML = sorted.map(([store, data], i) => {
        const unavailNote = data.unavailableCount
            ? ` <span class="unavail-note">(${data.unavailableCount} item${data.unavailableCount > 1 ? 's' : ''} unavailable)</span>`
            : '';
        const itemRows = data.items.map(it =>
            `<tr class="store-detail-item">
                <td class="detail-name">${it.name}</td>
                <td class="detail-price">${it.price !== null ? `\u00a3${it.price.toFixed(2)}${it.qty > 1 ? ` \u00d7${it.qty}` : ''}` : '<em>unavailable</em>'}</td>
            </tr>`
        ).join('');
        return `
            <tr class="store-total-row${i === 0 ? ' cheapest' : ''}" onclick="toggleStoreDetail('${store}')">
                <td>${formatStoreName(store)}${i === 0 ? ' <span class="checkmark">\u2713</span>' : ''}${unavailNote}</td>
                <td>\u00a3${data.total.toFixed(2)} <span class="expand-icon">\u25b8</span></td>
            </tr>
            <tr class="store-detail-row" id="store-detail-${store}" style="display:none">
                <td colspan="2" class="store-detail-cell">
                    <table class="store-detail-table">${itemRows}</table>
                </td>
            </tr>`;
    }).join('');

    const savings = mostExpensive - cheapestTotal;
    const savingsDiv = document.getElementById('savings');
    const savingsText = document.getElementById('savings-text');
    if (savings > 0.005) {
        savingsText.textContent = `You could save \u00a3${savings.toFixed(2)} shopping at ${formatStoreName(sorted[0][0])}!`;
        savingsDiv.style.display = 'block';
    } else {
        savingsText.textContent = '';
        savingsDiv.style.display = 'none';
    }
}

function toggleStoreDetail(store) {
    const row = document.getElementById(`store-detail-${store}`);
    if (!row) return;
    const isOpen = row.style.display !== 'none';
    row.style.display = isOpen ? 'none' : '';
    const totalRow = row.previousElementSibling;
    if (totalRow) {
        const icon = totalRow.querySelector('.expand-icon');
        if (icon) icon.textContent = isOpen ? '\u25b8' : '\u25be';
    }
}

// ── Substitutes ───────────────────────────────────────────────────────────────
async function showSubstitutes(productName, store) {
    const panel = document.getElementById('substitutes-panel');
    const overlay = document.getElementById('substitutes-overlay');
    const content = document.getElementById('substitutes-content');

    panel.querySelector('.sub-panel-header h3').textContent = 'Cheaper Alternatives';
    content.innerHTML = '<p class="search-status">Loading alternatives…</p>';
    panel.classList.add('open');
    overlay.classList.add('open');

    try {
        const res = await fetch(
            `${API_URL}/substitutes?product=${encodeURIComponent(productName)}&store=${encodeURIComponent(store)}&top_k=5`
        );
        const subs = await res.json();
        renderSubstitutesContent(subs, productName);
    } catch {
        content.innerHTML = '<p class="search-status">Failed to load alternatives.</p>';
    }
}

function renderSubstitutesContent(subs, productName) {
    const content = document.getElementById('substitutes-content');
    if (!subs.length) {
        content.innerHTML = `<p class="search-status">No cheaper alternatives found.</p>`;
        return;
    }
    content.innerHTML = `
        <p class="sub-context">Cheaper alternatives for<br><strong>${productName}</strong></p>
        ${subs.map(s => `
        <div class="sub-item">
            <div class="sub-info">
                <span class="sub-name">${s.substitute_name}</span>
                <span class="sub-store">${formatStoreName(s.substitute_store)}</span>
            </div>
            <div class="sub-pricing">
                <span class="sub-price">£${s.substitute_price.toFixed(2)}</span>
                <span class="sub-saving">Save £${s.saving.toFixed(2)} (${s.saving_pct.toFixed(0)}%)</span>
            </div>
        </div>`).join('')}`;
}

function closeSubstitutesPanel() {
    document.getElementById('substitutes-panel').classList.remove('open');
    document.getElementById('substitutes-overlay').classList.remove('open');
}

// ── Saved Lists ───────────────────────────────────────────────────────────────
async function loadSavedLists() {
    try {
        const res = await fetch(`${API_URL}/lists`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) renderSavedLists(await res.json());
    } catch { console.error('Failed to load lists'); }
}

function renderSavedLists(lists) {
    const container = document.getElementById('saved-lists');
    if (!lists.length) {
        container.innerHTML = '<p class="empty-note">No saved lists yet</p>';
        return;
    }
    container.innerHTML = lists.map(list => `
        <div class="saved-list-item">
            <span>${list.name} <span class="list-count">${list.items.length} items</span></span>
            <div class="saved-list-actions">
                <button class="btn btn-small btn-primary" onclick="loadList(${list.id})">Load</button>
                <button class="btn btn-small btn-danger" onclick="deleteList(${list.id})">Delete</button>
            </div>
        </div>`).join('');
}

async function saveList() {
    const name = document.getElementById('list-name').value.trim() || 'My Shopping List';
    if (!basket.length) { document.getElementById('save-message').textContent = 'Basket is empty!'; return; }

    const items = basket.map(b => ({
        item_name: b.type === 'matched' ? b.name_clean : b.name,
        quantity: b.quantity
    }));

    try {
        const res = await fetch(`${API_URL}/lists`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ name, items })
        });
        if (res.ok) {
            document.getElementById('save-message').textContent = 'List saved!';
            document.getElementById('list-name').value = '';
            await loadSavedLists();
            setTimeout(() => { document.getElementById('save-message').textContent = ''; }, 2000);
        } else { document.getElementById('save-message').textContent = 'Failed to save'; }
    } catch { document.getElementById('save-message').textContent = 'Error saving list'; }
}

async function loadList(listId) {
    try {
        const res = await fetch(`${API_URL}/lists/${listId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) return;
        const list = await res.json();
        basket = [];

        for (const item of list.items) {
            const matchRes = await fetch(`${API_URL}/match-best?q=${encodeURIComponent(item.item_name)}`);
            const products = await matchRes.json();
            if (products.length) {
                basket.push({
                    name_clean: products[0].name_clean,
                    query: item.item_name,
                    products,
                    quantity: item.quantity,
                    type: 'matched'
                });
            } else {
                basket.push({ name: item.item_name, store: 'unknown', price: 0, quantity: item.quantity, type: 'specific' });
            }
        }

        document.getElementById('list-name').value = list.name;
        renderBasket();
        calculatePrices();
    } catch { console.error('Failed to load list'); }
}

async function deleteList(listId) {
    if (!confirm('Delete this list?')) return;
    try {
        await fetch(`${API_URL}/lists/${listId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        await loadSavedLists();
    } catch { console.error('Failed to delete list'); }
}
