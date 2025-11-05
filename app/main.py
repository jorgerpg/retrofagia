import time
from datetime import datetime, timezone
from itertools import chain

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import and_, func, or_

from . import db
from .models import Album, Follow, Message, Review, ReviewComment, User
from .storage import clone_image, delete_image, save_image

main_bp = Blueprint("main", __name__, template_folder="templates")


def _to_utc_iso(dt: datetime) -> str:
    """Format datetimes as ISO strings with Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed


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
        username = request.form.get("username", "").strip()
        avatar_file = request.files.get("avatar")

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
                if avatar_file and avatar_file.filename:
                    try:
                        new_avatar_path = save_image(avatar_file)
                    except ValueError as exc:
                        flash(str(exc), "error")
                        db.session.rollback()
                        db.session.refresh(current_user)
                        return redirect(url_for("main.edit_profile"))
                    else:
                        delete_image(current_user.avatar_url)
                        current_user.avatar_url = new_avatar_path
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
        cover_file = request.files.get("cover")

        if not title or not artist:
            flash("Título e artista são obrigatórios.", "error")
        else:
            cover_path = ""
            if cover_file and cover_file.filename:
                try:
                    cover_path = save_image(cover_file)
                except ValueError as exc:
                    flash(str(exc), "error")
                    return redirect(url_for("main.albums"))
            album = Album(
                title=title,
                artist=artist,
                cover_url=cover_path,
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
    delete_image(album.cover_url)
    db.session.delete(album)
    db.session.commit()
    flash("Álbum removido.", "success")
    return redirect(url_for("main.albums"))


@main_bp.route("/albums/<int:album_id>/clone", methods=["POST"])
@login_required
def clone_album(album_id):
    source_album = Album.query.get_or_404(album_id)

    if source_album.user_id == current_user.id:
        flash("Este álbum já está na sua coleção.", "info")
        return redirect(request.referrer or url_for("main.feed"))

    existing = (
        Album.query.filter_by(user_id=current_user.id)
        .filter(
            func.lower(Album.title) == source_album.title.lower(),
            func.lower(Album.artist) == source_album.artist.lower(),
        )
        .first()
    )
    if existing:
        flash("Este álbum já está na sua coleção.", "info")
        return redirect(request.referrer or url_for("main.feed"))

    cover_path = source_album.cover_url
    if cover_path:
        cover_path = clone_image(cover_path)

    cloned = Album(
        title=source_album.title,
        artist=source_album.artist,
        cover_url=cover_path,
        owner=current_user,
    )
    db.session.add(cloned)
    db.session.commit()
    flash("Álbum adicionado à sua coleção. Publique sua review no feed!", "success")
    return redirect(url_for("main.feed"))


@main_bp.route("/albums/<int:album_id>")
@login_required
def album_detail(album_id):
    album = Album.query.get_or_404(album_id)

    title_key = album.title.lower()
    artist_key = album.artist.lower()

    matching_albums = (
        Album.query.filter(
            func.lower(Album.title) == title_key,
            func.lower(Album.artist) == artist_key,
        ).all()
    )
    album_ids = [a.id for a in matching_albums] or [album.id]
    matching_albums_sorted = sorted(matching_albums, key=lambda a: a.created_at)
    canonical_album = matching_albums_sorted[0] if matching_albums_sorted else album

    reviews = (
        Review.query.filter(Review.album_id.in_(album_ids))
        .order_by(Review.created_at.desc())
        .all()
    )

    avg_rating = (
        db.session.query(func.avg(Review.rating))
        .filter(Review.album_id.in_(album_ids))
        .scalar()
    )
    avg_rating = round(float(avg_rating), 1) if avg_rating else None
    review_count = len(reviews)

    user_album = next((a for a in matching_albums if a.user_id == current_user.id), None)
    user_review = next((r for r in reviews if r.user_id == current_user.id), None)

    unique_reviewer_count = len({review.user_id for review in reviews})

    cover_url = None
    if user_album and user_album.cover_url:
        cover_url = user_album.cover_url
    elif album.cover_url:
        cover_url = album.cover_url
    else:
        for candidate in matching_albums_sorted:
            if candidate.cover_url:
                cover_url = candidate.cover_url
                break

    return render_template(
        "album_detail.html",
        album=album,
        cover_url=cover_url,
        reviews=reviews,
        avg_rating=avg_rating,
        review_count=review_count,
        user_album=user_album,
        user_review=user_review,
        unique_reviewer_count=unique_reviewer_count,
        canonical_album_id=canonical_album.id,
    )


@main_bp.route("/albums/<int:album_id>/cover", methods=["POST"])
@login_required
def update_album_cover(album_id):
    album = Album.query.filter_by(id=album_id, user_id=current_user.id).first_or_404()
    file = request.files.get("cover")

    if not file or not file.filename:
        flash("Envie uma imagem para atualizar a capa.", "error")
        return redirect(request.referrer or url_for("main.album_detail", album_id=album_id))

    try:
        new_path = save_image(file)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("main.album_detail", album_id=album_id))

    delete_image(album.cover_url)
    album.cover_url = new_path
    db.session.commit()
    flash("Capa do álbum atualizada.", "success")
    return redirect(request.referrer or url_for("main.album_detail", album_id=album_id))


@main_bp.route("/reviews/<int:review_id>/comments", methods=["POST"])
@login_required
def add_comment(review_id):
    review = Review.query.get_or_404(review_id)
    content = request.form.get("content", "").strip()

    if not content:
        flash("Digite um comentário antes de enviar.", "error")
        return redirect(request.referrer or url_for("main.feed"))

    if len(content) > 600:
        flash("O comentário pode ter no máximo 600 caracteres.", "error")
        return redirect(request.referrer or url_for("main.feed"))

    comment = ReviewComment(review_id=review.id, user_id=current_user.id, content=content)
    db.session.add(comment)
    db.session.commit()
    flash("Comentário publicado.", "success")
    return redirect(request.referrer or url_for("main.feed"))


@main_bp.route("/reviews/<int:review_id>/edit", methods=["GET", "POST"])
@login_required
def edit_review(review_id):
    review = Review.query.get_or_404(review_id)
    if review.user_id != current_user.id:
        abort(403)

    if request.method == "POST":
        rating_raw = request.form.get("rating")
        content = request.form.get("content", "").strip()

        try:
            rating_value = int(rating_raw)
        except (TypeError, ValueError):
            rating_value = None

        if rating_value is None or rating_value < 1 or rating_value > 5:
            flash("A avaliação deve ser um número entre 1 e 5.", "error")
        elif not content:
            flash("Escreva algo sobre o álbum.", "error")
        elif len(content) > 4000:
            flash("A review pode ter no máximo 4000 caracteres.", "error")
        else:
            review.rating = rating_value
            review.content = content
            db.session.commit()
            flash("Review atualizada.", "success")
            return redirect(url_for("main.album_detail", album_id=review.album_id))

    return render_template("review_edit.html", review=review)


@main_bp.route("/reviews/<int:review_id>/delete", methods=["POST"])
@login_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    if review.user_id != current_user.id:
        abort(403)

    album_id = review.album_id
    db.session.delete(review)
    db.session.commit()
    flash("Review removida.", "success")
    return redirect(request.referrer or url_for("main.album_detail", album_id=album_id))


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
        page_class="chat-page",
    )


def _collect_notifications(user: User, since: datetime | None):
    follow_query = Follow.query.filter(Follow.following_id == user.id)
    if since:
        follow_query = follow_query.filter(Follow.created_at > since)
    follow_records = follow_query.order_by(Follow.created_at.desc()).all()

    follower_ids = {record.follower_id for record in follow_records}
    followers_map = (
        {
            follower.id: follower
            for follower in User.query.filter(User.id.in_(follower_ids)).all()
        }
        if follower_ids
        else {}
    )

    followers_payload = [
        {
            "id": record.follower_id,
            "username": followers_map[record.follower_id].username,
            "avatar_url": followers_map[record.follower_id].avatar_url,
            "created_at": _to_utc_iso(record.created_at),
        }
        for record in follow_records
        if record.follower_id in followers_map
    ]

    message_query = Message.query.filter(Message.receiver_id == user.id)
    if since:
        message_query = message_query.filter(Message.created_at > since)
    message_records = message_query.order_by(Message.created_at.desc()).all()

    senders = {message.sender_id for message in message_records}
    senders_map = (
        {
            sender.id: sender
            for sender in User.query.filter(User.id.in_(senders)).all()
        }
        if senders
        else {}
    )

    latest_per_sender: dict[int, dict[str, object]] = {}
    for message in message_records:
        sender = senders_map.get(message.sender_id)
        if not sender:
            continue
        existing = latest_per_sender.get(sender.id)
        if not existing or message.created_at > existing["created_at"]:
            latest_per_sender[sender.id] = {
                "created_at": message.created_at,
                "from_user": {
                    "id": sender.id,
                    "username": sender.username,
                    "avatar_url": sender.avatar_url,
                },
                "latest_message": message.content,
            }

    messages_payload = []
    for _, entry in sorted(
        (
            (value["created_at"], value)
            for value in latest_per_sender.values()
        ),
        key=lambda pair: pair[0],
        reverse=True,
    ):
        messages_payload.append(
            {
                "from_user": entry["from_user"],
                "latest_message": entry["latest_message"],
                "created_at": _to_utc_iso(entry["created_at"]),
            }
        )

    return followers_payload, messages_payload


@main_bp.route("/api/notifications")
@login_required
def notifications_api():
    since = _parse_iso(request.args.get("since"))
    wait_for_updates = bool(request.args.get("wait", type=int))
    timeout_param = request.args.get("timeout", type=int)
    timeout_seconds = max(5, min(timeout_param if timeout_param else 30, 60))
    deadline = time.monotonic() + timeout_seconds if wait_for_updates else None

    while True:
        followers_payload, messages_payload = _collect_notifications(
            current_user, since
        )
        if (
            not wait_for_updates
            or followers_payload
            or messages_payload
            or (deadline is not None and time.monotonic() >= deadline)
        ):
            return jsonify(
                {
                    "server_time": _to_utc_iso(datetime.now(timezone.utc)),
                    "new_followers": followers_payload,
                    "new_messages": messages_payload,
                }
            )
        time.sleep(1)
        db.session.expire_all()


def _load_chat_messages(
    current_id: int, target_id: int, after_id: int | None
) -> list[Message]:
    conversation_query = Message.query.filter(
        or_(
            and_(
                Message.sender_id == current_id,
                Message.receiver_id == target_id,
            ),
            and_(
                Message.sender_id == target_id,
                Message.receiver_id == current_id,
            ),
        )
    )
    if after_id is not None:
        conversation_query = conversation_query.filter(Message.id > after_id)

    return conversation_query.order_by(Message.created_at.asc()).all()


@main_bp.route("/api/chat/<int:user_id>/messages")
@login_required
def chat_messages_api(user_id: int):
    target = User.query.get_or_404(user_id)
    allowed_ids = {
        user.id for user in chain(current_user.following, current_user.followers)
    }
    if target.id not in allowed_ids and target.id != current_user.id:
        abort(403)

    after_id = request.args.get("after", type=int)
    wait_for_updates = bool(request.args.get("wait", type=int)) and (
        after_id is not None
    )
    timeout_param = request.args.get("timeout", type=int)
    timeout_seconds = max(5, min(timeout_param if timeout_param else 30, 60))
    deadline = time.monotonic() + timeout_seconds if wait_for_updates else None

    while True:
        messages = _load_chat_messages(current_user.id, target.id, after_id)

        if messages:
            payload = [
                {
                    "id": message.id,
                    "from_me": message.sender_id == current_user.id,
                    "content": message.content,
                    "created_at": _to_utc_iso(message.created_at),
                }
                for message in messages
            ]
            return jsonify(
                {
                    "messages": payload,
                    "last_id": payload[-1]["id"],
                }
            )

        if (
            not wait_for_updates
            or (deadline is not None and time.monotonic() >= deadline)
        ):
            return jsonify({"messages": [], "last_id": after_id or 0})

        time.sleep(1)
        db.session.expire_all()


@main_bp.route("/search")
@login_required
def search():
    query = request.args.get("q", "").strip()
    filter_type = request.args.get("type", "all")
    user_results = []
    album_results = []

    if query:
        like_term = f"%{query.lower()}%"
        if filter_type in ("all", "users"):
            user_results = (
                User.query.filter(User.id != current_user.id)
                .filter(
                    or_(
                        func.lower(User.username).like(like_term),
                        func.lower(User.bio).like(like_term),
                    )
                )
                .order_by(User.username.asc())
                .limit(20)
                .all()
            )
        if filter_type in ("all", "albums"):
            album_results = (
                Album.query.join(User, Album.user_id == User.id)
                .filter(
                    or_(
                        func.lower(Album.title).like(like_term),
                        func.lower(Album.artist).like(like_term),
                    )
                )
                .order_by(Album.created_at.asc())
                .limit(40)
                .all()
            )
            unique_albums = []
            seen_keys = set()
            for album in album_results:
                key = (album.title.lower(), album.artist.lower())
                if key in seen_keys:
                    continue
                unique_albums.append(album)
                seen_keys.add(key)
            album_results = unique_albums

    owned_signatures = {
        (album.title.lower(), album.artist.lower()) for album in current_user.albums
    }

    return render_template(
        "search.html",
        query=query,
        filter_type=filter_type,
        user_results=user_results,
        album_results=album_results,
        owned_signatures=owned_signatures,
    )
