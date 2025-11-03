import base64
import io
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app, db
from app.models import Album, Follow, Message, Review, ReviewComment, User

PNG_PLACEHOLDER = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "Xw8AAoMBgA0eMZkAAAAASUVORK5CYII="
)


def image_bytes(filename: str):
    file_obj = io.BytesIO(PNG_PLACEHOLDER)
    file_obj.name = filename
    return file_obj


def reset_uploads(app):
    upload_dir = app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    for entry in os.listdir(upload_dir):
        path = os.path.join(upload_dir, entry)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def main():
    app = create_app()

    with app.app_context():
        reset_uploads(app)
        db.drop_all()
        db.create_all()

        client = app.test_client()

        print("== Registro de usuários ==")
        client.post(
            "/register",
            data={
                "username": "alice",
                "email": "alice@example.com",
                "password": "senha123",
                "confirm": "senha123",
            },
            follow_redirects=True,
        )
        print("• Alice criada")

        client.post(
            "/register",
            data={
                "username": "bob",
                "email": "bob@example.com",
                "password": "senha123",
                "confirm": "senha123",
            },
            follow_redirects=True,
        )
        print("• Bob criado")

        print("\n== Alice atualiza perfil e cria conteúdo ==")
        client.post(
            "/login",
            data={"email": "alice@example.com", "password": "senha123"},
            follow_redirects=True,
        )

        client.post(
            "/profile",
            data={
                "username": "alice",
                "bio": "Aficionada por shoegaze e dream pop.",
                "avatar": (image_bytes("alice.png"), "alice.png"),
            },
            follow_redirects=True,
        )
        print("• Avatar e bio da Alice atualizados")

        client.post(
            "/albums",
            data={
                "title": "Loveless",
                "artist": "My Bloody Valentine",
                "cover": (image_bytes("loveless.png"), "loveless.png"),
            },
            follow_redirects=True,
        )
        client.post(
            "/albums",
            data={
                "title": "Souvlaki",
                "artist": "Slowdive",
                "cover": (image_bytes("souvlaki.png"), "souvlaki.png"),
            },
            follow_redirects=True,
        )
        print("• Alice adicionou dois álbuns")

        alice_album = Album.query.filter_by(title="Loveless").first()
        client.post(
            "/feed",
            data={
                "album_id": str(alice_album.id),
                "rating": "5",
                "content": "Clássico absoluto, texturas infinitas!",
            },
            follow_redirects=True,
        )
        print("• Alice publicou review de Loveless")

        client.get("/logout", follow_redirects=True)

        print("\n== Bob atualiza perfil, segue Alice e interage ==")
        client.post(
            "/login",
            data={"email": "bob@example.com", "password": "senha123"},
            follow_redirects=True,
        )
        client.post(
            "/profile",
            data={
                "username": "bob",
                "bio": "Colecionador de vinis obscuros.",
                "avatar": (image_bytes("bob.png"), "bob.png"),
            },
            follow_redirects=True,
        )
        print("• Avatar e bio do Bob atualizados")

        client.post(f"/follow/alice", follow_redirects=True)
        print("• Bob começou a seguir Alice")

        client.post(
            "/albums",
            data={
                "title": "The Dark Side of the Moon",
                "artist": "Pink Floyd",
                "cover": (image_bytes("darkside.png"), "darkside.png"),
            },
            follow_redirects=True,
        )
        bob_album = Album.query.filter_by(title="The Dark Side of the Moon").first()
        client.post(
            "/feed",
            data={
                "album_id": str(bob_album.id),
                "rating": "4",
                "content": "Produção impecável e viagem sônica garantida.",
            },
            follow_redirects=True,
        )
        print("• Bob adicionou álbum e review")

        alice = User.query.filter_by(username="alice").first()
        bob = User.query.filter_by(username="bob").first()

        alice_review = (
            Review.query.filter_by(user_id=alice.id)
            .order_by(Review.created_at.desc())
            .first()
        )
        bob_review = Review.query.filter_by(user_id=bob.id, album_id=bob_album.id).first()

        client.post(
            f"/reviews/{alice_review.id}/comments",
            data={"content": "Comentário massa! Concordo demais."},
            follow_redirects=True,
        )
        print("• Bob comentou na review da Alice")

        client.post(
            f"/reviews/{bob_review.id}/edit",
            data={
                "rating": "5",
                "content": "Atualizei para 5★ depois de ouvir de novo com fones.",
            },
            follow_redirects=True,
        )
        print("• Bob ajustou a review para 5★")

        client.post(
            "/chat",
            data={
                "recipient_id": str(alice.id),
                "content": "Oi Alice! A review de Loveless ficou incrível.",
            },
            follow_redirects=True,
        )
        print("• Bob enviou mensagem para Alice")

        print("\n== Resumo das ações gravadas ==")
        followers = Follow.query.all()
        for rel in followers:
            follower = User.query.get(rel.follower_id)
            following = User.query.get(rel.following_id)
            print(f"• {follower.username} segue {following.username}")

        for review in Review.query.order_by(Review.created_at.asc()):
            album = Album.query.get(review.album_id)
            user = User.query.get(review.user_id)
            print(f"• {user.username} avaliou '{album.title}' com {review.rating}★")

        for comment in ReviewComment.query.order_by(ReviewComment.created_at.asc()):
            author = User.query.get(comment.user_id)
            review = Review.query.get(comment.review_id)
            album = Album.query.get(review.album_id)
            print(
                f"• Comentário de {author.username} em '{album.title}': {comment.content}"
            )

        for message in Message.query.order_by(Message.created_at.asc()):
            sender = User.query.get(message.sender_id)
            receiver = User.query.get(message.receiver_id)
            print(f"• Mensagem {sender.username} → {receiver.username}: {message.content}")

        print("\nMock finalizado com sucesso.")


if __name__ == "__main__":
    main()
