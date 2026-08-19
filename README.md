# 🪙 COIN HUB — Crypto Platform with Supabase & Render

Полнофункциональное веб-приложение для мониторинга криптовалют, аналитики и сохранения персональных заметок/таргетов в облачную базу данных **Supabase** (PostgreSQL) с автоматическим деплоем на **Render**.

---

## 🚀 Быстрый старт локально

```bash
# 1. Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Скопировать и настроить переменные окружения (опционально)
cp .env.example .env

# 4. Запустить локальный сервер
python app.py
```
Откройте [http://localhost:5000](http://localhost:5000) в браузере.

---

## ☁️ Настройка Supabase (База данных)

1. Перейдите на [Supabase Dashboard](https://supabase.com/dashboard) и создайте проект.
2. Откройте **SQL Editor** в левом меню, нажмите **New Query** и выполните код из файла [`supabase_schema.sql`](supabase_schema.sql):
```sql
CREATE TABLE IF NOT EXISTS public.watchlist (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    target_price NUMERIC,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.watchlist ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access" ON public.watchlist FOR SELECT USING (true);
CREATE POLICY "Allow public insert access" ON public.watchlist FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public delete access" ON public.watchlist FOR DELETE USING (true);
```
3. Перейдите в **Project Settings -> API** и скопируйте:
   - **Project URL** (например: `https://abcdefghijkl.supabase.co`)
   - **Project API Keys** -> `anon public`

---

## 🌐 Деплой на Render

### Вариант 1: Через Blueprint (1 клик)
В репозитории уже настроен файл `render.yaml`.
1. Войдите в [Render Dashboard](https://dashboard.render.com).
2. Нажмите **New +** -> **Blueprint**.
3. Выберите репозиторий `coin` (или `coin-hub`).
4. Укажите переменные окружения `SUPABASE_URL` и `SUPABASE_KEY`.
5. Нажмите **Apply**.

### Вариант 2: Вручную (Web Service)
1. Нажмите **New +** -> **Web Service**.
2. Подключите этот репозиторий GitHub.
3. Настройки сервиса:
   - **Name:** `coin-app`
   - **Environment:** `Python 3`
   - **Region:** `Frankfurt (EU)`
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Health Check Path:** `/health`
4. В разделе **Environment Variables** добавьте:
   - `SUPABASE_URL` = ваш Supabase Project URL
   - `SUPABASE_KEY` = ваш Supabase Anon Key
   - `SECRET_KEY` = (любая случайная строка)
5. Нажмите **Create Web Service**. Сервис соберется за 1–2 минуты и будет доступен по бесплатному URL на `.onrender.com`.

---

## 📁 Структура проекта

```
coin/
├── app.py                  # Главное приложение Flask + REST API
├── requirements.txt        # Зависимости Python
├── Procfile                # Команда запуска для Render / Heroku
├── render.yaml             # Blueprint конфигурация Render
├── supabase_schema.sql     # SQL схема для быстрой инициализации Supabase
├── .env.example            # Пример переменных окружения
├── .gitignore              # Исключения для Git
├── templates/
│   └── index.html          # Главная страница веб-интерфейса
└── static/
    ├── css/
    │   └── style.css       # Стилистика (Dark Glassmorphism)
    └── js/
        └── app.js          # Логика клиента (котировки, Supabase CRUD)
```
