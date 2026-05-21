// API Configuration - Change this to your Railway backend URL
const API_URL = 'https://grocery-compare-production-394e.up.railway.app';

// State
let token = localStorage.getItem('token');
let basket = [];

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    if (token) {
        showMainApp();
    }
});

// Auth Functions
async function register() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            token = data.access_token;
            localStorage.setItem('token', token);
            showMainApp();
        } else {
            showAuthError(data.detail || 'Registration failed');
        }
    } catch (error) {
        showAuthError('Connection error. Is the backend running?');
    }
}

async function login() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            token = data.access_token;
            localStorage.setItem('token', token);
            showMainApp();
        } else {
            showAuthError(data.detail || 'Login failed');
        }
    } catch (error) {
        showAuthError('Connection error. Is the backend running?');
    }
}

function logout() {
    token = null;
    localStorage.removeItem('token');
    basket = [];
    document.getElementById('login-section').style.display = 'flex';
    document.getElementById('main-section').style.display = 'none';
}

function showAuthError(message) {
    document.getElementById('auth-message').textContent = message;
}

// Main App
async function showMainApp() {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('main-section').style.display = 'block';

    // Get user info
    try {
        const response = await fetch(`${API_URL}/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const user = await response.json();
            document.getElementById('user-email').textContent = user.email;
        } else {
            logout();
            return;
        }
    } catch (error) {
        logout();
        return;
    }

    await loadSavedLists();
}

// ── Smart Match (ML-powered) ──────────────────────────────────────────────────
async function smartMatch() {
    const query = document.getElementById('search-input').value.trim();
    if (!query) return;

    const resultsDiv = document.getElementById('search-results');
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = '<p>Matching...</p>';

    try {
        const response = await fetch(`${API_URL}/match?q=${encodeURIComponent(query)}&top_k=20`);
        const results = await response.json();

        if (results.length === 0) {
            resultsDiv.innerHTML = '<p>No matches found. Try "Search" for a manual lookup.</p>';
            return;
        }

        // Group confident matches by name_clean (same product across stores)
        const confidentMatches = results.filter(r => r.confident);
        const grouped = {};
        confidentMatches.forEach(r => {
            if (!grouped[r.name_clean]) grouped[r.name_clean] = [];
            grouped[r.name_clean].push(r);
        });

        let html = '';
        for (const [cleanName, products] of Object.entries(grouped)) {
            products.sort((a, b) => a.price - b.price);

            html += `<div class="match-group">`;
            html += `<h4>${cleanName}</h4>`;
            html += `<table class="match-table"><tbody>`;
            products.forEach((p, i) => {
                const highlight = i === 0 ? ' class="cheapest"' : '';
                html += `<tr${highlight}>`;
                html += `<td>${p.store}</td>`;
                html += `<td>£${p.price.toFixed(2)}</td>`;
                html += `<td>${p.name}</td>`;
                html += `</tr>`;
            });
            html += `</tbody></table>`;
            html += `<button class="btn btn-small btn-primary" onclick='addMatchToBasket(${JSON.stringify(cleanName)}, ${JSON.stringify(products)})'>Add to basket</button>`;
            html += `</div>`;
        }

        // Show non-confident results as suggestions when there are no confident matches
        const uncertain = results.filter(r => !r.confident);
        if (uncertain.length > 0 && confidentMatches.length === 0) {
            html += `<p>No confident matches. These might be related:</p>`;
            uncertain.forEach(r => {
                html += `<div class="search-result-item" onclick='addSpecificToBasket(${JSON.stringify(r)})'>`;
                html += `<span>${r.name} (${r.store}) — £${r.price.toFixed(2)}</span>`;
                html += `<span class="similarity">Similarity: ${(r.similarity * 100).toFixed(0)}%</span>`;
                html += `</div>`;
            });
        }

        resultsDiv.innerHTML = html || '<p>No confident matches. Try "Search" for manual lookup.</p>';
    } catch (error) {
        resultsDiv.innerHTML = '<p>Error connecting to server.</p>';
    }
}

// ── Manual Search (text fallback) ─────────────────────────────────────────────
async function manualSearch() {
    const query = document.getElementById('search-input').value.trim();
    if (!query) return;

    const resultsDiv = document.getElementById('search-results');
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = '<p>Searching...</p>';

    try {
        const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}&top_k=30`);
        const results = await response.json();

        if (results.length === 0) {
            resultsDiv.innerHTML = '<p>No products found.</p>';
            return;
        }

        let html = '<div class="search-list">';
        results.forEach(r => {
            html += `<div class="search-result-item" onclick='addSpecificToBasket(${JSON.stringify(r)})'>`;
            html += `<span class="result-name">${r.name}</span>`;
            html += `<span class="result-meta">${r.store} — £${r.price.toFixed(2)}</span>`;
            html += `</div>`;
        });
        html += '</div>';
        resultsDiv.innerHTML = html;
    } catch (error) {
        resultsDiv.innerHTML = '<p>Error connecting to server.</p>';
    }
}

// ── Add to basket ─────────────────────────────────────────────────────────────
function addMatchToBasket(cleanName, products) {
    const quantity = parseInt(document.getElementById('quantity').value) || 1;

    const existing = basket.find(b => b.name_clean === cleanName);
    if (existing) {
        existing.quantity += quantity;
    } else {
        basket.push({
            name_clean: cleanName,
            products: products,
            quantity: quantity,
            type: 'matched'
        });
    }

    document.getElementById('search-input').value = '';
    document.getElementById('quantity').value = 1;
    document.getElementById('search-results').style.display = 'none';
    renderBasket();
    calculatePrices();
}

function addSpecificToBasket(product) {
    const quantity = parseInt(document.getElementById('quantity').value) || 1;

    basket.push({
        name: product.name,
        store: product.store,
        price: product.price,
        quantity: quantity,
        type: 'specific'
    });

    document.getElementById('search-input').value = '';
    document.getElementById('quantity').value = 1;
    document.getElementById('search-results').style.display = 'none';
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
    tbody.innerHTML = '';

    basket.forEach((item, index) => {
        const row = document.createElement('tr');
        if (item.type === 'matched') {
            row.innerHTML = `
                <td>${item.name_clean} <span class="badge">matched</span></td>
                <td>${item.quantity}</td>
                <td><button class="remove-btn" onclick="removeFromBasket(${index})">×</button></td>
            `;
        } else {
            row.innerHTML = `
                <td>${item.name} <span class="badge-store">${item.store}</span></td>
                <td>${item.quantity}</td>
                <td><button class="remove-btn" onclick="removeFromBasket(${index})">×</button></td>
            `;
        }
        tbody.appendChild(row);
    });
}

// ── Price Calculation ─────────────────────────────────────────────────────────
function calculatePrices() {
    if (basket.length === 0) {
        document.getElementById('recommendations-body').innerHTML = '';
        document.getElementById('totals-body').innerHTML = '';
        document.getElementById('savings-text').textContent = '';
        return;
    }

    const recommendations = [];
    const storeTotals = {};

    basket.forEach(item => {
        if (item.type === 'matched') {
            const cheapest = item.products.reduce((min, p) => p.price < min.price ? p : min);
            recommendations.push({
                item: item.name_clean,
                store: cheapest.store,
                price: cheapest.price * item.quantity
            });

            item.products.forEach(p => {
                if (!storeTotals[p.store]) storeTotals[p.store] = 0;
                storeTotals[p.store] += p.price * item.quantity;
            });
        } else {
            recommendations.push({
                item: item.name,
                store: item.store,
                price: item.price * item.quantity
            });

            if (!storeTotals[item.store]) storeTotals[item.store] = 0;
            storeTotals[item.store] += item.price * item.quantity;
        }
    });

    // Render recommendations table
    const recBody = document.getElementById('recommendations-body');
    recBody.innerHTML = '';
    recommendations.forEach(rec => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${rec.item}</td>
            <td>${rec.store}</td>
            <td>£${rec.price.toFixed(2)}</td>
        `;
        recBody.appendChild(row);
    });

    // Render store totals
    const totalsBody = document.getElementById('totals-body');
    totalsBody.innerHTML = '';

    const sortedStores = Object.entries(storeTotals).sort((a, b) => a[1] - b[1]);
    if (sortedStores.length === 0) return;

    const cheapestTotal = sortedStores[0][1];
    const mostExpensive = sortedStores[sortedStores.length - 1][1];

    sortedStores.forEach(([store, total], index) => {
        const row = document.createElement('tr');
        if (index === 0) row.className = 'cheapest';
        row.innerHTML = `
            <td>${store}${index === 0 ? ' ✓' : ''}</td>
            <td>£${total.toFixed(2)}</td>
        `;
        totalsBody.appendChild(row);
    });

    const savings = mostExpensive - cheapestTotal;
    if (savings > 0) {
        document.getElementById('savings-text').textContent =
            `You could save £${savings.toFixed(2)} by shopping at ${sortedStores[0][0]}!`;
    } else {
        document.getElementById('savings-text').textContent = '';
    }
}

// Saved Lists
async function loadSavedLists() {
    try {
        const response = await fetch(`${API_URL}/lists`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const lists = await response.json();
            renderSavedLists(lists);
        }
    } catch (error) {
        console.error('Failed to load lists:', error);
    }
}

function renderSavedLists(lists) {
    const container = document.getElementById('saved-lists');
    container.innerHTML = '';

    if (lists.length === 0) {
        container.innerHTML = '<p style="color: #7f8c8d;">No saved lists yet</p>';
        return;
    }

    lists.forEach(list => {
        const div = document.createElement('div');
        div.className = 'saved-list-item';
        div.innerHTML = `
            <span>${list.name} (${list.items.length} items)</span>
            <div class="saved-list-actions">
                <button class="btn btn-small btn-primary" onclick="loadList(${list.id})">Load</button>
                <button class="btn btn-small btn-danger" onclick="deleteList(${list.id})">Delete</button>
            </div>
        `;
        container.appendChild(div);
    });
}

async function saveList() {
    const name = document.getElementById('list-name').value || 'My Shopping List';

    if (basket.length === 0) {
        document.getElementById('save-message').textContent = 'Basket is empty!';
        return;
    }

    const items = basket.map(b => ({
        item_name: b.type === 'matched' ? b.name_clean : b.name,
        quantity: b.quantity
    }));

    try {
        const response = await fetch(`${API_URL}/lists`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ name, items })
        });

        if (response.ok) {
            document.getElementById('save-message').textContent = 'List saved!';
            document.getElementById('list-name').value = '';
            await loadSavedLists();
            setTimeout(() => {
                document.getElementById('save-message').textContent = '';
            }, 2000);
        } else {
            document.getElementById('save-message').textContent = 'Failed to save list';
        }
    } catch (error) {
        document.getElementById('save-message').textContent = 'Error saving list';
    }
}

async function loadList(listId) {
    try {
        const response = await fetch(`${API_URL}/lists/${listId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const list = await response.json();
            basket = [];

            // Re-match each saved item to get current prices
            for (const item of list.items) {
                const matchResponse = await fetch(
                    `${API_URL}/match?q=${encodeURIComponent(item.item_name)}&top_k=10`
                );
                const matches = await matchResponse.json();
                const confident = matches.filter(m => m.confident);

                if (confident.length > 0) {
                    const grouped = {};
                    confident.forEach(r => {
                        if (!grouped[r.name_clean]) grouped[r.name_clean] = [];
                        grouped[r.name_clean].push(r);
                    });
                    const bestGroup = Object.entries(grouped)[0];
                    basket.push({
                        name_clean: bestGroup[0],
                        products: bestGroup[1],
                        quantity: item.quantity,
                        type: 'matched'
                    });
                } else {
                    basket.push({
                        name: item.item_name,
                        store: 'unknown',
                        price: 0,
                        quantity: item.quantity,
                        type: 'specific'
                    });
                }
            }

            document.getElementById('list-name').value = list.name;
            renderBasket();
            calculatePrices();
        }
    } catch (error) {
        console.error('Failed to load list:', error);
    }
}

async function deleteList(listId) {
    if (!confirm('Delete this list?')) return;

    try {
        const response = await fetch(`${API_URL}/lists/${listId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            await loadSavedLists();
        }
    } catch (error) {
        console.error('Failed to delete list:', error);
    }
}