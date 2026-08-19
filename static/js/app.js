// Global State
let coinsData = [];
let watchlistData = [];
let currentUser = null;

// Telegram WebApp Instance
const tg = window.Telegram?.WebApp;

// DOM Elements
const userAvatar = document.getElementById('userAvatar');
const userFullName = document.getElementById('userFullName');
const userUsername = document.getElementById('userUsername');
const userId = document.getElementById('userId');
const userLanguage = document.getElementById('userLanguage');
const userPremiumBadge = document.getElementById('userPremiumBadge');
const tgPlatformBadge = document.getElementById('tgPlatformBadge');
const authStatusText = document.getElementById('authStatusText');

const coinsGrid = document.getElementById('coinsGrid');
const watchlistTableBody = document.getElementById('watchlistTableBody');
const dbStatusBadge = document.getElementById('dbStatusBadge');
const dbStatusText = document.getElementById('dbStatusText');
const coinSearchInput = document.getElementById('coinSearchInput');
const refreshCoinsBtn = document.getElementById('refreshCoinsBtn');

// Modals
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
const setMenuButtonBtn = document.getElementById('setMenuButtonBtn');

// 1. Initialize Telegram WebApp & Load User Profile
async function initTelegramProfile() {
    if (tg) {
        try {
            tg.ready();
            tg.expand();
            
            // Set header color to match dark aesthetic
            if (tg.setHeaderColor) {
                tg.setHeaderColor('#0b0f19');
            }
            if (tg.setBackgroundColor) {
                tg.setBackgroundColor('#0b0f19');
            }
        } catch (e) {
            console.log('TG WebApp styling initialization note:', e);
        }
    }

    const tgUser = tg?.initDataUnsafe?.user;
    const initData = tg?.initData || '';
    const platform = tg?.platform || 'browser';

    tgPlatformBadge.textContent = platform;

    if (tgUser && tgUser.id) {
        // Authenticated through real Telegram Mini App
        currentUser = tgUser;
        renderUserProfile(tgUser, true);

        // Send to backend for cryptographic HMAC verification & Supabase sync
        try {
            const res = await fetch('/api/telegram/auth', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ initData, user: tgUser })
            });
            const data = await res.json();
            if (data.verified) {
                authStatusText.textContent = '🟢 Подтвержден (Telegram HMAC)';
            } else {
                authStatusText.textContent = '🟢 Авторизован (Telegram ID)';
            }
        } catch (err) {
            console.warn('Backend sync note:', err);
        }
    } else {
        // Opened in regular web browser (Simulated Profile Mode)
        const mockUser = {
            id: 8514899291,
            first_name: "Пользователь",
            last_name: "Telegram",
            username: "telegram_user",
            language_code: "ru",
            is_premium: true
        };
        currentUser = mockUser;
        renderUserProfile(mockUser, false);
        authStatusText.textContent = '🟡 Веб-режим (Демо профиль)';
        tgPlatformBadge.textContent = 'Web Browser';
    }
}

function renderUserProfile(user, isLive) {
    const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim() || 'Telegram User';
    userFullName.textContent = fullName;
    
    if (user.username) {
        userUsername.textContent = `@${user.username}`;
    } else {
        userUsername.textContent = 'Без @юзернейма';
    }

    userId.textContent = user.id || '—';

    // Language display
    const langMap = {
        'ru': 'Русский (ru)',
        'en': 'English (en)',
        'uk': 'Українська (uk)',
        'uz': 'O‘zbek (uz)',
        'kz': 'Қазақ (kz)'
    };
    userLanguage.textContent = langMap[user.language_code] || user.language_code || 'ru';

    // Premium Badge
    if (user.is_premium) {
        userPremiumBadge.classList.remove('hidden');
    } else {
        userPremiumBadge.classList.add('hidden');
    }

    // Avatar display (Photo or Initials)
    if (user.photo_url) {
        userAvatar.style.backgroundImage = `url('${user.photo_url}')`;
        userAvatar.textContent = '';
    } else {
        userAvatar.style.backgroundImage = 'none';
        const initials = ((user.first_name?.[0] || '') + (user.last_name?.[0] || user.first_name?.[1] || '')).toUpperCase() || 'TG';
        userAvatar.textContent = initials;
    }
}

// Copy User ID with Haptic Feedback
userId.addEventListener('click', () => {
    const text = userId.textContent;
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text);
    }
    if (tg?.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred('success');
    }
    const original = userId.textContent;
    userId.textContent = 'Скопировано! ✅';
    setTimeout(() => { userId.textContent = original; }, 1500);
});

// Formatters
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

// 2. Fetch Backend & Supabase Status
async function checkSystemStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        if (data.supabase && data.supabase.connected) {
            dbStatusBadge.className = 'status-badge connected';
            dbStatusText.textContent = '🟢 Supabase активен';
        } else if (data.supabase && data.supabase.configured) {
            dbStatusBadge.className = 'status-badge memory';
            dbStatusText.textContent = '🟡 Supabase подключен';
        } else {
            dbStatusBadge.className = 'status-badge memory';
            dbStatusText.textContent = '🟡 Локальный режим';
        }
    } catch (err) {
        dbStatusBadge.className = 'status-badge memory';
        dbStatusText.textContent = '⚪ Автономный режим';
    }
}

// 3. Fetch Live Coins
async function fetchCoins() {
    coinsGrid.innerHTML = '<div class="loading-spinner">Загрузка котировок...</div>';
    try {
        const res = await fetch('/api/coins');
        const result = await res.json();
        coinsData = result.data || [];
        renderCoins(coinsData);
    } catch (err) {
        coinsGrid.innerHTML = '<p class="text-danger">Не удалось загрузить данные котировок.</p>';
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
            <div class="coin-card">
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
                </div>
            </div>
        `;
    }).join('');
}

// 4. Watchlist
async function fetchWatchlist() {
    try {
        const res = await fetch('/api/watchlist');
        const result = await res.json();
        watchlistData = result.data || [];
        renderWatchlist(watchlistData);
    } catch (err) {
        watchlistTableBody.innerHTML = `<tr><td colspan="5" class="text-danger text-center">Ошибка загрузки записей</td></tr>`;
    }
}

function renderWatchlist(items) {
    if (!items.length) {
        watchlistTableBody.innerHTML = `<tr><td colspan="5" class="text-muted text-center py-3">Список пуст. Добавьте монету в базу.</td></tr>`;
        return;
    }

    watchlistTableBody.innerHTML = items.map(item => {
        return `
            <tr>
                <td><span class="symbol-tag">${item.symbol}</span></td>
                <td><strong>${item.name || item.symbol}</strong></td>
                <td>${item.target_price ? formatCurrency(item.target_price) : '<span class="text-muted">—</span>'}</td>
                <td>${item.notes || '<span class="text-muted">—</span>'}</td>
                <td>
                    <button class="btn-danger-sm" onclick="deleteWatchlistItem('${item.id}')">✕</button>
                </td>
            </tr>
        `;
    }).join('');
}

async function deleteWatchlistItem(id) {
    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
    if (!confirm('Удалить запись из Supabase?')) return;
    try {
        const res = await fetch(`/api/watchlist/${id}`, { method: 'DELETE' });
        if (res.ok) {
            await fetchWatchlist();
        }
    } catch (err) {
        alert('Ошибка при удалении');
    }
}

// Add item form
addCoinForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');

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
            if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
            addCoinForm.reset();
            addModal.classList.add('hidden');
            await fetchWatchlist();
        } else {
            const errData = await res.json();
            alert('Ошибка: ' + (errData.error || 'Не удалось сохранить'));
        }
    } catch (err) {
        alert('Ошибка соединения');
    } finally {
        const saveBtn = document.getElementById('saveWatchlistBtn');
        saveBtn.disabled = false;
        saveBtn.textContent = 'Сохранить';
    }
});

// Set Menu Button in Bot
setMenuButtonBtn.addEventListener('click', async () => {
    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
    setMenuButtonBtn.textContent = 'Настройка...';
    try {
        const currentUrl = window.location.origin;
        const res = await fetch('/api/telegram/set-menu', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: currentUrl })
        });
        const result = await res.json();
        if (result.ok) {
            alert('✅ Кнопка меню успешно установлена в боте @fanat_mavro_robot!');
        } else {
            alert('Ответ: ' + (result.description || JSON.stringify(result)));
        }
    } catch (err) {
        alert('Ошибка при запросе к Telegram Bot API');
    } finally {
        setMenuButtonBtn.textContent = '📌 Прикрепить кнопку меню в бота';
    }
});

// Search
coinSearchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    const filtered = coinsData.filter(c => 
        c.name.toLowerCase().includes(query) || 
        c.symbol.toLowerCase().includes(query)
    );
    renderCoins(filtered);
});

refreshCoinsBtn.addEventListener('click', () => {
    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
    fetchCoins();
});

// Modals
openAddModalBtn.addEventListener('click', () => addModal.classList.remove('hidden'));
closeAddModalBtn.addEventListener('click', () => addModal.classList.add('hidden'));
cancelAddBtn.addEventListener('click', () => addModal.classList.add('hidden'));

openSettingsBtn.addEventListener('click', () => settingsModal.classList.remove('hidden'));
closeSettingsModalBtn.addEventListener('click', () => settingsModal.classList.add('hidden'));
closeSettingsBtn.addEventListener('click', () => settingsModal.classList.add('hidden'));

testConnectionBtn.addEventListener('click', async () => {
    const url = document.getElementById('testSupabaseUrl').value.trim();
    const key = document.getElementById('testSupabaseKey').value.trim();

    testResultBox.className = 'test-result';
    testResultBox.classList.remove('hidden');
    testResultBox.textContent = 'Проверка...';

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
        testResultBox.textContent = '❌ Ошибка запроса';
    }
});

// Init
document.addEventListener('DOMContentLoaded', () => {
    initTelegramProfile();
    checkSystemStatus();
    fetchCoins();
    fetchWatchlist();
});
