-- =========================================================
-- Supabase Schema for Coin Tracker (Участники, Переводы, Курс)
-- =========================================================

-- 1. Таблица конфигурации монеты
CREATE TABLE IF NOT EXISTS public.coin_config (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'main',
    name VARCHAR(100) NOT NULL DEFAULT 'Дискойн',
    symbol VARCHAR(20) NOT NULL DEFAULT '🪙',
    value NUMERIC NOT NULL DEFAULT 12.5,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Таблица участников и их балансов
CREATE TABLE IF NOT EXISTS public.accounts (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    telegram_id BIGINT,
    username VARCHAR(255),
    balance NUMERIC NOT NULL DEFAULT 100.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Таблица истории всех транзакций
CREATE TABLE IF NOT EXISTS public.transactions (
    id VARCHAR(100) PRIMARY KEY,
    from_id VARCHAR(100) NOT NULL,
    from_name VARCHAR(255) NOT NULL,
    to_id VARCHAR(100) NOT NULL,
    to_name VARCHAR(255) NOT NULL,
    amount NUMERIC NOT NULL,
    timestamp BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Открываем RLS политики для публичного доступа
ALTER TABLE public.coin_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public all coin_config" ON public.coin_config FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public all accounts" ON public.accounts FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public all transactions" ON public.transactions FOR ALL USING (true) WITH CHECK (true);

-- Начальные данные
INSERT INTO public.coin_config (id, name, symbol, value)
VALUES ('main', 'Дискойн', '🪙', 12.5)
ON CONFLICT (id) DO NOTHING;
