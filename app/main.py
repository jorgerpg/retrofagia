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
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import joinedload, aliased

from . import db
from .models import (
    Album,
    ChatReadState,
    Follow,
    Message,
    Review,
    ReviewComment,
    ReviewReaction,
    CommentReaction,
    User,
)
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


def _image_url(value: str | None) -> str:
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return url_for("static", filename=value)


def _review_reaction_maps(review_ids: list[int]) -> tuple[dict[int, dict[str, int]], dict[int, int]]:
    counts = {review_id: {"likes": 0, "dislikes": 0} for review_id in review_ids}
    if not review_ids:
        return counts, {}

    aggregates = (
        db.session.query(
            ReviewReaction.review_id,
            func.sum(case((ReviewReaction.value == 1, 1), else_=0)).label("likes"),
            func.sum(case((ReviewReaction.value == -1, 1), else_=0)).label("dislikes"),
        )
        .filter(ReviewReaction.review_id.in_(review_ids))
        .group_by(ReviewReaction.review_id)
        .all()
    )
    for row in aggregates:
        counts[row.review_id] = {
            "likes": int(row.likes or 0),
            "dislikes": int(row.dislikes or 0),
        }

    user_reactions = {
        row.review_id: row.value
        for row in ReviewReaction.query.filter_by(user_id=current_user.id)
        .filter(ReviewReaction.review_id.in_(review_ids))
        .all()
    }
    return counts, user_reactions


def _comment_reaction_maps(comment_ids: list[int]) -> tuple[dict[int, dict[str, int]], dict[int, int]]:
    counts = {comment_id: {"likes": 0, "dislikes": 0} for comment_id in comment_ids}
    if not comment_ids:
        return counts, {}

    aggregates = (
        db.session.query(
            CommentReaction.comment_id,
            func.sum(case((CommentReaction.value == 1, 1), else_=0)).label("likes"),
            func.sum(case((CommentReaction.value == -1, 1), else_=0)).label("dislikes"),
        )
        .filter(CommentReaction.comment_id.in_(comment_ids))
        .group_by(CommentReaction.comment_id)
        .all()
    )
    for row in aggregates:
        counts[row.comment_id] = {
            "likes": int(row.likes or 0),
            "dislikes": int(row.dislikes or 0),
        }

    user_reactions = {
        row.comment_id: row.value
        for row in CommentReaction.query.filter_by(user_id=current_user.id)
        .filter(CommentReaction.comment_id.in_(comment_ids))
        .all()
    }
    return counts, user_reactions


def _wants_json_response() -> bool:
    if request.args.get("format") == "json":
        return True
    requested_with = request.headers.get("X-Requested-With", "")
    if requested_with and requested_with.lower() == "xmlhttprequest":
        return True
    accepts = request.accept_mimetypes
    best = accepts.best or ""
    if best == "application/json":
        return True
    return accepts["application/json"] >= accepts["text/html"]


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
        Review.query.options(
            joinedload(Review.user),
            joinedload(Review.album),
            joinedload(Review.comments).joinedload(ReviewComment.user),
        )
        .join(User, Review.user_id == User.id)
        .join(Album, Review.album_id == Album.id)
        .filter(Review.user_id.in_(relevant_ids))
        .order_by(Review.created_at.desc())
        .all()
    )

    review_ids = [review.id for review in feed_reviews]
    comment_ids = [comment.id for review in feed_reviews for comment in review.comments]
    review_reaction_counts, review_user_reactions = _review_reaction_maps(review_ids)
    comment_reaction_counts, comment_user_reactions = _comment_reaction_maps(comment_ids)

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
        review_reaction_counts=review_reaction_counts,
        review_user_reactions=review_user_reactions,
        comment_reaction_counts=comment_reaction_counts,
        comment_user_reactions=comment_user_reactions,
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


@main_bp.route("/profile/edit", methods=["GET", "POST"])
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


def _profile_payload(user: User):
    reviews = (
        Review.query.options(joinedload(Review.album))
        .filter_by(user_id=user.id)
        .order_by(Review.created_at.desc())
        .all()
    )
    user_albums = (
        Album.query.filter_by(user_id=user.id)
        .order_by(Album.created_at.desc())
        .all()
    )
    follower_count = Follow.query.filter_by(following_id=user.id).count()
    following_count = Follow.query.filter_by(follower_id=user.id).count()
    return reviews, user_albums, follower_count, following_count


@main_bp.route("/profile")
@login_required
def my_profile():
    (
        reviews,
        user_albums,
        follower_count,
        following_count,
    ) = _profile_payload(current_user)
    review_ids = [review.id for review in reviews]
    review_reaction_counts, review_user_reactions = _review_reaction_maps(review_ids)
    return render_template(
        "profile_view.html",
        user=current_user,
        reviews=reviews,
        albums=user_albums,
        follower_count=follower_count,
        following_count=following_count,
        is_self=True,
        review_reaction_counts=review_reaction_counts,
        review_user_reactions=review_user_reactions,
    )


@main_bp.route("/profile/<username>")
@login_required
def view_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    (
        reviews,
        user_albums,
        follower_count,
        following_count,
    ) = _profile_payload(user)
    review_ids = [review.id for review in reviews]
    review_reaction_counts, review_user_reactions = _review_reaction_maps(review_ids)
    return render_template(
        "profile_view.html",
        user=user,
        reviews=reviews,
        albums=user_albums,
        follower_count=follower_count,
        following_count=following_count,
        is_self=current_user.id == user.id,
        review_reaction_counts=review_reaction_counts,
        review_user_reactions=review_user_reactions,
    )


@main_bp.route("/profile/<username>/collection")
@login_required
def profile_collection(username):
    user = User.query.filter_by(username=username).first_or_404()
    albums = (
        Album.query.filter_by(user_id=user.id)
        .order_by(Album.created_at.desc())
        .all()
    )
    is_self = current_user.id == user.id
    return render_template(
        "profile_collection.html",
        user=user,
        albums=albums,
        is_self=is_self,
    )


@main_bp.route("/albums")
@login_required
def albums():
    user_albums = (
        Album.query.filter_by(user_id=current_user.id)
        .order_by(Album.created_at.desc())
        .all()
    )
    return render_template("albums.html", albums=user_albums)


@main_bp.route("/albums/new", methods=["GET", "POST"])
@login_required
def create_album():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        artist = request.form.get("artist", "").strip()
        cover_file = request.files.get("cover")

        if not title or not artist:
            flash("Título e artista são obrigatórios.", "error")
            return redirect(url_for("main.create_album"))

        personal_cover_path = ""
        if cover_file and cover_file.filename:
            try:
                personal_cover_path = save_image(cover_file)
            except ValueError as exc:
                flash(str(exc), "error")
                return redirect(url_for("main.create_album"))

        title_key = title.lower()
        artist_key = artist.lower()
        matching_albums = (
            Album.query.filter(
                func.lower(Album.title) == title_key,
                func.lower(Album.artist) == artist_key,
            ).all()
        )
        existing_global_cover = next((a.cover_url for a in matching_albums if a.cover_url), "")

        album = Album(
            title=title,
            artist=artist,
            cover_url=existing_global_cover,
            personal_cover_url=personal_cover_path,
            owner=current_user,
        )
        db.session.add(album)
        db.session.commit()

        if not existing_global_cover and personal_cover_path:
            global_cover = clone_image(personal_cover_path) or personal_cover_path
            for entry in matching_albums + [album]:
                entry.cover_url = global_cover
            db.session.commit()

        flash("Álbum adicionado à sua coleção.", "success")
        return redirect(url_for("main.albums"))

    return render_template("album_new.html")


@main_bp.route("/api/albums/search")
@login_required
def album_search_api():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify(results=[])

    like_query = f"%{query}%"
    owned_pairs = {
        (title.lower(), artist.lower())
        for title, artist in db.session.query(Album.title, Album.artist)
        .filter(Album.user_id == current_user.id)
        .all()
    }

    matches = (
        Album.query.filter(
            or_(
                Album.title.ilike(like_query),
                Album.artist.ilike(like_query),
            )
        )
        .order_by(Album.created_at.desc())
        .limit(40)
        .all()
    )

    seen = set()
    results = []
    for album in matches:
        key = (album.title.lower(), album.artist.lower())
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "id": album.id,
                "title": album.title,
                "artist": album.artist,
                "cover_url": _image_url(album.cover_url),
                "already_owned": key in owned_pairs,
            }
        )
        if len(results) >= 10:
            break

    return jsonify(results=results)


@main_bp.route("/albums/<int:album_id>/delete", methods=["POST"])
@login_required
def delete_album(album_id):
    album = Album.query.filter_by(id=album_id, user_id=current_user.id).first()
    if not album:
        abort(404)
    delete_image(album.personal_cover_url)
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
        return redirect(url_for("main.album_detail", album_id=source_album.id))

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
        return redirect(url_for("main.album_detail", album_id=existing.id))

    cloned = Album(
        title=source_album.title,
        artist=source_album.artist,
        cover_url=source_album.cover_url,
        personal_cover_url="",
        owner=current_user,
    )
    db.session.add(cloned)
    db.session.commit()
    flash("Álbum adicionado à sua coleção. Publique sua review no feed!", "success")
    return redirect(url_for("main.album_detail", album_id=cloned.id))


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
        Review.query.options(
            joinedload(Review.user),
            joinedload(Review.comments).joinedload(ReviewComment.user),
        )
        .filter(Review.album_id.in_(album_ids))
        .order_by(Review.created_at.desc())
        .all()
    )

    review_ids = [review.id for review in reviews]
    comment_ids = [comment.id for review in reviews for comment in review.comments]
    review_reaction_counts, review_user_reactions = _review_reaction_maps(review_ids)
    comment_reaction_counts, comment_user_reactions = _comment_reaction_maps(comment_ids)

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
    if canonical_album.cover_url:
        cover_url = canonical_album.cover_url
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
        review_reaction_counts=review_reaction_counts,
        review_user_reactions=review_user_reactions,
        comment_reaction_counts=comment_reaction_counts,
        comment_user_reactions=comment_user_reactions,
    )


@main_bp.route("/albums/<int:album_id>/cover", methods=["POST"])
@login_required
def update_album_cover(album_id):
    scope = request.form.get("scope", "personal")
    file = request.files.get("cover")

    if not file or not file.filename:
        flash("Envie uma imagem para atualizar a capa.", "error")
        return redirect(request.referrer or url_for("main.album_detail", album_id=album_id))

    try:
        new_path = save_image(file)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("main.album_detail", album_id=album_id))

    if scope == "global":
        album = Album.query.get_or_404(album_id)
        if not current_user.is_admin:
            delete_image(new_path)
            abort(403)
        normalized_title = album.title.strip().lower()
        normalized_artist = album.artist.strip().lower()
        matching_albums = (
            Album.query.filter(
                func.lower(Album.title) == normalized_title,
                func.lower(Album.artist) == normalized_artist,
            ).all()
        )
        for entry in matching_albums:
            delete_image(entry.cover_url)
            entry.cover_url = new_path
        db.session.commit()
        flash("Capa global atualizada para todos.", "success")
        target_id = album_id
    else:
        album = Album.query.filter_by(id=album_id, user_id=current_user.id).first()
        if not album:
            delete_image(new_path)
            abort(403)
        delete_image(album.personal_cover_url)
        album.personal_cover_url = new_path

        normalized_title = album.title.strip().lower()
        normalized_artist = album.artist.strip().lower()
        matching_albums = (
            Album.query.filter(
                func.lower(Album.title) == normalized_title,
                func.lower(Album.artist) == normalized_artist,
            ).all()
        )
        canonical_album = (
            sorted(matching_albums, key=lambda a: a.created_at)[0]
            if matching_albums
            else album
        )
        if not canonical_album.cover_url:
            global_clone = clone_image(new_path) or new_path
            for entry in matching_albums:
                entry.cover_url = global_clone
        db.session.commit()
        flash("Capa da sua coleção atualizada.", "success")
        target_id = album_id

    return redirect(request.referrer or url_for("main.album_detail", album_id=target_id))


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
    if not current_user.is_admin and review.user_id != current_user.id:
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


@main_bp.route("/reviews/<int:review_id>")
@login_required
def view_review(review_id):
    review = (
        Review.query.options(
            joinedload(Review.user),
            joinedload(Review.album),
            joinedload(Review.comments).joinedload(ReviewComment.user),
        )
        .get_or_404(review_id)
    )
    review_reaction_counts, review_user_reactions = _review_reaction_maps([review.id])
    comment_ids = [comment.id for comment in review.comments]
    comment_reaction_counts, comment_user_reactions = _comment_reaction_maps(comment_ids)
    return render_template(
        "review_view.html",
        review=review,
        review_reaction_counts=review_reaction_counts,
        review_user_reactions=review_user_reactions,
        comment_reaction_counts=comment_reaction_counts,
        comment_user_reactions=comment_user_reactions,
    )


@main_bp.route("/reviews/<int:review_id>/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(review_id, comment_id):
    comment = (
        ReviewComment.query.filter_by(id=comment_id, review_id=review_id)
        .options(joinedload(ReviewComment.review))
        .first_or_404()
    )
    review = comment.review
    if (
        not current_user.is_admin
        and comment.user_id != current_user.id
        and review.user_id != current_user.id
    ):
        abort(403)

    db.session.delete(comment)
    db.session.commit()
    flash("Comentário removido.", "success")
    return redirect(request.referrer or url_for("main.feed"))


@main_bp.route("/reviews/<int:review_id>/react", methods=["POST"])
@login_required
def react_review(review_id):
    review = Review.query.get_or_404(review_id)
    action = request.form.get("action")
    if action not in {"like", "dislike"}:
        abort(400)

    value = 1 if action == "like" else -1
    reaction = ReviewReaction.query.filter_by(
        review_id=review.id, user_id=current_user.id
    ).first()

    if reaction and reaction.value == value:
        db.session.delete(reaction)
    else:
        if reaction:
            reaction.value = value
        else:
            reaction = ReviewReaction(
                review_id=review.id,
                user_id=current_user.id,
                value=value,
            )
            db.session.add(reaction)

    db.session.commit()
    if _wants_json_response():
        counts, user_map = _review_reaction_maps([review.id])
        payload = {
            "target_type": "review",
            "target_id": review.id,
            "likes": counts.get(review.id, {}).get("likes", 0),
            "dislikes": counts.get(review.id, {}).get("dislikes", 0),
            "user_reaction": user_map.get(review.id),
        }
        return jsonify(payload)
    return redirect(request.referrer or url_for("main.feed"))


@main_bp.route(
    "/reviews/<int:review_id>/comments/<int:comment_id>/react", methods=["POST"]
)
@login_required
def react_comment(review_id, comment_id):
    comment = (
        ReviewComment.query.filter_by(id=comment_id, review_id=review_id)
        .options(joinedload(ReviewComment.review))
        .first_or_404()
    )
    action = request.form.get("action")
    if action not in {"like", "dislike"}:
        abort(400)

    value = 1 if action == "like" else -1
    reaction = CommentReaction.query.filter_by(
        comment_id=comment.id, user_id=current_user.id
    ).first()

    if reaction and reaction.value == value:
        db.session.delete(reaction)
    else:
        if reaction:
            reaction.value = value
        else:
            reaction = CommentReaction(
                comment_id=comment.id,
                user_id=current_user.id,
                value=value,
            )
            db.session.add(reaction)

    db.session.commit()
    if _wants_json_response():
        counts, user_map = _comment_reaction_maps([comment.id])
        payload = {
            "target_type": "comment",
            "target_id": comment.id,
            "likes": counts.get(comment.id, {}).get("likes", 0),
            "dislikes": counts.get(comment.id, {}).get("dislikes", 0),
            "user_reaction": user_map.get(comment.id),
        }
        return jsonify(payload)
    return redirect(request.referrer or url_for("main.feed"))


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
    redirect_to = request.form.get("redirect_to")
    if redirect_to == "albums":
        return redirect(url_for("main.albums"))
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
            if conversation:
                last_incoming = [
                    (message.id, message.created_at)
                    for message in conversation
                    if message.sender_id == selected_user.id
                ]
                if last_incoming:
                    last_incoming_id, last_incoming_at = max(
                        last_incoming, key=lambda item: item[1]
                    )
                    _mark_messages_as_read(
                        current_user.id,
                        selected_user.id,
                        last_incoming_id,
                        last_incoming_at,
                    )

    contacts_map = {}
    for user in chain(current_user.following, current_user.followers):
        contacts_map[user.id] = user
    contact_ids = list(contacts_map.keys())

    last_activity = {}
    if contact_ids:
        other_id = case(
            (Message.sender_id == current_user.id, Message.receiver_id),
            else_=Message.sender_id,
        )
        last_rows = (
            db.session.query(other_id.label("contact_id"), func.max(Message.created_at))
            .filter(
                or_(
                    Message.sender_id == current_user.id,
                    Message.receiver_id == current_user.id,
                ),
                or_(
                    Message.sender_id.in_(contact_ids),
                    Message.receiver_id.in_(contact_ids),
                ),
            )
            .group_by("contact_id")
            .all()
        )
        last_activity = {row.contact_id: row[1] for row in last_rows}

    contacts = sorted(
        contacts_map.values(),
        key=lambda u: (
            last_activity.get(u.id) or datetime.min,
            u.username.lower(),
        ),
        reverse=True,
    )

    return render_template(
        "chat.html",
        contacts=contacts,
        selected_user=selected_user,
        conversation=conversation,
        unread_counts=_get_unread_counts(current_user.id, {user.id for user in contacts}),
        contact_last_activity=last_activity,
        page_class="chat-page",
    )


def _mark_messages_as_read(
    user_id: int,
    contact_id: int,
    last_message_id: int | None,
    last_message_at: datetime | None,
) -> None:
    if not last_message_id:
        return
    state = ChatReadState.query.filter_by(user_id=user_id, contact_id=contact_id).first()
    if not state:
        state = ChatReadState(
            user_id=user_id,
            contact_id=contact_id,
            last_read_message_id=0,
        )
        db.session.add(state)
    if state.last_read_message_id is None:
        state.last_read_message_id = 0
    if last_message_id <= state.last_read_message_id:
        if not state.last_read_at and last_message_at:
            state.last_read_at = last_message_at
            db.session.commit()
        return
    state.last_read_message_id = last_message_id
    if last_message_at is None:
        message = Message.query.get(last_message_id)
        last_message_at = message.created_at if message else None
    if last_message_at:
        state.last_read_at = last_message_at
    db.session.commit()


def _get_unread_counts(user_id: int, sender_ids: set[int] | None = None) -> dict[int, int]:
    if sender_ids is not None and not sender_ids:
        return {}
    state_alias = aliased(ChatReadState)
    epoch = datetime(1970, 1, 1)
    query = (
        db.session.query(
            Message.sender_id.label("sender_id"),
            func.count(Message.id).label("unread_count"),
        )
        .outerjoin(
            state_alias,
            and_(
                state_alias.user_id == user_id,
                state_alias.contact_id == Message.sender_id,
            ),
        )
        .filter(Message.receiver_id == user_id)
        .filter(
            or_(
                state_alias.last_read_at.is_(None),
                Message.created_at > func.coalesce(state_alias.last_read_at, epoch),
            )
        )
    )
    if sender_ids is not None:
        query = query.filter(Message.sender_id.in_(sender_ids))
    unread_rows = query.group_by(Message.sender_id).all()
    return {row.sender_id: int(row.unread_count) for row in unread_rows}


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

    unread_counts_all = _get_unread_counts(user.id)
    total_unread = sum(unread_counts_all.values())

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
                "unread_count": unread_counts_all.get(entry["from_user"]["id"], 0),
            }
        )

    return followers_payload, messages_payload, total_unread


@main_bp.route("/api/notifications")
@login_required
def notifications_api():
    since = _parse_iso(request.args.get("since"))
    wait_for_updates = bool(request.args.get("wait", type=int))
    timeout_param = request.args.get("timeout", type=int)
    timeout_seconds = max(5, min(timeout_param if timeout_param else 30, 60))
    deadline = time.monotonic() + timeout_seconds if wait_for_updates else None
    known_unread = request.args.get("unread_snapshot", type=int)

    while True:
        (
            followers_payload,
            messages_payload,
            total_unread_messages,
        ) = _collect_notifications(
            current_user, since
        )
        unread_changed = (
            known_unread is not None and known_unread != total_unread_messages
        )
        if (
            not wait_for_updates
            or followers_payload
            or messages_payload
            or unread_changed
            or (deadline is not None and time.monotonic() >= deadline)
        ):
            return jsonify(
                {
                    "server_time": _to_utc_iso(datetime.now(timezone.utc)),
                    "new_followers": followers_payload,
                    "new_messages": messages_payload,
                    "total_unread_messages": total_unread_messages,
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
    is_active = bool(request.args.get("active", type=int))
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
            last_incoming = [
                (message.id, message.created_at)
                for message in messages
                if message.sender_id == target.id
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


@main_bp.route("/api/chat/<int:user_id>/read", methods=["POST"])
@login_required
def chat_mark_read_api(user_id: int):
    target = User.query.get_or_404(user_id)
    allowed_ids = {
        user.id for user in chain(current_user.following, current_user.followers)
    }
    if target.id not in allowed_ids and target.id != current_user.id:
        abort(403)

    data = request.get_json(silent=True) or {}
    last_id = data.get("last_message_id")
    last_at_raw = data.get("last_message_at")
    last_at = _parse_iso(last_at_raw)

    if not last_id:
        latest = (
            Message.query.filter(
                or_(
                    and_(
                        Message.sender_id == current_user.id,
                        Message.receiver_id == target.id,
                    ),
                    and_(
                        Message.sender_id == target.id,
                        Message.receiver_id == current_user.id,
                    ),
                )
            )
            .order_by(Message.id.desc())
            .first()
        )
        if latest:
            last_id = latest.id
            last_at = latest.created_at

    if not last_id:
        return jsonify({"status": "noop"})

    _mark_messages_as_read(current_user.id, target.id, last_id, last_at)
    return jsonify({"status": "ok"})


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
