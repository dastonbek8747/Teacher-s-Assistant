<div align="center">

# 🎓 Ustoz AI — Teacher's Assistant

### O'qituvchilar uchun ko'p agentli (multi-agent) sun'iy intellekt platformasi

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-FF6F00)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-success)]()

**Ustoz AI** — o'qituvchining kundalik ishini avtomatlashtiradigan aqlli yordamchi.
Bitta **Supervisor** agent foydalanuvchi so'rovini tahlil qiladi, uni eng mos
mutaxassis agentga yo'naltiradi va natijani tekshirib, yakuniy javob qaytaradi.

</div>

---

## 📋 Mundarija

- [Asosiy imkoniyatlar](#-asosiy-imkoniyatlar)
- [Arxitektura](#-arxitektura)
- [Agentlar jamoasi](#-agentlar-jamoasi)
- [Texnologiyalar](#-texnologiyalar)
- [Loyiha tuzilishi](#-loyiha-tuzilishi)
- [Tez boshlash](#-tez-boshlash)
- [Muhit o'zgaruvchilari](#-muhit-ozgaruvchilari)
- [API qo'llanma](#-api-qollanma)
- [Docker bilan ishga tushirish](#-docker-bilan-ishga-tushirish)
- [Xavfsizlik](#-xavfsizlik)
- [Muammolarni bartaraf etish](#-muammolarni-bartaraf-etish)
- [Yo'l xaritasi](#-yol-xaritasi)
- [Hissa qo'shish](#-hissa-qoshish)
- [Litsenziya](#-litsenziya)

---

## ✨ Asosiy imkoniyatlar

| | Imkoniyat | Tavsif |
|---|---|---|
| 🧠 | **Supervisor arxitekturasi** | Markaziy agent so'rovni tahlil qiladi va mos mutaxassisni tanlaydi |
| 🔁 | **O'zini tuzatish (self-correction)** | Agent javobi qabul qilinmasa, feedback bilan qayta urinadi (`max_attempts`) |
| 🌐 | **Brauzer boshqaruvi** | e-maktab, YouTube, Telegram web — real vaqtda ma'lumot va amallar |
| 🗄️ | **Database agent** | Ma'lumotlarni o'qish/yozish/yangilash/o'chirish (PostgreSQL) |
| 📄 | **Hujjat agenti** | Word, Excel, PowerPoint, PDF yaratish va tahrirlash |
| 🎮 | **O'yin generatori** | Mavzu bo'yicha bitta `.html` interaktiv o'yin yaratadi |
| 📚 | **Dars rejasi agenti** | Sinf va mavzu uchun metodik dars rejasi va faollik g'oyalari |
| 🔍 | **RAG agent** | Qdrant vektor bazasidan ma'no bo'yicha qidiruv |
| 🕵️ | **Research agent** | Internetdan chuqur, manbali qidiruv |
| 🔐 | **JWT autentifikatsiya** | Argon2 parol hashlash + Bearer token |
| 📖 | **Avtomatik hujjat** | Swagger UI (`/docs`) va ReDoc (`/redoc`) |

---

## 🏗 Arxitektura

### Umumiy oqim

```mermaid
flowchart TD
    U([👤 Foydalanuvchi]) -->|POST /api/v1/chat + JWT| API[⚡ FastAPI]
    API --> SUP{{🧠 Supervisor Agent}}

    SUP -->|brauzer| B[🌐 Brauzer]
    SUP -->|database| DB[🗄️ Database]
    SUP -->|document| DOC[📄 Document]
    SUP -->|game| G[🎮 Game]
    SUP -->|lesson| L[📚 Lesson]
    SUP -->|rag| R[🔍 RAG]
    SUP -->|research| RS[🕵️ Research]

    B --> SUP
    DB --> SUP
    DOC --> SUP
    G --> SUP
    L --> SUP
    R --> SUP
    RS --> SUP

    SUP -->|finally_response| API
    API -->|JSON javob| U

    SUP -.->|javob tasdiqlanmasa: feedback + retry| SUP
```

### LangGraph grafi (avtomatik generatsiya qilingan)

<p align="center">
  <img src="backend/graph/graph.png" alt="LangGraph agent diagrammasi" width="100%">
</p>

> Graf `backend/graph/nodes.py` dagi `StateGraph` ta'rifidan
> `graph.get_graph().draw_mermaid_png()` orqali yaratilgan.

**Ish logikasi:**

1. `__start__` → `supervisior_node`
2. Supervisor so'rovni tahlil qiladi:
   - oddiy savol bo'lsa → o'zi javob beradi va `__end__` ga o'tadi;
   - topshiriq bo'lsa → `next_agent` bo'yicha mos agentga yo'naltiradi.
3. Agent natijani `respoonse_agent` sifatida supervisorga qaytaradi.
4. Supervisor javobni tekshiradi:
   - ✅ `approved=True` → `finally_response` yoziladi → `__end__`
   - ❌ `approved=False` → `feedback` beriladi, `attempts += 1`, qayta urinish
5. `attempts > max_attempts` (default `5`) → uzr so'rab yakunlanadi.

---

## 🤖 Agentlar jamoasi

| Kalit | Node | Vazifasi |
|---|---|---|
| `brauzer` | `brauzer_node` | Brauzerni boshqarish: e-maktab, YouTube, Telegram web, boshqa saytlar. Jonli ma'lumot. |
| `database` | `db_node` | PostgreSQL bilan ishlash: CRUD, jadval, eslatmalar, tuzilgan ma'lumot. |
| `document` | `document_node` | Word / Excel / PowerPoint / PDF fayllarni o'qish, yozish, yaratish. |
| `game` | `game_node` | Mavzu bo'yicha bitta `.html` o'yin generatsiyasi. |
| `lesson` | `lesson_node` | Dars rejasi, metodlar, sinf uchun faollik g'oyalari. |
| `rag` | `rag_node` | Qdrant vektor bazasiga saqlash va ma'no bo'yicha qidirish. |
| `research` | `research_node` | Internetdan chuqur, manbali tadqiqot. |

---

## 🧰 Texnologiyalar

<div align="center">

| Qatlam | Texnologiya |
|---|---|
| **API** | FastAPI, Uvicorn, Pydantic v2 |
| **Agentlar** | LangChain, LangGraph, DeepSeek LLM |
| **Checkpoint** | LangGraph PostgresSaver |
| **Ma'lumotlar bazasi** | PostgreSQL, SQLAlchemy |
| **Vektor qidiruv** | Qdrant, HuggingFace embeddings (`BAAI/bge-m3`) |
| **Autentifikatsiya** | PyJWT, Argon2 |
| **Hujjatlar** | python-docx, openpyxl, python-pptx, pypdf, unstructured |
| **Brauzer** | Playwright / Chrome CDP |
| **Deploy** | Docker, Docker Compose |

</div>

---

## 📁 Loyiha tuzilishi

```text
Teacher-s-Assistant/
├── backend/
│   ├── main.py                  # FastAPI ilovasi (routerlar, CORS, static)
│   ├── config.py                # Sozlamalar (.env)
│   ├── Dockerfile               # Backend obraz
│   ├── requirements.txt         # Python bog'liqliklar
│   ├── .env.example             # Muhit o'zgaruvchilari namunasi
│   │
│   ├── api/                     # HTTP API qatlami
│   │   ├── models.py            # SQLAlchemy User modeli
│   │   ├── schemas.py           # Pydantic request/response sxemalari
│   │   ├── db_conn.py           # DB engine va sessiya
│   │   ├── security.py          # JWT yaratish/dekodlash
│   │   ├── deps.py              # get_current_user dependency
│   │   ├── hashing_password.py  # Argon2 hashlash
│   │   ├── agents_registry.py   # Agentlar ro'yxati
│   │   └── routes/
│   │       ├── auth.py          # /auth/* endpoint'lari
│   │       ├── chat.py          # /chat endpoint'i
│   │       ├── health.py        # /health
│   │       └── agents.py        # /agents
│   │
│   ├── graph/                   # LangGraph
│   │   ├── nodes.py             # Supervisor + agent node'lari
│   │   ├── states.py            # State sxemalari
│   │   └── graph.png            # Avtomatik chizilgan graf
│   │
│   ├── agents/                  # Har bir mutaxassis agent
│   ├── prompts/                 # System prompt'lar
│   ├── tools/                   # Tool'lar (browser, DB, fayl, vektor, search)
│   ├── llm/                     # LLM konfiguratsiyalari
│   └── creating_files/          # Yaratilgan fayllar (static)
│
├── docker-compose.yml           # PostgreSQL + Qdrant + API
├── .gitignore
└── README.md
```

---

## 🚀 Tez boshlash

### Talablar

- Python **3.11+** (tavsiya: 3.12)
- PostgreSQL **14+** (LangGraph checkpointer uchun)
- Qdrant (RAG agent uchun, ixtiyoriy)
- Kamida bitta LLM API kaliti (DeepSeek va h.k.)

### 1️⃣ Reponi klonlash

```bash
git clone https://github.com/dastonbek8747/Teacher-s-Assistant.git
cd Teacher-s-Assistant
```

### 2️⃣ Virtual muhit va bog'liqliklar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 3️⃣ `.env` faylini sozlash

```bash
cp backend/.env.example backend/.env
```

`backend/.env` faylini ochib, kalitlarni to'ldiring:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/teachflow
DEEPSEEK_API_KEY=sk-...
JWT_SECRET_KEY=<uzun-tasodifiy-satr>
```

### 4️⃣ Serverni ishga tushirish

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

Yoki to'g'ridan-to'g'ri:

```bash
python -m backend.main
```

Tayyor! 🎉

| Manzil | Tavsif |
|---|---|
| http://localhost:8001/ | API ma'lumoti |
| http://localhost:8001/docs | **Swagger UI** (interaktiv) |
| http://localhost:8001/redoc | ReDoc |
| http://localhost:8001/api/v1/health | Health check |

---

## ⚙️ Muhit o'zgaruvchilari

| O'zgaruvchi | Majburiy | Default | Tavsif |
|---|:---:|---|---|
| `DATABASE_URL` | ✅ | `sqlite:///./teachflow.db` | PostgreSQL ulanish satri (checkpointer uchun Postgres) |
| `DEEPSEEK_API_KEY` | ✅ | — | DeepSeek LLM kaliti |
| `JWT_SECRET_KEY` | ✅ | *o'zgartirish shart* | JWT imzolash kaliti (32+ belgi) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | `1440` | Token amal qilish muddati (daqiqa) |
| `GEMINI_API_KEY` | ❌ | — | Google Gemini kaliti |
| `OPENROUTER_API_KEY` | ❌ | — | OpenRouter kaliti |
| `GROQ_API_KEY` | ❌ | — | Groq kaliti |
| `NVIDIA_API_KEY` | ❌ | — | NVIDIA kaliti |
| `TAVILY_SEARCH_API_KEY` | ❌ | — | Tavily qidiruv kaliti |
| `QDRANT_URL` | ❌ | `http://localhost:6333` | Qdrant manzili |
| `CORS_ORIGINS` | ❌ | `*` | Ruxsat etilgan origin'lar (vergul bilan) |
| `CREATE_TABLES_ON_STARTUP` | ❌ | `true` | Startup'da jadvallarni yaratish |
| `PROJECT_NAME` | ❌ | `Ustoz AI — Teacher's Assistant` | Ilova nomi |
| `VERSION` | ❌ | `1.0.0` | Versiya |

> 💡 To'liq ro'yxat: [`backend/.env.example`](backend/.env.example)

---

## 📡 API qo'llanma

**Base URL:** `http://localhost:8001`
**API prefix:** `/api/v1`

### Endpoint'lar

| Method | Endpoint | Auth | Tavsif |
|---|---|:---:|---|
| `GET` | `/` | ❌ | API haqida ma'lumot |
| `GET` | `/health` · `/api/v1/health` | ❌ | Ilova va DB holati |
| `POST` | `/api/v1/auth/register` | ❌ | Ro'yxatdan o'tish |
| `POST` | `/api/v1/auth/login` | ❌ | Kirish (JSON) → JWT |
| `POST` | `/api/v1/auth/token` | ❌ | Kirish (OAuth2 form, Swagger uchun) |
| `GET` | `/api/v1/auth/me` | ✅ | Joriy foydalanuvchi profili |
| `GET` | `/api/v1/agents` | ❌ | Mutaxassis agentlar ro'yxati |
| `POST` | `/api/v1/chat` | ✅ | AI agentlar bilan suhbat |

### 🔑 Autentifikatsiya oqimi

```text
register → login (JWT) → Authorization: Bearer <token> → chat
```

### 1) Ro'yxatdan o'tish

```bash
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "ustoz_ali",
    "email": "ali@example.com",
    "password": "StrongPass123",
    "confirm_password": "StrongPass123"
  }'
```

**Javob `201 Created`:**

```json
{
  "id": 1,
  "username": "ustoz_ali",
  "email": "ali@example.com",
  "created_at": "2026-11-21T08:46:08"
}
```

### 2) Tizimga kirish (token olish)

```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "ustoz_ali", "password": "StrongPass123"}'
```

**Javob `200 OK`:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in_minutes": 1440
}
```

### 3) Profil

```bash
curl http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### 4) Suhbat (asosiy endpoint)

```bash
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "7-A sinfga informatika fanidan dars rejasini tayyorla",
    "session_id": "optional-session-id"
  }'
```

**Javob `200 OK`:**

```json
{
  "session_id": "1-4670921f-47b7-4c43-ad5a-6aa9f622c501",
  "response": "Mana 7-A sinf uchun informatika dars rejasi...",
  "approved": true,
  "attempts": 0,
  "next_agent": "lesson",
  "raw": {
    "finally_response": "Mana 7-A sinf uchun informatika dars rejasi...",
    "response_agent_approved": true,
    "attempts": 0,
    "next_agent": "lesson"
  }
}
```

> `session_id` — suhbat kontekstini saqlash uchun. Bir xil `session_id` bilan
> yuborilgan so'rovlar oldingi suhbat tarixini davom ettiradi.

### 5) Agentlar ro'yxati

```bash
curl http://localhost:8001/api/v1/agents
```

### 6) Health check

```bash
curl http://localhost:8001/api/v1/health
```

```json
{ "status": "ok", "version": "1.0.0", "database": "ok" }
```

### 📌 Xato kodlari

| Kod | Ma'no |
|---|---|
| `401` | Token yo'q, yaroqsiz yoki muddati o'tgan |
| `409` | Username yoki email allaqachon band |
| `422` | Validatsiya xatosi (parollar mos emas, email noto'g'ri...) |
| `502` | Agent/LLM ishlashida xatolik |

---

## 🐳 Docker bilan ishga tushirish

Bitta buyruq bilan PostgreSQL + Qdrant + API:

```bash
cp backend/.env.example backend/.env
# backend/.env ichida DEEPSEEK_API_KEY va JWT_SECRET_KEY ni to'ldiring

docker compose up --build
```

Xizmatlar:

| Xizmat | Port |
|---|---|
| API | `8001` |
| PostgreSQL | `5432` |
| Qdrant | `6333` (REST) · `6334` (gRPC) |

To'xtatish:

```bash
docker compose down          # konteynerlarni to'xtatish
docker compose down -v       # + ma'lumotlarni o'chirish
```

---

## 🔒 Xavfsizlik

- 🔑 Parollar **Argon2** bilan hashlanadi (ochiq holda saqlanmaydi).
- 🎫 API **JWT Bearer** token bilan himoyalangan.
- 🚫 `.env` fayli **git'ga qo'shilmaydi** (`.gitignore` da).
- ⚠️ Production'da albatta:
  - `JWT_SECRET_KEY` ni uzoq tasodifiy satrga almashtiring;
  - `CORS_ORIGINS` ni aniq domenlar bilan cheklang (`*` emas);
  - HTTPS orqali ishlating;
  - `CREATE_TABLES_ON_STARTUP=false` qilib, migratsiyalardan foydalaning.

> ❗ Agar API kalitlaringiz biror marta ommaviy repoga tushgan bo'lsa,
> ularni darhol bekor qiling (rotate) va yangisini yarating.

---

## 🩺 Muammolarni bartaraf etish

<details>
<summary><b>ModuleNotFoundError: No module named 'backend'</b></summary>

Repo **ildizidan** ishga tushiring:

```bash
uvicorn backend.main:app --reload
```

yoki `PYTHONPATH` ni o'rnating:

```bash
export PYTHONPATH=$(pwd)
```
</details>

<details>
<summary><b>psycopg2 / libpq xatosi</b></summary>

Debian/Ubuntu:

```bash
sudo apt-get install -y libpq-dev build-essential
```

macOS:

```bash
brew install postgresql
```
</details>

<details>
<summary><b>LangGraph checkpointer ulanmayapti</b></summary>

`DATABASE_URL` PostgreSQL'ga ishora qilishini tekshiring. SQLite checkpointer
uchun mos emas:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/teachflow
```
</details>

<details>
<summary><b>RAG agent Qdrant'ga ulanmayapti</b></summary>

Qdrant ishga tushiring:

```bash
docker run -p 6333:6333 qdrant/qdrant
```

yoki `QDRANT_URL` ni to'g'ri manzilga o'rnating.
</details>

---

## 🗺 Yo'l xaritasi

- [x] FastAPI REST API (auth + chat)
- [x] JWT autentifikatsiya
- [x] Docker Compose (Postgres + Qdrant)
- [ ] Chat uchun SSE / WebSocket streaming
- [ ] Alembic migratsiyalar
- [ ] Suhbatlar tarixi endpoint'i (`/api/v1/sessions`)
- [ ] Rate limiting va audit log
- [ ] Frontend (React / Next.js)
- [ ] Unit va integration testlar (pytest)
- [ ] CI/CD (GitHub Actions)

---

## 🤝 Hissa qo'shish

1. Reponi **fork** qiling
2. Yangi branch oching: `git checkout -b feature/ajoyib-yangilik`
3. O'zgarishlarni commit qiling: `git commit -m "feat: ajoyib yangilik"`
4. Branch'ni push qiling: `git push origin feature/ajoyib-yangilik`
5. **Pull Request** oching

---

## 📄 Litsenziya

Ushbu loyiha **MIT** litsenziyasi ostida tarqatiladi.

---

<div align="center">

**🎓 Ustoz AI** — o'qituvchining vaqtini tejaydigan aqlli yordamchi

Made with ❤️ by [dastonbek8747](https://github.com/dastonbek8747)

</div>
