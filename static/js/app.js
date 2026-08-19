// State
let coinsData = [];
let watchlistData = [];

// DOM Elements
const coinsGrid = document.getElementById('coinsGrid');
const watchlistTableBody = document.getElementById('watchlistTableBody');
const dbStatusBadge = document.getElementById('dbStatusBadge');
const dbStatusText = document.getElementById('dbStatusText');
const coinSearchInput = document.getElementById('coinSearchInput');
const refreshCoinsBtn = document.getElementById('refreshCoinsBtn');
const totalCoinsCount = document.getElementById('totalCoinsCount');
const watchlistCount = document.getElementById('watchlistCount');

// Modal Elements
const addModal = document.getElementById('addModal');
const openAddModalBtn = document.getElementById('openAddModalBtn');
const closeAddModalBtn = document.getElementById('closeAddModalBtn');
const cancelAddBtn = document.getElementById('cancelAddBtn');
const addCoinForm = document.getElementById('addCoinForm');

const settingsModal = document.getElementById('settingsModal');
const openSettingsBtn = document.getElementById('openSettingsBtn');
const closeSettingsModalBtn = document.getElementById('closeSettingsModalBtn');
const closeSettingsBtn = document.getElementById('closeSettingsBtn');
const testConnectionBtn = document.getElementById('testConnectionBtn');
const testResultBox = document.getElementById('testResultBox');

// Helpers
function formatCurrency(val) {
    if (val === null || val === undefined || isNaN(val)) return '—';
    if (val < 1) return '$' + Number(val).toFixed(4);
    if (val < 10) return '$' + Number(val).toFixed(2);
    return '$' + Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatLargeNumber(val) {
    if (!val) return '—';
    if (val >= 1e12) return '$' + (val / 1e12).toFixed(2) + ' T';
    if (val >= 1e9) return '$' + (val / 1e9).toFixed(2) + ' B';
    if (val >= 1e6) return '$' + (val / 1e6).toFixed(2) + ' M';
    return '$' + Number(val).toLocaleString();
}

// 1. Fetch Backend & Supabase Status
async function checkSystemStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        if (data.supabase && data.supabase.connected) {
            dbStatusBadge.className = 'status-badge connected';
            dbStatusText.textContent = '🟢 Supabase подключен';
        } else if (data.supabase && data.supabase.configured) {
            dbStatusBadge.className = 'status-badge memory';
            dbStatusText.textContent = '🟡 Supabase (Таблица не найдена)';
        } else {
            dbStatusBadge.className = 'status-badge memory';
            dbStatusText.textContent = '🟡 Локальный режим (Демо данные)';
        }
    } catch (err) {
        dbStatusBadge.className = 'status-badge memory';
        dbStatusText.textContent = '⚪ Автономный режим';
    }
}

// 2. Fetch Live Coins
async function fetchCoins() {
    coinsGrid.innerHTML = '<div class="loading-spinner">Загрузка котировок...</div>';
    try {
        const res = await fetch('/api/coins');
        const result = await res.json();
        coinsData = result.data || [];
        totalCoinsCount.textContent = coinsData.length;
        renderCoins(coinsData);
    } catch (err) {
        coinsGrid.innerHTML = '<p class="text-danger">Не удалось загрузить данные о ценах.</p>';
    }
}

function renderCoins(coins) {
    if (!coins.length) {
        coinsGrid.innerHTML = '<p class="text-muted">Монеты не найдены</p>';
        return;
    }

    coinsGrid.innerHTML = coins.map(coin => {
        const change = coin.price_change_percentage_24h || 0;
        const isUp = change >= 0;
        const badgeClass = isUp ? 'badge-up' : 'badge-down';
        const changeSign = isUp ? '+' : '';
        const changeFormatted = `${changeSign}${change.toFixed(2)}%`;

        return `
            <div class="coin-card" data-symbol="${coin.symbol}">
                <div class="coin-card-header">
                    <div class="coin-identity">
                        <div class="coin-icon">${coin.symbol.slice(0, 3)}</div>
                        <div>
                            <div class="coin-name">${coin.name}</div>
                            <div class="coin-symbol">${coin.symbol}</div>
                        </div>
                    </div>
                    <span class="coin-badge-change ${badgeClass}">${changeFormatted}</span>
                </div>
                <div class="coin-card-body">
                    <div class="coin-price">${formatCurrency(coin.current_price)}</div>
                    <div class="coin-stats-row">
                        <span>24h High: ${formatCurrency(coin.high_24h)}</span>
                        <span>24h Low: ${formatCurrency(coin.low_24h)}</span>
                    </div>
                    <div class="coin-stats-row">
                        <span>Market Cap:</span>
                        <span>${formatLargeNumber(coin.market_cap)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// 3. Fetch Watchlist
async function fetchWatchlist() {
    try {
        const res = await fetch('/api/watchlist');
        const result = await res.json();
        watchlistData = result.data || [];
        watchlistCount.textContent = watchlistData.length;
        renderWatchlist(watchlistData);
    } catch (err) {
        watchlistTableBody.innerHTML = `<tr><td colspan="6" class="text-danger text-center">Ошибка загрузки записей базы</td></tr>`;
    }
}

function renderWatchlist(items) {
    if (!items.length) {
        watchlistTableBody.innerHTML = `<tr><td colspan="6" class="text-muted text-center py-4">Список пуст. Нажмите "+ Добавить монету", чтобы сохранить заметку в Supabase.</td></tr>`;
        return;
    }

    watchlistTableBody.innerHTML = items.map(item => {
        const createdDate = item.created_at ? new Date(item.created_at).toLocaleDateString('ru-RU') : '—';
        return `
            <tr>
                <td><span class="symbol-tag">${item.symbol}</span></td>
                <td><strong>${item.name || item.symbol}</strong></td>
                <td>${item.target_price ? formatCurrency(item.target_price) : '<span class="text-muted">Не указан</span>'}</td>
                <td>${item.notes || '<span class="text-muted">—</span>'}</td>
                <td><small class="text-muted">${createdDate}</small></td>
                <td>
                    <button class="btn-danger-sm" onclick="deleteWatchlistItem('${item.id}')">Удалить</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Delete item
async function deleteWatchlistItem(id) {
    if (!confirm('Удалить эту заметку?')) return;
    try {
        const res = await fetch(`/api/watchlist/${id}`, { method: 'DELETE' });
        if (res.ok) {
            await fetchWatchlist();
        } else {
            alert('Ошибка при удалении');
        }
    } catch (err) {
        alert('Ошибка связи с сервером');
    }
}

// Add item form
addCoinForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const symbol = document.getElementById('coinSymbol').value.trim();
    const name = document.getElementById('coinName').value.trim();
    const target_price = document.getElementById('coinTarget').value;
    const notes = document.getElementById('coinNotes').value.trim();

    try {
        const saveBtn = document.getElementById('saveWatchlistBtn');
        saveBtn.disabled = true;
        saveBtn.textContent = 'Сохранение...';

        const res = await fetch('/api/watchlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, name, target_price, notes })
        });

        if (res.ok) {
            addCoinForm.reset();
            addModal.classList.add('hidden');
            await fetchWatchlist();
        } else {
            const errData = await res.json();
            alert('Ошибка: ' + (errData.error || 'Не удалось сохранить'));
        }
    } catch (err) {
        alert('Ошибка соединения с бэкендом');
    } finally {
        const saveBtn = document.getElementById('saveWatchlistBtn');
        saveBtn.disabled = false;
        saveBtn.textContent = 'Сохранить в базу';
    }
});

// Search Coins
coinSearchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    const filtered = coinsData.filter(c => 
        c.name.toLowerCase().includes(query) || 
        c.symbol.toLowerCase().includes(query)
    );
    renderCoins(filtered);
});

// Refresh button
refreshCoinsBtn.addEventListener('click', () => {
    fetchCoins();
});

// Modals event listeners
openAddModalBtn.addEventListener('click', () => addModal.classList.remove('hidden'));
closeAddModalBtn.addEventListener('click', () => addModal.classList.add('hidden'));
cancelAddBtn.addEventListener('click', () => addModal.classList.add('hidden'));

openSettingsBtn.addEventListener('click', () => settingsModal.classList.remove('hidden'));
closeSettingsModalBtn.addEventListener('click', () => settingsModal.classList.add('hidden'));
closeSettingsBtn.addEventListener('click', () => settingsModal.classList.add('hidden'));

// Supabase credential live tester
testConnectionBtn.addEventListener('click', async () => {
    const url = document.getElementById('testSupabaseUrl').value.trim();
    const key = document.getElementById('testSupabaseKey').value.trim();

    testResultBox.className = 'test-result';
    testResultBox.classList.remove('hidden');
    testResultBox.textContent = 'Проверка соединения с базой...';

    try {
        const res = await fetch('/api/test-supabase', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, key })
        });
        const result = await res.json();

        if (result.success) {
            testResultBox.className = 'test-result success';
            testResultBox.textContent = '✅ ' + result.message;
        } else {
            testResultBox.className = 'test-result error';
            testResultBox.textContent = '❌ ' + result.message;
        }
    } catch (err) {
        testResultBox.className = 'test-result error';
        testResultBox.textContent = '❌ Ошибка при отправке запроса тестирования';
    }
});

// Initial boot
document.addEventListener('DOMContentLoaded', () => {
    checkSystemStatus();
    fetchCoins();
    fetchWatchlist();
});
