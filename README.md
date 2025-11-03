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
- Upload local de avatares e capas de álbuns com validação de formato.
- Busca por perfis e álbuns com atalho para seguir usuários ou adicionar discos à sua coleção.
- Perfil de álbuns com estatísticas, todas as reviews e formulário rápido para avaliar.
- Comentários em reviews e controles para editar ou excluir suas próprias avaliações.
- Capa de álbum compartilhada automaticamente e personalização individual da imagem em cada coleção.
- Navegação móvel com barra inferior por ícones (feed, coleção, chat e perfil) e busca fixa no topo.
- Chat responsivo com carrossel de contatos e balões que se ajustam ao tamanho da mensagem.

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

## Mock de ações automáticas

Para popular o ambiente com usuários, follows, álbuns, reviews, comentários e mensagens de exemplo, rode:

```bash
docker compose run --rm web python scripts/mock_actions.py
```

O script reinicializa o banco e os uploads, executa os fluxos principais (cadastro, login, uploads, follow, reviews, comentários, edições, chat) via cliente de teste Flask e imprime um resumo das interações criadas.

## Estrutura

- `app/`: Aplicação Flask
  - `__init__.py`: factory do app e inicialização do banco
  - `models.py`: modelos SQLAlchemy (usuários, follows, álbuns, reviews, mensagens)
  - `auth.py`: rotas de autenticação
  - `main.py`: rotas do feed, perfil, coleção e chat
  - `templates/`: páginas HTML com Jinja2
  - `static/style.css`: tema escuro minimalista
  - `static/uploads/`: arquivos enviados pelos usuários
- `scripts/mock_actions.py`: script de mock para simular os fluxos da aplicação
- `Dockerfile`: define a imagem do serviço web
- `docker-compose.yml`: orquestra o app Flask e o PostgreSQL
- `requirements.txt`: dependências Python

## Variáveis de ambiente

O `docker-compose.yml` define valores padrão:

- `DATABASE_URL`: conexão com o Postgres
- `SECRET_KEY`: chave para sessões Flask
- `UPLOAD_FOLDER`: caminho (dentro do container) onde as imagens são salvas; padrão `app/static/uploads`

Você pode sobrescrever os valores criando um arquivo `.env` na raiz ou definindo variáveis ao executar o compose.

## Próximos passos sugeridos

- Implementar redimensionamento e otimização das imagens enviadas.
- Persistir uploads em storage externo (S3, etc.) para ambientes de produção.
- Criar testes automatizados para rotas críticas.
- Adicionar notificações para novos follows e mensagens.
