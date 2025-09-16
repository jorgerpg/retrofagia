# Retrofagia — Backend MVP

Colecionador de vinis com feed social, avaliações e DMs. Este README descreve **o que já foi construído**, como **rodar/testar** e os **próximos passos** (com checklists).

---

## 🔧 Stack & Arquitetura

* **API**: FastAPI (Python 3.12)
* **Auth**: JWT (python-jose) + senhas com Passlib/bcrypt

  > 🔇 Para silenciar warnings do passlib com bcrypt, estamos usando `bcrypt==3.2.2`.
* **ORM**: SQLAlchemy **2.x**
* **DB**: PostgreSQL 16
* **Migrações**: Alembic
* **Container**: Docker + Docker Compose
* **Pydantic**: v2 (schemas com `ConfigDict(from_attributes=True)`)

**Diretórios principais (sugestão):**

```
retrofagia/
├─ backend/
│  ├─ app/
│  │  ├─ main.py                 # app FastAPI + CORS + include_routers
│  │  ├─ db.py                   # SessionLocal, engine, Base
│  │  ├─ config.py               # settings (.env)
│  │  ├─ deps.py                 # get_current_user (JWT)
│  │  ├─ models.py               # modelos SQLAlchemy (Users, Records, etc.)
│  │  ├─ schemas.py              # Pydantic v2 (UUID/datetime)
│  │  ├─ activity.py             # create_activity(...)
│  │  └─ routers/
│  │     ├─ auth.py
│  │     ├─ records.py
│  │     ├─ collection.py
│  │     ├─ reviews.py
│  │     ├─ comments.py          # comentários em discos
│  │     ├─ feed.py              # feed + likes + comentários na activity
│  │     ├─ follows.py           # follow/unfollow (204)
│  │     └─ conversations.py     # DMs (1:1)
│  ├─ alembic/ ...               # migrações
│  ├─ requirements.txt
│  ├─ Dockerfile
│  ├─ tests_retrofagia.sh        # script de testes E2E (curl + jq)
│  └─ Makefile                   # up/build/logs/test
├─ docker-compose.yaml
└─ (frontend/ - a ser criado)
```

---

## ✅ Funcionalidades já implementadas

### Usuários & Autenticação

* [x] Registro `/auth/register` (400 se username/email já usados)
* [x] Login `/auth/login` → `access_token` (JWT)
* [x] Perfil atual `/auth/me`

### Discos & Coleção

* [x] Cadastro de disco `/records` (unique por `matrix_code`)
* [x] Busca de discos por `code`, `q`(titulo/artista), `artist`, `year`, `genre`, `label`
* [x] Adicionar à coleção `/collection/{record_id}`
* [x] Favoritar na coleção `PATCH /collection/{record_id} {"is_favorite": true}`
* [x] Listar favoritos `/collection/me/favorites`

### Avaliações & Comentários

* [x] Review com nota/comentário `POST /reviews` (upsert por user+record)
* [x] Comentários em disco `POST/GET /records/{id}/comments`

### Social (seguidores) & Feed

* [x] Seguir usuário `POST /users/{user_id}/follow` (204)
* [x] Feed dos seguidos `/feed?limit=...` (ordem cronológica inversa)
* [x] Atividades no feed: ADD\_RECORD, REVIEW, COMMENT
* [x] Like de atividade `POST/DELETE /feed/{activity_id}/like`
* [x] Comentários em atividade `POST/GET /feed/{activity_id}/comments`

### Mensagens privadas (DMs)

* [x] Criar conversa 1:1 `POST /conversations { other_user_id }`
* [x] Enviar mensagem `POST /conversations/{conversation_id}/messages`
* [x] Listar histórico `GET /conversations/{conversation_id}/messages`

---

## ▶️ Como rodar

Pré-requisitos: **Docker**, **Docker Compose**, `curl`, `jq` e (opcional) `make`.

```bash
# subir serviços
docker compose up -d --build

# ver logs
docker compose logs -f backend
```

Variáveis de ambiente (sugestão de chaves em `.env` usadas no backend):

```
DATABASE_URL=postgresql+psycopg://retrofagia:retrofagia@db:5432/retrofagia
JWT_SECRET=troque-por-uma-chave-segura
JWT_ALG=HS256
```

> **Migrations**: se necessário, rode `alembic upgrade head` dentro do container backend; mas o projeto já vem com as tabelas criadas/testadas.

---

## 🧪 Testes E2E (script)

Usamos um script bash que valida o fluxo **end-to-end** (auth, discos, coleção, reviews, feed, follow, comentários, favoritos, likes, DMs).

```bash
cd backend
chmod +x tests_retrofagia.sh

# direto
./tests_retrofagia.sh

# ou via make
make up && make build && make test
```

Saída esperada (resumo):

```
🎉 TODOS OS TESTES PASSARAM!
```

---

## 🔌 Endpoints (cheat sheet)

**Auth**

* `POST /auth/register` → `{ access_token }`
* `POST /auth/login` → `{ access_token }`
* `GET /auth/me` → `{ id, username, email }`

**Discos**

* `POST /records` → cria (unique `matrix_code`)
* `GET /records?code=...&q=...&artist=...&year=...&genre=...&label=...` → lista

**Coleção**

* `POST /collection/{record_id}` → adiciona
* `PATCH /collection/{record_id}` `{ "is_favorite": true }`
* `GET /collection/me/favorites` → lista de `Record`

**Reviews & Comentários**

* `POST /reviews` `{ record_id, rating, comment? }` → upsert por user+record
* `POST /records/{record_id}/comments` `{ content }`
* `GET  /records/{record_id}/comments`

**Social & Feed**

* `POST /users/{user_id}/follow` → 204
* `GET  /feed?limit=20` → atividades dos seguidos (e do próprio)
* `POST /feed/{activity_id}/like` → 204
* `DELETE /feed/{activity_id}/like` → 204
* `POST /feed/{activity_id}/comments` `{ content }`
* `GET  /feed/{activity_id}/comments`

**DMs**

* `POST /conversations` `{ other_user_id }`
* `POST /conversations/{conversation_id}/messages` `{ content }`
* `GET  /conversations/{conversation_id}/messages`

---

## 🩹 Troubleshooting (erros comuns que já resolvemos)

* **SQLAlchemy 2.x**: não use `Model.id.cast(str)`.
  ✅ Use `from sqlalchemy import cast, String` e compare assim: `cast(Model.id, String) == some_id_str`.

* **UUID vs String no Postgres**: evite `cast(..., String)` quando a coluna é UUID.
  ✅ Tipar o parâmetro de rota como `UUID` e comparar `UUID == UUID` (ex.: DMs `conversation_id: UUID`).

* **Pydantic v2**: tipos corretos nas responses.
  ✅ Campos `id`, `user_id`, `record_id` como `UUID`; `created_at` como `datetime`.
  ✅ `model_config = ConfigDict(from_attributes=True)`.

* **Passlib + bcrypt 4.x**: “(trapped) error reading bcrypt version”.
  ✅ Fix com `bcrypt==3.2.2` em `requirements.txt`.

---

## 📈 Índices recomendados (Alembic)

Para performance (opcional, mas sugerido):

* `records(matrix_code)` (unique)
* `records(title, artist)`
* `user_collection(user_id)`
* `reviews(user_id, record_id)` (unique)
* `follows(follower_id)`
* `activity(actor_id, created_at)`

> Crie uma revisão Alembic `add indexes` e aplique.

---

## 🗺️ Roadmap (próximos passos)

### Frontend (React + Vite + TS + Tailwind + React Query)

* [ ] Setup do projeto (`frontend/`) + CORS no backend
* [ ] Página **Login** (persistência do token + `/auth/me`)
* [ ] Página **Feed** (listar; like/comentar activity)
* [ ] Página **Busca/Explorar** (filtros por ano/gênero/gravadora)
* [ ] Página **Detalhe do Disco** (adicionar à coleção, favoritar, avaliar, comentar, ver reviews)
* [ ] Página **Minha Coleção** / **Favoritos**
* [ ] **Perfil do Usuário** (seguir/unfollow, ver coleção/avaliações)
* [ ] **DMs** (lista de conversas + chat em tempo real depois com WS)
* [ ] UX: toasts, loading states, paginação (cursor no feed), vazio/erros

### Backend (evoluções)

* [ ] Paginação com cursor em `/feed`, `/records`, etc.
* [ ] Validações (ex.: `rating` entre 0–10, tamanho de conteúdo)
* [ ] Uniqueness e constraints robustas (follow único, conversa 1:1 única por par)
* [ ] WebSockets para **DMs** e (talvez) feed ao vivo
* [ ] Notificações (ex.: novo seguidor, novo comentário)
* [ ] Upload/armazenamento de capas (opcional, S3/minio)
* [ ] Logs estruturados (JSON) + correlação de request
* [ ] Seeds de dados para dev (`db/seed.sql`)
* [ ] Healthchecks e métricas (Prometheus/OTel)

### Qualidade & DevOps

* [ ] **pre-commit** (black, ruff) configurado
* [ ] **pytest** com testes de integração (substituir/acompanhar o script bash)
* [ ] **CI** (GitHub Actions): lint, build, testes com serviço Postgres
* [ ] **CD** (deploy container em staging/prod)
* [ ] Ambiente `.env` separado por stage + `pydantic-settings`

---

## 🧭 TL;DR (dev loop)

```bash
# subir
docker compose up -d --build

# testar E2E
cd backend
make test

# logs
docker compose logs -f backend
```
