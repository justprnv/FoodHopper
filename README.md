## FoodHopper

Discover, add, and review local food spots on an interactive map. FoodHopper lets anyone explore places, filter by cuisine/price/diet, add new spots with photos, post reviews, and like/favorite places. Vendors get a simple portal to see their listings, and there’s a lightweight admin dashboard.

### Features
- **Interactive map**: Browse places on a Leaflet + OpenStreetMap map with saved view state.
- **Filtering**: Filter by **cuisines**, **dietary options**, and **price range**.
- **Add places**: Authenticated users can add places with photos, details, and map-picked coordinates.
- **Photos**: Multiple image uploads per place; images are served from `uploads/`.
- **Reviews**: Post rating (1–5), cost, text, and optional image per review.
- **Likes & favorites**: Toggle likes; add/remove favorites.
- **Directions**: One-click routing from your current location to a place.
- **Vendor portal**: Registered vendors can view their added places.
- **Admin dashboard**: View and delete any place or review. Quick demo login.

### Tech stack
- **Backend**: Flask, Flask-Login, Flask-SQLAlchemy, SQLite (default)
- **Frontend**: Bootstrap 5, Leaflet, Leaflet Routing Machine

## Quick start (Windows PowerShell)
Prerequisites: Python 3.10+ recommended

1) Clone or open the folder in your environment, then in PowerShell in the project root run:
```
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

2) [Optional] Create a `.env` (same folder as `app.py`) to override defaults:
```
SECRET_KEY=replace-me
DATABASE_URL=sqlite:///foodhopper.db
PORT=5000
```

3) Run the app:
```
python app.py
```

4) Open `http://127.0.0.1:5000` in your browser.

### Logins
- **Admin (demo)**: Use the normal login page with email `admin` and password `admin` to access the Admin dashboard. Do not use this in production.
- **User**: Register normally on the Sign Up page. Check “I am a vendor” to enable the vendor portal.

## How it works
- On first run, the app auto-creates the SQLite database file `foodhopper.db` and tables.
- Image uploads (place and review photos) are stored in `uploads/` and served via `/uploads/<filename>`.
- Default server is `http://0.0.0.0:5000` (accessible at `http://127.0.0.1:5000`).

## Project structure
```
FoodHopper/
  app.py                 # Flask app, models, routes, APIs
  foodhopper.db          # SQLite DB (created on first run)
  requirements.txt       # Python dependencies
  static/                # Frontend assets
    css/styles.css
    js/main.js
  templates/             # Jinja templates
    base.html, index.html, login.html, register.html, admin.html, vendor.html
  uploads/               # Image uploads (created/used at runtime)
```

## Key routes
- **Pages**
  - `/` home with map, filters, add-place modal, place details modal
  - `/login`, `/register`, `/logout`
  - `/vendor` vendor portal (requires vendor user)
  - `/admin` admin dashboard (requires admin session)
- **Static uploads**
  - `/uploads/<filename>` serves images from `uploads/`

## API endpoints
- `GET /api/places`
  - Query params: `cuisine`, `diet`, `price_min`, `price_max`
  - Returns: list of places with photo URLs and counts

- `POST /api/places` (auth required)
  - Form fields: `name` (required), `description`, `cuisine_types`, `diet_options`, `price_min`, `price_max`, `hours`, `contact_info`, `menu_url`, `latitude` (required), `longitude` (required)
  - Files: `photos` (one or many), allowed: png, jpg, jpeg, gif, webp

- `GET /api/places/<id>`
  - Returns a place with photos, counts, and reviews

- `POST /api/places/<id>/review` (auth required)
  - Form fields: `rating` (1–5, required), `text`, `cost`
  - File: `image` (optional)

- `POST /api/places/<id>/favorite` (auth required)
  - Body/form: `action`=`remove` to remove; omit or other to add
  - Returns updated `favorite_count`

- `POST /api/places/<id>/like` (auth required)
  - Toggles like; returns updated `like_count`

### Example curl (after logging in via browser to set a session cookie)
Note: Replace `<cookie>` with your session cookie (from browser devtools) if calling auth endpoints from curl.
```
curl "http://127.0.0.1:5000/api/places?cuisine=pizza&price_max=20"

curl -X POST \
  -H "Cookie: session=<cookie>" \
  -F "name=Test Pizza" \
  -F "latitude=40.7128" \
  -F "longitude=-74.0060" \
  -F "photos=@path/to/photo.jpg" \
  http://127.0.0.1:5000/api/places
```

## Configuration
Environment variables (via real env or `.env`):
- `SECRET_KEY` session secret; default `dev-secret-change`
- `DATABASE_URL` SQLAlchemy URL; default `sqlite:///foodhopper.db`
- `PORT` server port; default `5000`

Other limits and settings:
- Max upload size: 32 MB total per request
- Allowed images: `png, jpg, jpeg, gif, webp`

## Troubleshooting
- "No module named flask": Ensure your venv is activated and `pip install -r requirements.txt` succeeded.
- Port already in use: Set `PORT` to a free port and re-run.
- Database issues: Stop the app, remove `foodhopper.db` if you want a clean slate, and restart (will recreate tables). Note this deletes data.
- Images not showing: Check files exist in `uploads/` and that the filenames returned by the API are reachable under `/uploads/<filename>`.

## Security & production notes
- The admin demo login (`admin`/`admin`) is for local testing only.
- For production, set a strong `SECRET_KEY`, use a real database, and run behind a WSGI server (e.g., gunicorn) with a reverse proxy.


