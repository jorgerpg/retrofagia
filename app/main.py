from itertools import chain

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import and_, or_

from . import db
from .models import Album, Follow, Message, Review, User

main_bp = Blueprint("main", __name__, template_folder="templates")


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.feed"))
    return redirect(url_for("auth.login"))


@main_bp.route("/feed", methods=["GET", "POST"])
@login_required
def feed():
    if request.method == "POST":
        album_id_raw = request.form.get("album_id")
        rating_raw = request.form.get("rating")
        content = request.form.get("content", "").strip()

        if not album_id_raw or not rating_raw or not content:
            flash("Selecione um álbum, avaliação e escreva uma review.", "error")
        else:
            try:
                album_id = int(album_id_raw)
            except (TypeError, ValueError):
                album_id = None

            album = (
                Album.query.filter_by(id=album_id, user_id=current_user.id).first()
                if album_id
                else None
            )
            if not album:
                flash("Álbum inválido para review.", "error")
            else:
                try:
                    rating_value = int(rating_raw)
                except ValueError:
                    flash("A avaliação deve ser um número inteiro.", "error")
                else:
                    if rating_value < 1 or rating_value > 5:
                        flash("A avaliação deve ser entre 1 e 5 estrelas.", "error")
                    else:
                        review = Review.query.filter_by(
                            user_id=current_user.id, album_id=album.id
                        ).first()
                        if review:
                            review.rating = rating_value
                            review.content = content
                            flash("Review atualizada.", "success")
                        else:
                            review = Review(
                                user_id=current_user.id,
                                album_id=album.id,
                                rating=rating_value,
                                content=content,
                            )
                            db.session.add(review)
                            flash("Review criada!", "success")
                        db.session.commit()

    followed_ids = [user.id for user in current_user.following]
    relevant_ids = list(set(chain(followed_ids, [current_user.id])))

    feed_reviews = (
        Review.query.join(User, Review.user_id == User.id)
        .join(Album, Review.album_id == Album.id)
        .filter(Review.user_id.in_(relevant_ids))
        .order_by(Review.created_at.desc())
        .all()
    )

    suggested_users = (
        User.query.filter(User.id != current_user.id)
        .filter(~User.followers.any(id=current_user.id))
        .order_by(User.created_at.desc())
        .limit(6)
        .all()
    )

    return render_template(
        "feed.html",
        reviews=feed_reviews,
        albums=current_user.albums,
        suggested_users=suggested_users,
    )


@main_bp.route("/follow/<username>", methods=["POST"])
@login_required
def follow_user(username):
    target = User.query.filter_by(username=username).first_or_404()
    if target.id == current_user.id:
        flash("Você não pode seguir a si mesmo.", "error")
        return redirect(request.referrer or url_for("main.feed"))

    if current_user.is_following(target):
        Follow.query.filter_by(
            follower_id=current_user.id, following_id=target.id
        ).delete()
        db.session.commit()
        flash(f"Você deixou de seguir {target.username}.", "success")
    else:
        follow = Follow(follower_id=current_user.id, following_id=target.id)
        db.session.add(follow)
        db.session.commit()
        flash(f"Agora você segue {target.username}.", "success")

    return redirect(request.referrer or url_for("main.feed"))


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        bio = request.form.get("bio", "").strip()
        avatar_url = request.form.get("avatar_url", "").strip()
        username = request.form.get("username", "").strip()

        if not username:
            flash("O nome de usuário é obrigatório.", "error")
        else:
            existing_user = User.query.filter(
                User.username == username, User.id != current_user.id
            ).first()
            if existing_user:
                flash("Esse nome de usuário já está em uso.", "error")
            else:
                current_user.username = username
                current_user.bio = bio
                current_user.avatar_url = avatar_url
                db.session.commit()
                flash("Perfil atualizado.", "success")

    return render_template("profile_edit.html")


@main_bp.route("/profile/<username>")
@login_required
def view_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    reviews = (
        Review.query.filter_by(user_id=user.id)
        .join(Album)
        .order_by(Review.created_at.desc())
        .all()
    )
    return render_template("profile_view.html", user=user, reviews=reviews)


@main_bp.route("/albums", methods=["GET", "POST"])
@login_required
def albums():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        artist = request.form.get("artist", "").strip()
        cover_url = request.form.get("cover_url", "").strip()

        if not title or not artist:
            flash("Título e artista são obrigatórios.", "error")
        else:
            album = Album(
                title=title,
                artist=artist,
                cover_url=cover_url,
                owner=current_user,
            )
            db.session.add(album)
            db.session.commit()
            flash("Álbum adicionado à sua coleção.", "success")

    user_albums = (
        Album.query.filter_by(user_id=current_user.id)
        .order_by(Album.created_at.desc())
        .all()
    )
    return render_template("albums.html", albums=user_albums)


@main_bp.route("/albums/<int:album_id>/delete", methods=["POST"])
@login_required
def delete_album(album_id):
    album = Album.query.filter_by(id=album_id, user_id=current_user.id).first()
    if not album:
        abort(404)
    db.session.delete(album)
    db.session.commit()
    flash("Álbum removido.", "success")
    return redirect(url_for("main.albums"))


@main_bp.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    if request.method == "POST":
        recipient_id = request.form.get("recipient_id")
        content = request.form.get("content", "").strip()

        if not recipient_id or not content:
            flash("Selecione um destinatário e escreva uma mensagem.", "error")
            return redirect(url_for("main.chat", with_user=recipient_id or ""))

        recipient = User.query.get(recipient_id)
        if not recipient:
            flash("Usuário não encontrado.", "error")
            return redirect(url_for("main.chat"))

        allowed_ids = {
            user.id for user in chain(current_user.following, current_user.followers)
        }
        if recipient.id not in allowed_ids and recipient.id != current_user.id:
            flash("Você só pode enviar mensagens para seguidores ou seguidos.", "error")
            return redirect(url_for("main.chat"))

        message = Message(
            sender_id=current_user.id,
            receiver_id=recipient.id,
            content=content,
        )
        db.session.add(message)
        db.session.commit()
        flash("Mensagem enviada.", "success")
        return redirect(url_for("main.chat", with_user=recipient.id))

    raw_recipient = request.args.get("with_user")
    selected_user = None
    conversation = []

    if raw_recipient:
        try:
            recipient_id = int(raw_recipient)
        except (TypeError, ValueError):
            recipient_id = None
        if recipient_id:
            selected_user = User.query.filter_by(id=recipient_id).first()
        if selected_user:
            conversation = (
                Message.query.filter(
                    or_(
                        and_(
                            Message.sender_id == current_user.id,
                            Message.receiver_id == selected_user.id,
                        ),
                        and_(
                            Message.sender_id == selected_user.id,
                            Message.receiver_id == current_user.id,
                        ),
                    )
                )
                .order_by(Message.created_at.asc())
                .all()
            )

    contacts_map = {}
    for user in chain(current_user.following, current_user.followers):
        contacts_map[user.id] = user
    contacts = sorted(contacts_map.values(), key=lambda u: u.username.lower())

    return render_template(
        "chat.html",
        contacts=contacts,
        selected_user=selected_user,
        conversation=conversation,
    )
