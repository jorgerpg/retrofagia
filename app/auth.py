from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .models import User

auth_bp = Blueprint("auth", __name__, template_folder="templates")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.feed"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not email or not password:
            flash("Preencha todos os campos.", "error")
        elif password != confirm:
            flash("As senhas não coincidem.", "error")
        elif User.query.filter_by(email=email).first() or User.query.filter_by(
            username=username
        ).first():
            flash("Usuário ou email já cadastrado.", "error")
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Conta criada com sucesso. Faça login.", "success")
            return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.feed"))

    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash(f"Bem-vindo, {user.username}!", "success")
            return redirect(url_for("main.feed"))

        flash("Credenciais inválidas.", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.", "success")
    return redirect(url_for("auth.login"))
