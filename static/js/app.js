// ---------- storage helpers & state ----------
const MY_ID_KEY = "my-profile-id";

let state = {
    loading: true,
    error: "",
    coin: { name: "Дискойн", symbol: "🪙", value: 12.5 },
    accounts: [],
    txs: [],
    myId: localStorage.getItem(MY_ID_KEY) || null,
    editingValue: false
};

// Telegram WebApp SDK
const tg = window.Telegram?.WebApp;

// DOM Elements
const loadingScreen = document.getElementById('loadingScreen');
const loginScreen = document.getElementById('loginScreen');
const mainScreen = document.getElementById('mainScreen');

// Login Screen Elements
const loginTag = document.getElementById('loginTag');
const loginCoinName = document.getElementById('loginCoinName');
const nameInput = document.getElementById('nameInput');
const createProfileBtn = document.getElementById('createProfileBtn');
const existingAccHint = document.getElementById('existingAccHint');

// Header Coin Elements
const coinTitleDisplay = document.getElementById('coinTitleDisplay');
const coinSymbolText = document.getElementById('coinSymbolText');
const coinRateText = document.getElementById('coinRateText');
const coinValueDisplay = document.getElementById('coinValueDisplay');
const editValueForm = document.getElementById('editValueForm');
const valueInput = document.getElementById('valueInput');
const cancelEditValueBtn = document.getElementById('cancelEditValueBtn');

// Profile & Transfer Elements
const profileNameDisplay = document.getElementById('profileNameDisplay');
const profileBalanceDisplay = document.getElementById('profileBalanceDisplay');
const switchProfileBtn = document.getElementById('switchProfileBtn');
const transferForm = document.getElementById('transferForm');
const toIdSelect = document.getElementById('toIdSelect');
const transferAmountInput = document.getElementById('transferAmountInput');
const txErrorMsg = document.getElementById('txErrorMsg');
const txOkMsg = document.getElementById('txOkMsg');

// Lists
const accountsCountTag = document.getElementById('accountsCountTag');
const accountsList = document.getElementById('accountsList');
const txCountTag = document.getElementById('txCountTag');
const txEmptyMsg = document.getElementById('txEmptyMsg');
const txList = document.getElementById('txList');
const globalErrorBar = document.getElementById('globalErrorBar');

// Helpers
function fmt(n) {
    return Number(n || 0).toLocaleString("ru-RU", { maximumFractionDigits: 4 });
}

function fmtTime(ts) {
    const d = new Date(Number(ts));
    return d.toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

// ---------- API Integration ----------
async function loadData() {
    try {
        state.error = "";
        const res = await fetch('/api/data');
        const data = await res.json();
        
        if (data.coin) state.coin = data.coin;
        if (data.accounts) state.accounts = data.accounts;
        if (data.transactions) state.txs = data.transactions;
    } catch (e) {
        state.error = "Не удалось загрузить данные. Попробуйте обновить.";
    } finally {
        state.loading = false;
        render();
    }
}

// Telegram auto-login
async function checkTelegramAuth() {
    if (tg) {
        try {
            tg.ready();
            tg.expand();
            if (tg.setHeaderColor) tg.setHeaderColor('#F7F3EA');
            if (tg.setBackgroundColor) tg.setBackgroundColor('#F7F3EA');
        } catch (e) {}

        const tgUser = tg.initDataUnsafe?.user;
        if (tgUser && tgUser.id) {
            try {
                const res = await fetch('/api/profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tg_user: tgUser,
                        initData: tg.initData || ''
                    })
                });
                const data = await res.json();
                if (data.account) {
                    state.myId = data.account.id;
                    localStorage.setItem(MY_ID_KEY, data.account.id);
                }
            } catch (err) {
                console.error("TG login error:", err);
            }
        }
    }
}

// Create or Switch Profile
async function createProfile() {
    const name = nameInput.value.trim();
    if (!name) return;

    try {
        const res = await fetch('/api/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (data.account) {
            state.myId = data.account.id;
            localStorage.setItem(MY_ID_KEY, data.account.id);
            await loadData();
        } else if (data.error) {
            alert(data.error);
        }
    } catch (err) {
        alert("Ошибка при входе");
    }
}

function switchProfile() {
    state.myId = null;
    localStorage.removeItem(MY_ID_KEY);
    nameInput.value = "";
    render();
}

// Edit Coin Value
function startEditValue() {
    valueInput.value = String(state.coin.value);
    state.editingValue = true;
    editValueForm.classList.remove('hidden');
    coinValueDisplay.classList.add('hidden');
    valueInput.focus();
}

function cancelEditValue() {
    state.editingValue = false;
    editValueForm.classList.add('hidden');
    coinValueDisplay.classList.remove('hidden');
}

async function submitValue(e) {
    e.preventDefault();
    const v = parseFloat(valueInput.value);
    if (!v || v <= 0) return;

    try {
        const res = await fetch('/api/coin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ value: v })
        });
        const data = await res.json();
        if (data.coin) {
            state.coin = data.coin;
        }
        cancelEditValue();
        render();
    } catch (err) {
        alert("Не удалось сохранить курс");
    }
}

// Transfer Coins
async function submitTransfer(e) {
    e.preventDefault();
    txErrorMsg.classList.add('hidden');
    txOkMsg.classList.add('hidden');
    txErrorMsg.textContent = "";
    txOkMsg.textContent = "";

    const toId = toIdSelect.value;
    const amount = transferAmountInput.value.trim();
    const amt = parseFloat(amount);
    const me = state.accounts.find(a => a.id === state.myId);

    if (!toId) {
        txErrorMsg.textContent = "Выберите получателя.";
        txErrorMsg.classList.remove('hidden');
        return;
    }
    if (toId === state.myId) {
        txErrorMsg.textContent = "Нельзя перевести самому себе.";
        txErrorMsg.classList.remove('hidden');
        return;
    }
    if (!amt || amt <= 0) {
        txErrorMsg.textContent = "Введите корректную сумму.";
        txErrorMsg.classList.remove('hidden');
        return;
    }
    if (!me || amt > me.balance) {
        txErrorMsg.textContent = "Недостаточно монет на балансе.";
        txErrorMsg.classList.remove('hidden');
        return;
    }

    try {
        const submitBtn = document.getElementById('submitTransferBtn');
        submitBtn.disabled = true;

        const res = await fetch('/api/transfer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                from_id: state.myId,
                to_id: toId,
                amount: amt
            })
        });

        const data = await res.json();

        if (res.ok && data.status === "success") {
            const recipient = state.accounts.find(a => a.id === toId);
            transferAmountInput.value = "";
            toIdSelect.value = "";
            txOkMsg.textContent = `Переведено ${fmt(amt)} ${state.coin.symbol} → ${recipient ? recipient.name : ""}`;
            txOkMsg.classList.remove('hidden');
            
            if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
            await loadData();
        } else {
            txErrorMsg.textContent = data.error || "Ошибка при переводе.";
            txErrorMsg.classList.remove('hidden');
        }
    } catch (err) {
        txErrorMsg.textContent = "Ошибка соединения.";
        txErrorMsg.classList.remove('hidden');
    } finally {
        document.getElementById('submitTransferBtn').disabled = false;
    }
}

// ---------- Render UI ----------
function render() {
    if (state.loading) {
        loadingScreen.classList.remove('hidden');
        loginScreen.classList.add('hidden');
        mainScreen.classList.add('hidden');
        return;
    }

    loadingScreen.classList.add('hidden');
    const me = state.accounts.find(a => a.id === state.myId);

    // Profile Setup Screen
    if (!me) {
        loginScreen.classList.remove('hidden');
        mainScreen.classList.add('hidden');

        loginTag.textContent = `${state.coin.symbol} ПРОФИЛЬ УЧАСТНИКА`;
        loginCoinName.textContent = state.coin.name;

        if (state.accounts.length > 0) {
            existingAccHint.textContent = `Уже есть ${state.accounts.length} участник(ов). Введите существующее имя, чтобы вернуться к своему профилю.`;
        } else {
            existingAccHint.textContent = "";
        }
        return;
    }

    // Main App Screen
    loginScreen.classList.add('hidden');
    mainScreen.classList.remove('hidden');

    // 1. Header Coin Rate
    coinTitleDisplay.textContent = `${state.coin.symbol} ${state.coin.name}`;
    coinSymbolText.textContent = state.coin.symbol;
    coinRateText.textContent = fmt(state.coin.value);

    // 2. Profile
    profileNameDisplay.textContent = me.name;
    profileBalanceDisplay.textContent = `${fmt(me.balance)} ${state.coin.symbol}`;

    // Transfer Select options
    const otherAccounts = state.accounts.filter(a => a.id !== state.myId);
    toIdSelect.innerHTML = `<option value="">Получатель…</option>` + 
        otherAccounts.map(a => `<option value="${a.id}">${a.name} (${fmt(a.balance)} ${state.coin.symbol})</option>`).join('');

    transferAmountInput.placeholder = `Сумма в ${state.coin.symbol}`;

    // 3. Accounts List (Sorted by balance desc)
    const sortedAccounts = [...state.accounts].sort((a, b) => b.balance - a.balance);
    accountsCountTag.textContent = `УЧАСТНИКИ: ${state.accounts.length}`;

    accountsList.innerHTML = sortedAccounts.map(a => `
        <div class="account-row ${a.id === state.myId ? 'is-me' : ''}">
            <span>${a.name}${a.id === state.myId ? ' (вы)' : ''}</span>
            <span>${fmt(a.balance)} ${state.coin.symbol}</span>
        </div>
    `).join('');

    // 4. Transaction List
    const recentTxs = state.txs.slice(0, 25);
    txCountTag.textContent = `ТРАНЗАКЦИИ: ${state.txs.length}`;

    if (recentTxs.length === 0) {
        txEmptyMsg.classList.remove('hidden');
        txList.innerHTML = "";
    } else {
        txEmptyMsg.classList.add('hidden');
        txList.innerHTML = recentTxs.map(t => `
            <div class="tx-row">
                <span>${t.fromName} → ${t.toName}</span>
                <span class="tx-meta">${fmt(t.amount)} ${state.coin.symbol} · ${fmtTime(t.timestamp)}</span>
            </div>
        `).join('');
    }

    // Global Error
    if (state.error) {
        globalErrorBar.textContent = state.error;
        globalErrorBar.classList.remove('hidden');
    } else {
        globalErrorBar.classList.add('hidden');
    }
}

// ---------- Event Listeners ----------
createProfileBtn.addEventListener('click', createProfile);
nameInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') createProfile();
});

switchProfileBtn.addEventListener('click', switchProfile);

coinValueDisplay.addEventListener('click', startEditValue);
cancelEditValueBtn.addEventListener('click', cancelEditValue);
editValueForm.addEventListener('submit', submitValue);

transferForm.addEventListener('submit', submitTransfer);

// Init
document.addEventListener('DOMContentLoaded', async () => {
    await checkTelegramAuth();
    await loadData();
});
