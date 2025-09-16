# Retrofagia

App para catalogar discos (vinil/álbuns), avaliar, seguir amigos e acompanhar um feed de atividades — com mensagens privadas entre usuários.

## 🧱 Stack

* **Backend**: FastAPI + SQLAlchemy 2.0 + Alembic + JWT (PyJWT) + PostgreSQL + psycopg
* **Infra**: Docker Compose (db + backend), uploads estáticos servidos via FastAPI
* **Frontend**: React (Vite + TS) + React Router + React Query + Zustand + Tailwind (`@tailwindcss/postcss`) + lucide-react

---

## 📦 Estrutura de diretórios

```
retrofagia/
├─ backend/
│  ├─ app/
│  │  ├─ main.py            # instancia FastAPI, mounts, includes de routers
│  │  ├─ db.py              # SessionLocal, engine, Base
│  │  ├─ models.py          # Users, Records, Reviews, Follows, Conversations, etc.
│  │  ├─ schemas.py         # Pydantic models (v2)
│  │  ├─ deps.py            # get_db, get_current_user
│  │  └─ routers/
│  │     ├─ auth.py         # /auth/register, /auth/login, /auth/me
│  │     ├─ records.py      # CRUD records, comentários, upload/delete de capa
│  │     ├─ collection.py   # adicionar/remover da coleção, favoritos, listagens
│  │     ├─ reviews.py      # criação/upsert de review 0..5, "minha avaliação"
│  │     ├─ feed.py         # feed cronológico, likes e comentários em atividades
│  │     ├─ follows.py      # seguir/seguir de volta
│  │     └─ conversations.py# DMs (conversas e histórico)
│  ├─ alembic/              # migrações
│  ├─ requirements.txt
│  └─ Dockerfile
├─ frontend/
│  ├─ src/
│  │  ├─ main.tsx           # Router + QueryClientProvider + Protected routes
│  │  ├─ layouts/AppShell.tsx
│  │  ├─ lib/api.ts         # Axios com Authorization
│  │  ├─ store/auth.ts      # Zustand (token + /auth/me)
│  │  ├─ components/
│  │  │  ├─ RecordCard.tsx
│  │  │  ├─ AddRecordModal.tsx
│  │  │  └─ Stars.tsx
│  │  ├─ pages/
│  │  │  ├─ Feed.tsx
│  │  │  ├─ Collection.tsx
│  │  │  ├─ RecordDetail.tsx
│  │  │  ├─ DMs.tsx
│  │  │  └─ Login.tsx
│  │  ├─ types.ts
│  │  └─ index.css          # Tailwind + estilos utilitários
│  ├─ postcss.config.js     # usa @tailwindcss/postcss
│  ├─ tailwind.config.js
│  └─ vite.config.ts
├─ docker-compose.yaml
├─ tests_retrofagia.sh      # testes de ponta-a-ponta via curl
└─ README.md
```

---

## ✅ O que já está implementado

### Backend

* [x] **Autenticação JWT**

  * `/auth/register`, `/auth/login`, `/auth/me`
* [x] **Modelos e persistência** (PostgreSQL via SQLAlchemy/Alembic)

  * `users`, `records`, `reviews`, `user_collection`, `follows`, `comments`, `conversations`, `messages`, `activity`, `activity_likes`
* [x] **Cadastro e busca de discos**

  * `POST /records` (com `matrix_code` único)
  * `GET /records?code=...` + filtros avançados `year`, `genre`, `label`
* [x] **Coleção do usuário**

  * `POST /collection/{record_id}` (adiciona)
  * `PATCH /collection/{record_id}` (`is_favorite`)
  * `GET /collection/me` e `GET /collection/me/favorites`
  * `DELETE /collection/{record_id}` (remover da coleção) **Novo**
* [x] **Avaliações 0..5 estrelas**

  * `POST /reviews` (upsert por user+record, validação 0..5) **Atualizado**
  * `GET /reviews/records/{record_id}/me` (minha avaliação) **Novo**
* [x] **Comentários**

  * `POST /records/{id}/comments` e `GET /records/{id}/comments`
* [x] **Seguidores / Feed**

  * `POST /users/{user_id}/follow`
  * `GET /feed?limit=N` (atividades: ADD\_RECORD, REVIEW, COMMENT, FOLLOW)
  * `POST /feed/{activity_id}/like`, `POST /feed/{activity_id}/comments`, `GET /feed/{activity_id}/comments`
* [x] **Mensagens privadas (DMs)**

  * `POST /conversations` (A <-> B), `POST /conversations/{id}/messages`, `GET /conversations/{id}/messages`
* [x] **Uploads estáticos de capa**

  * `PUT /records/{id}/cover` (salva em `uploads/covers/<id>.webp`) **Novo**
  * `DELETE /records/{id}/cover` (remove arquivo) **Novo**
  * `GET /uploads/covers/<id>.webp` (servido por StaticFiles)

### Frontend

* [x] **AppShell responsivo** (topbar, content, bottom tab em mobile)
* [x] **Login** (guarda token em localStorage, `/auth/me`)
* [x] **Feed** (lista atividades, like/comentar activity)
* [x] **Coleção**

  * listagem responsiva (2/3/4/5 colunas), busca local, favoritos
  * **FAB** com **modal “Adicionar Disco”**: cria `record` + adiciona à coleção; se `matrix_code` duplicado, busca e adiciona mesmo assim
* [x] **Detalhe do Disco**

  * capa (upload/remover), metadados
  * **minha avaliação** 0..5 com estrelas (salva e reaparece ao abrir)
  * comentários do disco
  * **remover da coleção** (navega de volta pra lista)
* [x] **DMs** (tela base)
* [x] **Style**: Tailwind com `@tailwindcss/postcss`, componentes utilitários (`btn`, `card`, `input`, `badge`, etc.), grid e fab fix dentro do container.

### Testes de ponta-a-ponta (script)

* [x] `tests_retrofagia.sh` cobre:

  * auth (2 usuários), criação/busca de record, adicionar à coleção, avaliar, feed, comentar, favoritos, busca avançada, follow, like/comentar activity, DMs (ida/volta), duplicidade de `matrix_code`.

> Observação: o script ainda **não cobre** os novos endpoints de **capa** e **remover da coleção**; ver “Próximos passos”.

---

## 🚀 Como rodar (dev)

### Requisitos

* Docker & Docker Compose
* Node 18+ (para o frontend)

### Backend

```bash
cd backend
# (opcional) ajustar .env com SECRET_KEY / DB_URL se usar fora do compose
docker compose up -d  # sobe db e backend
# docs local: http://localhost:8000/docs
```

> Uploads persistem no diretório `backend/uploads`. Considere mapear volume no compose para não perder arquivos.

### Frontend

```bash
cd frontend
npm i
# atenção: Tailwind usa @tailwindcss/postcss, já configurado em postcss.config.js
npm run dev
# app: http://localhost:5173
```

**.env exemplo (frontend):**

```
VITE_API_URL=http://localhost:8000
```

---

## 🧪 Testes de API (shell)

Na raiz do projeto:

```bash
chmod +x tests_retrofagia.sh
./tests_retrofagia.sh
```

Saída esperada: todos os testes “✅”.

---

## 🧰 Troubleshooting

* **Docker “permission denied” no socket**
  Adicione seu usuário ao grupo `docker` e relogue:

  ```bash
  sudo usermod -aG docker $USER
  newgrp docker
  ```
* **bcrypt / passlib warning**
  Fix recomendado em `requirements.txt`:

  ```
  bcrypt==4.1.3
  passlib[bcrypt]==1.7.4
  ```
* **Tailwind erro “use `@tailwindcss/postcss`”**
  Já corrigido: `postcss.config.js` usa `require("@tailwindcss/postcss")`.
* **Imports TS “import type …”**
  Em TS/TSX use `import { type X } from "…"`. Em JS/JSX, use `import { X }`.

---

## 🧭 Roadmap & Checklists

### Backend

* [x] JWT auth, Users, Records, Collection, Reviews, Comments, Follows, Feed, DMs
* [x] Upload/DELETE de capa (arquivos estáticos)
* [x] Minha avaliação (`GET /reviews/records/{id}/me`)
* [ ] **GET `/records/{id}`** (evitar fallback no frontend)
* [ ] Paginação consistente (`/records`, `/feed`, `/comments`)
* [ ] Soft delete / idempotência em mais endpoints
* [ ] Seeds de dados para dev (usuários, discos de exemplo)
* [ ] Logs estruturados + CORS/config por ambiente
* [ ] Segurança: rate limit, senha forte, reset de senha/email verify
* [ ] Armazenamento de capa em S3/Cloud + CDN (produção)
* [ ] Testes automatizados (pytest) + CI (GitHub Actions)

### Frontend

* [x] AppShell responsivo + Bottom Tab
* [x] Login + proteção de rotas
* [x] Feed + Interações
* [x] Coleção + add via modal + favoritos
* [x] Detalhe do Disco: capa (up/del), avaliação 0..5, comentários, remover da coleção
* [ ] **Endpoints dedicados**: consumir `GET /records/{id}` quando disponível
* [ ] Tela de **Busca/Explorar** com filtros (ano/gênero/gravadora) + paginação
* [ ] **Perfil**: minhas avaliações, seguidores/seguindo, coleção pública
* [ ] UI de **DMs** mais completa (lista conversas, não só histórico)
* [ ] Toasts e erros amigáveis (react-hot-toast)
* [ ] Loading states/esqueletos padronizados
* [ ] Preferências de tema (dark já padrão)
* [ ] E2E (Playwright/Cypress)

### Testes & Qualidade

* [x] Script `tests_retrofagia.sh` cobrindo fluxo principal
* [ ] **Estender script** para:

  * [ ] `PUT /records/{id}/cover` (upload com imagem dummy)
  * [ ] `DELETE /records/{id}/cover`
  * [ ] `DELETE /collection/{id}`
  * [ ] `GET /reviews/records/{id}/me` garantindo 0..5
* [ ] Testes unitários backend (pytest) e frontend (vitest)
* [ ] CI (Actions): lint, typecheck, tests

---

## 🔌 Endpoints principais (resumo)

* **Auth**:
  `POST /auth/register` · `POST /auth/login` · `GET /auth/me`
* **Records**:
  `POST /records` · `GET /records?code|year|genre|label`
  `POST /records/{id}/comments` · `GET /records/{id}/comments`
  `PUT /records/{id}/cover` · `DELETE /records/{id}/cover`
  *(futuro)* `GET /records/{id}`
* **Collection**:
  `POST /collection/{id}` · `PATCH /collection/{id}` (`is_favorite`)
  `GET /collection/me` · `GET /collection/me/favorites`
  `DELETE /collection/{id}`
* **Reviews**:
  `POST /reviews` (0..5, upsert)
  `GET /reviews/records/{id}/me`
* **Feed/Follow**:
  `POST /users/{id}/follow` · `GET /feed`
  `POST /feed/{activity_id}/like`
  `POST /feed/{activity_id}/comments` · `GET /feed/{activity_id}/comments`
* **DMs**:
  `POST /conversations` · `POST /conversations/{id}/messages` · `GET /conversations/{id}/messages`

---

## 📋 Próximos passos sugeridos (curto prazo)

* [ ] Backend: `GET /records/{id}`
* [ ] Frontend: Detalhe do Disco usar `GET /records/{id}`
* [ ] Script de testes: cobrir **upload/remover capa** e **remover da coleção**
* [ ] UI de DMs (lista conversas + última mensagem, estados de leitura)
* [ ] Página de Perfil + seguir/desseguir pela UI

Se quiser, eu já te mando o **patch do script de testes** cobrindo capa/remover/coleção/minha avaliação.
