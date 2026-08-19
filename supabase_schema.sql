-- =========================================================
-- Supabase Schema for Coin App (Watchlist & Portfolio Notes)
-- =========================================================
-- Выполните этот SQL скрипт в панели Supabase:
-- Project Dashboard -> SQL Editor -> New Query -> Run

CREATE TABLE IF NOT EXISTS public.watchlist (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    target_price NUMERIC,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Открываем политику чтения и записи (RLS) для публичного демо:
ALTER TABLE public.watchlist ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access" 
ON public.watchlist 
FOR SELECT 
USING (true);

CREATE POLICY "Allow public insert access" 
ON public.watchlist 
FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Allow public delete access" 
ON public.watchlist 
FOR DELETE 
USING (true);

-- Начальные тестовые данные (по желанию):
INSERT INTO public.watchlist (symbol, name, target_price, notes)
VALUES 
    ('BTC', 'Bitcoin', 120000.00, 'HODL! Сильный уровень поддержки'),
    ('ETH', 'Ethereum', 4500.00, 'Стейкинг и DeFi экосистема'),
    ('SOL', 'Solana', 300.00, 'Быстрый рост транзакций и экосистемы'),
    ('TON', 'Toncoin', 10.00, 'Интеграция с Telegram')
ON CONFLICT DO NOTHING;
