import os
import uuid
from datetime import datetime
from typing import Dict, Any

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_from_directory,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'foodhopper.db')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
    return app


app = create_app()
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_vendor = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    places = db.relationship("Place", backref="creator", lazy=True)
    reviews = db.relationship("Review", backref="author", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Place(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cuisine_types = db.Column(db.String(300), nullable=True)
    diet_options = db.Column(db.String(200), nullable=True)
    price_min = db.Column(db.Integer, nullable=True)
    price_max = db.Column(db.Integer, nullable=True)
    hours = db.Column(db.String(200), nullable=True)
    contact_info = db.Column(db.String(200), nullable=True)
    menu_url = db.Column(db.String(300), nullable=True)

    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    photos = db.relationship("PlaceImage", backref="place", cascade="all,delete", lazy=True)
    reviews = db.relationship("Review", backref="place", cascade="all,delete", lazy=True)

    def to_dict(self, include_reviews: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cuisine_types": self.cuisine_types or "",
            "diet_options": self.diet_options or "",
            "price_min": self.price_min,
            "price_max": self.price_max,
            "hours": self.hours,
            "contact_info": self.contact_info,
            "menu_url": self.menu_url,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "photo_urls": [url_for("uploaded_file", filename=img.file_name) for img in self.photos],
            "avg_rating": round(sum([r.rating for r in self.reviews]) / len(self.reviews), 2) if self.reviews else None,
            "like_count": Like.query.filter_by(place_id=self.id).count(),
            "favorite_count": Favorite.query.filter_by(place_id=self.id).count(),
        }
        if include_reviews:
            data["reviews"] = [r.to_dict() for r in self.reviews]
        return data


class PlaceImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=True)
    cost = db.Column(db.Integer, nullable=True)
    image_file = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.author.name if self.author else None,
            "place_id": self.place_id,
            "rating": self.rating,
            "text": self.text,
            "cost": self.cost,
            "image_url": url_for("uploaded_file", filename=self.image_file) if self.image_file else None,
            "created_at": self.created_at.isoformat(),
        }


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "place_id", name="uq_favorite"),)


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "place_id", name="uq_like"),)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"]) 
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        # Admin shortcut
        if email == "admin" and password == "admin":
            session["is_admin"] = True
            flash("Logged in as admin.", "success")
            return redirect(url_for("admin_dashboard"))
        # Normal user flow
        user = User.query.filter_by(email=email.lower()).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Logged in successfully.", "success")
            return redirect(url_for("index"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"]) 
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        is_vendor = request.form.get("is_vendor") == "on"

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return render_template("register.html")

        user = User(name=name, email=email, is_vendor=is_vendor)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Account created.", "success")
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("index"))


@app.route("/vendor", methods=["GET"]) 
@login_required
def vendor_portal():
    if not current_user.is_vendor:
        flash("Vendor access required.", "warning")
        return redirect(url_for("index"))
    my_places = Place.query.filter_by(created_by=current_user.id).all()
    return render_template("vendor.html", places=my_places)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ---------- Admin ----------

def require_admin():
    if not session.get("is_admin"):
        flash("Admin access required.", "warning")
        return False
    return True


@app.route("/admin")
def admin_dashboard():
    if not require_admin():
        return redirect(url_for("login"))
    places = Place.query.order_by(Place.created_at.desc()).all()
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template("admin.html", places=places, reviews=reviews)


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Admin logged out.", "info")
    return redirect(url_for("index"))


@app.route("/admin/place/<int:place_id>/delete", methods=["POST"]) 
def admin_delete_place(place_id: int):
    if not require_admin():
        return redirect(url_for("login"))
    place = db.session.get(Place, place_id)
    if not place:
        flash("Place not found.", "danger")
        return redirect(url_for("admin_dashboard"))
    # Delete associated likes/favorites
    Like.query.filter_by(place_id=place_id).delete()
    Favorite.query.filter_by(place_id=place_id).delete()
    # Delete place images (files)
    for img in place.photos:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], img.file_name))
        except Exception:
            pass
    # Delete review images (files)
    for rev in place.reviews:
        if rev.image_file:
            try:
                os.remove(os.path.join(app.config["UPLOAD_FOLDER"], rev.image_file))
            except Exception:
                pass
    db.session.delete(place)
    db.session.commit()
    flash("Place deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/review/<int:review_id>/delete", methods=["POST"]) 
def admin_delete_review(review_id: int):
    if not require_admin():
        return redirect(url_for("login"))
    review = db.session.get(Review, review_id)
    if not review:
        flash("Review not found.", "danger")
        return redirect(url_for("admin_dashboard"))
    if review.image_file:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], review.image_file))
        except Exception:
            pass
    db.session.delete(review)
    db.session.commit()
    flash("Review deleted.", "success")
    return redirect(url_for("admin_dashboard"))


# ---------- API ----------


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@app.route("/api/places", methods=["GET"]) 
def api_list_places():
    cuisine = request.args.get("cuisine")
    diet = request.args.get("diet")
    price_min = request.args.get("price_min", type=int)
    price_max = request.args.get("price_max", type=int)

    q = Place.query
    if cuisine:
        for kw in [c.strip().lower() for c in cuisine.split(",") if c.strip()]:
            q = q.filter(Place.cuisine_types.ilike(f"%{kw}%"))
    if diet:
        for dw in [d.strip().lower() for d in diet.split(",") if d.strip()]:
            q = q.filter(Place.diet_options.ilike(f"%{dw}%"))
    if price_min is not None:
        q = q.filter((Place.price_min == None) | (Place.price_min >= price_min))  # noqa: E711
    if price_max is not None:
        q = q.filter((Place.price_max == None) | (Place.price_max <= price_max))  # noqa: E711

    places = q.order_by(Place.created_at.desc()).all()
    return jsonify([p.to_dict() for p in places])


@app.route("/api/places", methods=["POST"]) 
@login_required
def api_create_place():
    data = request.form
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    try:
        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))
    except (TypeError, ValueError):
        return jsonify({"error": "Valid latitude and longitude required"}), 400

    place = Place(
        name=name,
        description=data.get("description"),
        cuisine_types=(data.get("cuisine_types") or "").lower(),
        diet_options=(data.get("diet_options") or "").lower(),
        price_min=(int(data.get("price_min")) if data.get("price_min") else None),
        price_max=(int(data.get("price_max")) if data.get("price_max") else None),
        hours=data.get("hours"),
        contact_info=data.get("contact_info"),
        menu_url=data.get("menu_url"),
        latitude=latitude,
        longitude=longitude,
        created_by=current_user.id,
    )
    db.session.add(place)
    db.session.flush()

    if "photos" in request.files:
        files = request.files.getlist("photos")
        for f in files:
            if not f or f.filename == "":
                continue
            if _allowed_file(f.filename):
                filename = secure_filename(f.filename)
                ext = filename.rsplit(".", 1)[1].lower()
                final_name = f"place_{place.id}_{uuid.uuid4().hex}.{ext}"
                f.save(os.path.join(app.config["UPLOAD_FOLDER"], final_name))
                db.session.add(PlaceImage(place_id=place.id, file_name=final_name))

    db.session.commit()
    return jsonify(place.to_dict(include_reviews=True)), 201


@app.route("/api/places/<int:place_id>", methods=["GET"]) 
def api_get_place(place_id: int):
    place = db.session.get(Place, place_id)
    if not place:
        return jsonify({"error": "Not found"}), 404
    return jsonify(place.to_dict(include_reviews=True))


@app.route("/api/places/<int:place_id>/review", methods=["POST"]) 
@login_required
def api_add_review(place_id: int):
    place = db.session.get(Place, place_id)
    if not place:
        return jsonify({"error": "Place not found"}), 404
    rating = request.form.get("rating", type=int)
    if not rating or rating < 1 or rating > 5:
        return jsonify({"error": "Rating 1-5 required"}), 400

    review = Review(
        user_id=current_user.id,
        place_id=place.id,
        rating=rating,
        text=request.form.get("text"),
        cost=request.form.get("cost", type=int),
    )

    if "image" in request.files:
        f = request.files["image"]
        if f and _allowed_file(f.filename):
            filename = secure_filename(f.filename)
            ext = filename.rsplit(".", 1)[1].lower()
            final_name = f"review_{place.id}_{current_user.id}_{uuid.uuid4().hex}.{ext}"
            f.save(os.path.join(app.config["UPLOAD_FOLDER"], final_name))
            review.image_file = final_name

    db.session.add(review)
    db.session.commit()
    return jsonify(review.to_dict()), 201


@app.route("/api/places/<int:place_id>/favorite", methods=["POST"]) 
@login_required
def api_favorite(place_id: int):
    place = db.session.get(Place, place_id)
    if not place:
        return jsonify({"error": "Place not found"}), 404
    action = request.json.get("action") if request.is_json else request.form.get("action")
    fav = Favorite.query.filter_by(user_id=current_user.id, place_id=place_id).first()
    if action == "remove":
        if fav:
            db.session.delete(fav)
            db.session.commit()
        return jsonify({"status": "removed", "favorite_count": Favorite.query.filter_by(place_id=place_id).count()})
    if not fav:
        fav = Favorite(user_id=current_user.id, place_id=place_id)
        db.session.add(fav)
        db.session.commit()
    return jsonify({"status": "added", "favorite_count": Favorite.query.filter_by(place_id=place_id).count()})


@app.route("/api/places/<int:place_id>/like", methods=["POST"]) 
@login_required
def api_like(place_id: int):
    place = db.session.get(Place, place_id)
    if not place:
        return jsonify({"error": "Place not found"}), 404
    existing = Like.query.filter_by(user_id=current_user.id, place_id=place_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"status": "unliked", "like_count": Like.query.filter_by(place_id=place_id).count()})
    like = Like(user_id=current_user.id, place_id=place_id)
    db.session.add(like)
    db.session.commit()
    return jsonify({"status": "liked", "like_count": Like.query.filter_by(place_id=place_id).count()})


@app.context_processor
def inject_globals():
    return {"current_user": current_user, "is_admin": session.get("is_admin", False)}


def _init_db():
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    _init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
