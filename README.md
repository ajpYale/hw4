# Campus Customs — Shop + Chatbot

MGT 409 Homework 4. A Yale apparel storefront with a PydanticAI shop assistant that
answers from the real catalogue: browse by category, open a product page with live
stock by size, create an account, and ask the chat what we carry.

Built with React + TypeScript + Vite on the front end, FastAPI + PydanticAI on the
back, and SQLite for the shop data.

---

## 1. Get the data pack

The database and product images are **not in this repository** — they are course data.
Download `data.zip` from the MGT 409 materials and unzip it so the `data/` folder sits
beside `backend/` and `frontend/`:

```
hw4/
├── backend/
├── frontend/
└── data/
    ├── campus_customs.db
    └── products/            # product images, paths match the catalogue table
```

## 2. Add your API key

```bash
cp .env.example .env
```

Then fill in `PORTKEY_API_KEY`. The backend reads `hw4/.env` first and falls back to a
`.env` in the parent folder.

`SESSION_SECRET` is optional but recommended — it signs the login cookie. Generate one
with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## 3. Run the backend

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows
# .venv/bin/pip install -r requirements.txt        # macOS / Linux
```

Then, **from inside the `backend/` folder**:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Check it came up: <http://127.0.0.1:8000/api/health> should report
`{"status":"ok","products":102}`.

## 4. Run the front end

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` and `/static` to port 8000, so there
is no API base URL to configure.

## 5. Log in

A test account ships with the data pack:

```
test@campuscustoms.yale.edu  /  password
```

Or create a new one — registration writes to the `users` table with a PBKDF2 hash.

---

## Things to try

| Ask the chat | What it demonstrates |
|---|---|
| "what hoodies do you have?" | Catalogue search, with matches rendered as clickable product cards |
| "do you have the Baseball Left Chest Crewneck in XL?" | Honest stock — XL is sold out |
| "do you have this in pink?" *(on a product page)* | Page context: "this" resolves to the product on screen |
| "show me quarter-zips under $70" | No dead ends — the cheapest is $72, and it says so |
| "which of those is cheapest?" | Conversation memory, for signed-in customers |

---

## Layout

```
hw4/
├── AI_prompts.md            # the prompts used to build this, per problem
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── frontend/                # React + TypeScript + Vite
│   └── src/
│       ├── api.ts           # typed API client
│       ├── auth.tsx         # session context
│       ├── components/      # NavBar, ProductCard, ChatWidget
│       └── pages/           # Home, Products, ProductDetail, About, Login, CreateAccount
├── backend/
│   ├── main.py              # FastAPI app — catalogue, auth and chat routes
│   ├── agent.py             # the PydanticAI agent and its tools
│   ├── tools.py             # database access, chat history, audit log
│   ├── models.py            # shared Pydantic types
│   └── prompts/
│       └── prompt.md        # system prompt and safety rules
└── output/
    ├── harness.md           # how the whole system fits together
    ├── design.md            # the visual design and why
    ├── usability.md         # four usability improvements
    ├── app_check.html       # site testing, with screenshots
    ├── app_check_images/
    └── audit_trail.json     # append-only log of every tool call
```

The agent is the four files under `backend/`: `prompts/prompt.md`, `agent.py`,
`tools.py`, and `models.py`.

## How it works

`output/harness.md` is the full write-up — database fields, auth, the agent's tools and
why their return types are shaped the way they are, chat history, safety, and limits.

The one design decision worth repeating here: **the language model never produces
product data.** It writes prose; the tools record which product ids they actually
returned from SQLite; the server rebuilds the cards from the database afterwards. The
prose and the numbers come from different sources, so a hallucinated price cannot
reach a customer.

## Note

The database, product images and `.env` are excluded by `.gitignore` and must never be
committed.
