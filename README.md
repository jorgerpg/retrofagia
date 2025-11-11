# Retrofagia

Mini rede social para reviews de álbuns com chat privado, construída em Flask + PostgreSQL e pensada para uso tanto em desktop quanto em mobile (layout dark responsivo e barra de navegação inferior).

---

## ✨ Principais funcionalidades

### Experiência social
- Cadastro/login com sessão persistente e avatars personalizados.
- Seguir pessoas para montar um feed só com as reviews relevantes.
- Chat privado entre seguidores/seguidos, com long-polling e histórico incremental.

### Reviews e comentários
- Avaliações de 1 a 5 estrelas usando o seletor visual de estrelas.
- Feed e páginas de álbuns mostram apenas os 5 comentários mais recentes, com link para ver todos.
- Donos de reviews e autores dos comentários podem apagar seus próprios comentários.
- Tela dedicada para cada review exibindo o texto completo e todos os comentários.

### Coleção de álbuns
- Coleção particular para cada usuário, com upload de capa e customização por item.
- Busca dinâmica dentro da página da coleção: encontra álbuns já cadastrados por outros usuários e adiciona-os em um clique (sem duplicar no banco).
- Caso o álbum não exista, há um fluxo separado para cadastro manual com título, artista/banda e capa.
- Ao adicionar um álbum existente a partir da busca, o usuário é redirecionado direto para a view do álbum, facilitando a publicação da review.

### UI/UX
- Tema escuro minimalista com tipografia Inter, suporte completo a mobile (incluindo safe-area para notches).
- Barra inferior com atalhos para feed, coleção, chat e perfil quando autenticado.
- Formulários e cartões preparados para teclado virtual/mobile (chat e comentários).

---

## 🧱 Stack e arquitetura

- **Python 3.11 + Flask 3** para o backend.
- **SQLAlchemy** como ORM e PostgreSQL como banco de dados.
- **Flask-Login** para autenticação baseada em sessão.
- **Docker + Docker Compose** para provisionar app + banco rapidamente.
- **HTML + Jinja2** no server-side e **CSS puro** para o tema.
- **JavaScript vanilla** para funcionalidades como chat em tempo real (long polling), busca de álbuns e notificações via SSE-like polling.

---

## 🚀 Como executar

### Via Docker (recomendado)
1. Clone este repositório e entre na pasta:
   ```bash
   git clone https://github.com/.../retrofagia.git
   cd retrofagia
   ```
2. Suba os serviços:
   ```bash
   docker compose up --build
   ```
3. A aplicação ficará disponível em [http://localhost:5000](http://localhost:5000).

### Ambiente local (sem Docker)
1. Instale o PostgreSQL localmente e crie um database vazio (`retrofagia`).
2. Configure as variáveis de ambiente:
   ```bash
   export FLASK_APP=app
   export FLASK_ENV=development
   export DATABASE_URL="postgresql+psycopg2://usuario:senha@localhost:5432/retrofagia"
   export SECRET_KEY="algum-segredo"
   ```
3. Crie e ative um virtualenv:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Inicialize o banco na primeira execução:
   ```bash
   flask shell -c "from app import db, create_app; app = create_app(); app.app_context().push(); db.create_all()"
   ```
5. Rode o servidor de desenvolvimento:
   ```bash
   flask run --debug
   ```

---

## 🧪 Popular com dados de exemplo

Use o script `mock_actions.py` para gerar usuários, follows, álbuns, reviews, comentários e mensagens de demonstração:

```bash
docker compose run --rm web python scripts/mock_actions.py
```

Ele reinicializa o banco, recria uploads e executa os fluxos principais via cliente de teste do Flask, imprimindo um resumo das interações.

---

## 📁 Estrutura do projeto

```
app/
├── __init__.py        # factory do Flask, bootstrap do banco e filtros globais
├── auth.py            # rotas de autenticação
├── main.py            # feed, coleção, reviews, chat e APIs auxiliares
├── models.py          # modelos SQLAlchemy
├── templates/         # views Jinja2 (base, feed, álbuns, chat, etc.)
└── static/
    ├── style.css      # tema dark responsivo
    ├── app.js         # chat, buscas e notificações
    └── uploads/       # avatares e capas enviados (criado em runtime)
scripts/
└── mock_actions.py    # script para popular o ambiente
Dockerfile             # imagem do serviço web
docker-compose.yml     # orquestra Flask + Postgres
requirements.txt       # dependências Python
```

---

## ⚙️ Variáveis de ambiente

Dentro do `docker-compose.yml` você encontrará valores padrão. Para customizar, crie um `.env` na raiz ou exporte as variáveis antes de subir os serviços.

| Variável        | Descrição                                                                    | Default                                 |
|-----------------|------------------------------------------------------------------------------|-----------------------------------------|
| `DATABASE_URL`  | URL de conexão com o Postgres (driver SQLAlchemy)                            | `postgresql+psycopg2://postgres:postgres@db:5432/retrofagia` |
| `SECRET_KEY`    | Chave usada pelo Flask para assinar sessões                                  | `dev-secret-key`                        |
| `UPLOAD_FOLDER` | Caminho onde as imagens serão gravadas dentro do container                   | `app/static/uploads`                    |
| `MAX_CONTENT_LENGTH` | Limite por upload (já definido como 4MB no `create_app`)                 | `4 * 1024 * 1024`                       |

---

## 🔄 Fluxos principais

- **Coleção de álbuns**  
  - Buscar primeiro (evita duplicatas).  
  - Se já existir na comunidade, clique em “Adicionar” para clonar e abrir direto a página do álbum.  
  - Não encontrou? Use “Cadastrar novo álbum”.

- **Reviews**  
  - Dê notas usando estrelas preenchidas.  
  - Feed/álbum mostram só os 5 últimos comentários; clique em “Ver review” para ver tudo.  
  - Reviewers podem editar ou excluir sua avaliação, e apagar comentários em suas reviews.

- **Chat**  
  - Apenas seguidores/seguidos podem conversar.  
  - Long polling garante chegada de novas mensagens sem precisar recarregar.

---

## 📌 Roadmap / ideias futuras

- Testes automatizados (unitários e de integração) para rotas críticas.
- Notificações em tempo real via WebSockets.
- Paginação no feed e no histórico do chat.
- Suporte a playlists/singles (além de álbuns) e importação via APIs públicas.

Contribuições são bem-vindas! Abra uma issue ou envie um PR descrevendo sua proposta. 🙂
