# retrofagia

Mini rede social para reviews de álbuns com chat privado, construída com Flask, PostgreSQL e Docker.

## Funcionalidades

- Cadastro e login de usuários com sessão persistente.
- Perfil personalizável com bio e avatar.
- Seguimento entre usuários para montar o feed pessoal.
- Coleção própria de álbuns com capa, artista e título.
- Reviews com notas de 1 a 5 estrelas e comentários.
- Feed com reviews dos usuários seguidos.
- Chats privados entre seguidores/seguidos com histórico ordenado.
- Layout dark minimalista e responsivo, preparado para desktop e mobile.

## Requisitos

- Docker
- Docker Compose

## Como executar

1. Clone o repositório e entre na pasta do projeto.
2. Inicie os serviços:

   ```bash
   docker compose up --build
   ```

   O comando cria as imagens, sobe o backend Flask e um banco PostgreSQL já configurado.

3. Acesse o app em [http://localhost:5000](http://localhost:5000).

## Estrutura

- `app/`: Aplicação Flask
  - `__init__.py`: factory do app e inicialização do banco
  - `models.py`: modelos SQLAlchemy (usuários, follows, álbuns, reviews, mensagens)
  - `auth.py`: rotas de autenticação
  - `main.py`: rotas do feed, perfil, coleção e chat
  - `templates/`: páginas HTML com Jinja2
  - `static/style.css`: tema escuro minimalista
- `Dockerfile`: define a imagem do serviço web
- `docker-compose.yml`: orquestra o app Flask e o PostgreSQL
- `requirements.txt`: dependências Python

## Variáveis de ambiente

O `docker-compose.yml` define valores padrão:

- `DATABASE_URL`: conexão com o Postgres
- `SECRET_KEY`: chave para sessões Flask

Você pode sobrescrever os valores criando um arquivo `.env` na raiz ou definindo variáveis ao executar o compose.

## Próximos passos sugeridos

- Adicionar envio de imagens e armazenamento local/S3 para avatares.
- Implementar paginação no feed e nas reviews.
- Criar testes automatizados para rotas críticas.
- Adicionar notificações para novos follows e mensagens.

## Licença

Uso livre para fins educacionais e pessoais.
