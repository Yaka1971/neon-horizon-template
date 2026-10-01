from flask import Flask, render_template_string, send_from_directory, request, redirect, url_for, session, abort
import os, json, shutil, secrets, time
from datetime import datetime
from collections import defaultdict, deque
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from PIL import Image

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MD_ENV = os.environ.get("MD_ENV", "development").strip().lower()
MD_PRODUCTION = MD_ENV == "production"

MD_SECRET_KEY = os.environ.get("MD_SECRET_KEY", "").strip()
MD_MANAGER_USER = os.environ.get("MD_MANAGER_USER", "").strip()
MD_MANAGER_PASSWORD = os.environ.get("MD_MANAGER_PASSWORD", "")

if MD_PRODUCTION:
    missing = []
    if len(MD_SECRET_KEY) < 32: missing.append("MD_SECRET_KEY (32+ characters)")
    if not MD_MANAGER_USER: missing.append("MD_MANAGER_USER")
    if len(MD_MANAGER_PASSWORD) < 12: missing.append("MD_MANAGER_PASSWORD (12+ characters)")
    if missing:
        raise RuntimeError("Production configuration missing: " + ", ".join(missing))
else:
    MD_SECRET_KEY = MD_SECRET_KEY or "md-neon-local-development-key-change-before-deployment"
    MD_MANAGER_USER = MD_MANAGER_USER or "admin"
    MD_MANAGER_PASSWORD = MD_MANAGER_PASSWORD or "MD-Launch-2026!"

app.secret_key = MD_SECRET_KEY
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=MD_PRODUCTION,
    MAX_CONTENT_LENGTH=250 * 1024 * 1024,
)

MD_DATA_DIR = os.environ.get("MD_DATA_DIR", os.path.join(BASE_DIR, "md_data")).strip()
if MD_PRODUCTION and not os.environ.get("MD_DATA_DIR", "").strip():
    raise RuntimeError("MD_DATA_DIR must point to persistent storage in production.")

PUBLISHED = os.path.join(MD_DATA_DIR, "published.json")
DRAFT = os.path.join(MD_DATA_DIR, "draft.json")
BACKUPS = os.path.join(MD_DATA_DIR, "backups")
MEDIA_ROOT = os.path.join(MD_DATA_DIR, "media")
MEDIA_DRAFT = os.path.join(MEDIA_ROOT, "draft")
MEDIA_PUBLISHED = os.path.join(MEDIA_ROOT, "published")
MEDIA_JSON = os.path.join(MEDIA_ROOT, "media.json")

DEFAULT_CONTENT = {
    "site_name": "NEON HORIZON",
    "artist_name": "Nova Ray",
    "hero_kicker": "A MAYAKA'AL DIGITAL EXPERIENCE",
    "hero_headline": "FEEL THE SOUND",
    "hero_description": "A cinematic artist website experience built for musicians, singers, producers, and creators.",
    "hero_button": "Listen Now",
    "music_label": "Featured Releases",
    "music_heading": "Latest Music",
    "player_label": "Now Playing",
    "player_heading": "Featured Track",
    "video_label": "Visual Experience",
    "video_heading": "Latest Videos",
    "contact_label": "Connect With The Artist",
    "contact_heading": "Booking & Contact",
    "contact_text": "Ready to book a performance, request a feature, or collaborate on a new project?",
    "contact_button": "Book Now",
    "booking_email": "booking@example.com",
    "youtube_url": "#",
    "spotify_url": "#",
    "apple_music_url": "#",
    "instagram_url": "#",
    "footer_text": "© 2026 Neon Horizon.",
    "timezone": "America/New_York",

    "release_1_title": "Midnight Echoes",
    "release_1_type": "New Single",
    "release_1_track_1": "01 • Midnight Echoes",
    "release_1_track_1_time": "3:42",
    "release_1_track_2": "02 • Electric Dreams",
    "release_1_track_2_time": "4:11",
    "release_1_track_3": "03 • Afterglow",
    "release_1_track_3_time": "5:02",

    "release_2_title": "Electric Dreams",
    "release_2_type": "Extended Play",
    "release_2_track_1": "01 • Electric Dreams",
    "release_2_track_1_time": "4:11",
    "release_2_track_2": "02 • Neon Skyline",
    "release_2_track_2_time": "3:58",
    "release_2_track_3": "03 • Night Drive",
    "release_2_track_3_time": "4:26",

    "release_3_title": "Afterglow",
    "release_3_type": "Full Album",
    "release_3_track_1": "01 • Afterglow",
    "release_3_track_1_time": "5:02",
    "release_3_track_2": "02 • City Lights",
    "release_3_track_2_time": "3:49",
    "release_3_track_3": "03 • Lost In Motion",
    "release_3_track_3_time": "4:34",

    "video_1_title": "Midnight Echoes",
    "video_1_type": "Official Music Video",
    "video_1_url": "https://www.youtube.com/embed/ylj1lBUt7Ss",
    "video_2_title": "Electric Dreams",
    "video_2_type": "Live Performance",
    "video_2_url": "https://www.youtube.com/embed/-fS9rORQtMI",
    "video_3_title": "Afterglow",
    "video_3_type": "Cinematic Visualizer",
    "video_3_url": "https://www.youtube.com/embed/1OAVoq37Dko",
}

MEDIA_DEFAULTS = {
    "hero": "images/nova-ray-final.png",
    "album_1": "images/album-1.png",
    "album_2": "images/album-2.png",
    "album_3": "images/album-3.png",
    "video_1": "images/video-1.png",
    "video_2": "images/video-2.png",
    "video_3": "images/video-3.png",
    "audio_1": "music/cinematic-1.mp3",
    "audio_2": "music/cinematic-2.mp3",
    "audio_3": "music/cinematic-3.mp3",
}
MEDIA_STATE_DEFAULT = {k: {"draft": "", "published": ""} for k in MEDIA_DEFAULTS}

HOME_KEYS = [
    "site_name","artist_name","hero_kicker","hero_headline","hero_description","hero_button",
    "music_label","music_heading","player_label","player_heading","video_label","video_heading",
    "contact_label","contact_heading","contact_text","contact_button","footer_text"
]
CONTACT_KEYS = ["booking_email","youtube_url","spotify_url","apple_music_url","instagram_url","timezone"]
RELEASE_KEYS = [k for k in DEFAULT_CONTENT if k.startswith("release_")]
VIDEO_KEYS = [k for k in DEFAULT_CONTENT if k.startswith("video_")]

LOGIN_ATTEMPTS = defaultdict(deque)
LOGIN_WINDOW = 15 * 60
LOGIN_MAX = 8

def ensure_storage():
    for p in (MD_DATA_DIR, BACKUPS, MEDIA_ROOT, MEDIA_DRAFT, MEDIA_PUBLISHED):
        os.makedirs(p, exist_ok=True)
    for path in (PUBLISHED, DRAFT):
        if not os.path.exists(path):
            save_json(path, DEFAULT_CONTENT)
    if not os.path.exists(MEDIA_JSON):
        save_json(MEDIA_JSON, MEDIA_STATE_DEFAULT)

def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(fallback)
        merged.update(data)
        return merged
    except Exception:
        return dict(fallback)

def content(which="published"):
    ensure_storage()
    return load_json(DRAFT if which == "draft" else PUBLISHED, DEFAULT_CONTENT)

def media_state():
    ensure_storage()
    raw = load_json(MEDIA_JSON, MEDIA_STATE_DEFAULT)
    merged = {}
    for k in MEDIA_DEFAULTS:
        merged[k] = {"draft": "", "published": ""}
        if isinstance(raw.get(k), dict):
            merged[k].update(raw[k])
    return merged

def media_url(slot, which="published"):
    state = media_state()
    name = state.get(slot, {}).get(which, "")
    if name:
        return url_for("managed_media", state=which, filename=name)
    return "/" + MEDIA_DEFAULTS[slot]

def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token

app.jinja_env.globals["csrf_token"] = csrf_token

@app.before_request
def protect_post():
    ensure_storage()
    if request.method in {"POST","PUT","PATCH","DELETE"}:
        sent = request.form.get("_csrf_token", "")
        expected = session.get("_csrf_token", "")
        if not sent or not expected or not secrets.compare_digest(str(sent), str(expected)):
            abort(400)

@app.after_request
def headers(resp):
    resp.headers.setdefault("X-Content-Type-Options","nosniff")
    resp.headers.setdefault("X-Frame-Options","SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy","strict-origin-when-cross-origin")
    resp.headers.setdefault("Permissions-Policy","camera=(), microphone=(), geolocation=()")
    if request.path.startswith("/manager"):
        resp.headers.setdefault("Cache-Control","no-store, private")
    if MD_PRODUCTION:
        resp.headers.setdefault("Strict-Transport-Security","max-age=31536000; includeSubDomains")
    return resp

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("md_logged_in"):
            return redirect(url_for("manager_login"))
        return fn(*args, **kwargs)
    return wrapped

def login_key():
    forwarded = request.headers.get("X-Forwarded-For","")
    return (forwarded.split(",")[0].strip() if forwarded else request.remote_addr) or "unknown"

def rate_limited(key):
    now = time.time()
    q = LOGIN_ATTEMPTS[key]
    while q and now-q[0] > LOGIN_WINDOW: q.popleft()
    return len(q) >= LOGIN_MAX

def backup_live():
    os.makedirs(BACKUPS, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(BACKUPS, f"published-{stamp}.json")
    shutil.copy2(PUBLISHED, dest)
    return dest

def save_fields(keys):
    data = content("draft")
    for key in keys:
        data[key] = request.form.get(key, "").strip()
    save_json(DRAFT, data)

def publish_all():
    backup_live()
    shutil.copy2(DRAFT, PUBLISHED)
    state = media_state()
    for slot, info in state.items():
        draft_name = info.get("draft","")
        if draft_name:
            src = os.path.join(MEDIA_DRAFT, draft_name)
            if os.path.isfile(src):
                dst = os.path.join(MEDIA_PUBLISHED, draft_name)
                shutil.copy2(src, dst)
                old = info.get("published","")
                info["published"] = draft_name
                if old and old != draft_name:
                    oldpath = os.path.join(MEDIA_PUBLISHED, old)
                    if os.path.isfile(oldpath):
                        try: os.remove(oldpath)
                        except OSError: pass
    save_json(MEDIA_JSON, state)

def public_payload(c, which):
    return {
        "artist": c["artist_name"],
        "albums": {
            "midnight": {
                "title": c["release_1_title"], "type": f'{c["artist_name"]} • {c["release_1_type"]}',
                "cover": media_url("album_1", which), "audio": media_url("audio_1", which),
                "tracks": [[c[f"release_1_track_{i}"], c[f"release_1_track_{i}_time"]] for i in range(1,4)]
            },
            "electric": {
                "title": c["release_2_title"], "type": f'{c["artist_name"]} • {c["release_2_type"]}',
                "cover": media_url("album_2", which), "audio": media_url("audio_2", which),
                "tracks": [[c[f"release_2_track_{i}"], c[f"release_2_track_{i}_time"]] for i in range(1,4)]
            },
            "afterglow": {
                "title": c["release_3_title"], "type": f'{c["artist_name"]} • {c["release_3_type"]}',
                "cover": media_url("album_3", which), "audio": media_url("audio_3", which),
                "tracks": [[c[f"release_3_track_{i}"], c[f"release_3_track_{i}_time"]] for i in range(1,4)]
            },
        },
        "videos": [c["video_1_url"], c["video_2_url"], c["video_3_url"]]
    }

PUBLIC_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ c.site_name }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">
<style>
.hero{background-image:url("{{ media.hero }}")!important}
.cover-one{background-image:url("{{ media.album_1 }}")!important}
.cover-two{background-image:url("{{ media.album_2 }}")!important}
.cover-three{background-image:url("{{ media.album_3 }}")!important}
.video-one{background-image:url("{{ media.video_1 }}")!important}
.video-two{background-image:url("{{ media.video_2 }}")!important}
.video-three{background-image:url("{{ media.video_3 }}")!important}
.preview-bar{position:fixed;left:0;right:0;bottom:0;z-index:10000;background:#050505eF;border-top:1px solid gold;color:white;padding:10px 16px;text-align:center;font:700 12px Arial,sans-serif;letter-spacing:1px}
</style>
</head><body>
<div class="particles"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
<header><div class="logo">{{ c.site_name }}</div><nav>
<a href="#home">Home</a><a href="#music">Music</a><a href="#player">Player</a><a href="#videos">Videos</a><a href="#contact">Contact</a>
</nav></header>
<section class="hero" id="home"><div class="overlay"></div><div class="hero-content">
<p class="small-text">{{ c.hero_kicker }}</p><h1>{{ c.hero_headline }}</h1>
<p class="hero-description">{{ c.hero_description }}</p><button onclick="document.querySelector('#music').scrollIntoView({behavior:'smooth'})">{{ c.hero_button }}</button>
</div></section>
<section class="music-section" id="music"><p class="section-label reveal">{{ c.music_label }}</p><h2 class="reveal">{{ c.music_heading }}</h2>
<div class="album-grid">
<div class="album-card active-album reveal" data-album="midnight"><div class="album-cover cover-one"></div><h3>{{ c.release_1_title }}</h3><p>{{ c.release_1_type }}</p><button class="small-btn">Listen</button></div>
<div class="album-card reveal" data-album="electric"><div class="album-cover cover-two"></div><h3>{{ c.release_2_title }}</h3><p>{{ c.release_2_type }}</p><button class="small-btn">Listen</button></div>
<div class="album-card reveal" data-album="afterglow"><div class="album-cover cover-three"></div><h3>{{ c.release_3_title }}</h3><p>{{ c.release_3_type }}</p><button class="small-btn">Listen</button></div>
</div></section>
<section class="player-section" id="player"><p class="section-label reveal">{{ c.player_label }}</p><h2 class="reveal">{{ c.player_heading }}</h2>
<div class="player-container reveal"><div class="player-cover"><img src="{{ media.album_1 }}" alt="{{ c.release_1_title }} Album Cover"></div>
<div class="player-info"><h3>{{ c.release_1_title }}</h3><p>{{ c.artist_name }} • {{ c.release_1_type }}</p>
<audio controls class="audio-player"><source src="{{ media.audio_1 }}" type="audio/mpeg">Your browser does not support the audio element.</audio>
<div class="track-list"></div></div></div></section>
<section class="video-section" id="videos"><p class="section-label">{{ c.video_label }}</p><h2>{{ c.video_heading }}</h2><div class="video-grid">
<div class="video-card"><div class="video-thumbnail video-one"><div class="play-button">▶</div></div><h3>{{ c.video_1_title }}</h3><p>{{ c.video_1_type }}</p></div>
<div class="video-card"><div class="video-thumbnail video-two"><div class="play-button">▶</div></div><h3>{{ c.video_2_title }}</h3><p>{{ c.video_2_type }}</p></div>
<div class="video-card"><div class="video-thumbnail video-three"><div class="play-button">▶</div></div><h3>{{ c.video_3_title }}</h3><p>{{ c.video_3_type }}</p></div>
</div></section>
<div class="video-modal" id="videoModal"><div class="video-modal-content"><span class="close-video">&times;</span>
<iframe id="videoFrame" src="" title="{{ c.site_name }} Video Player" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe></div></div>
<section class="contact-section" id="contact"><p class="section-label">{{ c.contact_label }}</p><h2>{{ c.contact_heading }}</h2>
<p class="contact-text">{{ c.contact_text }}</p><a href="mailto:{{ c.booking_email }}" class="contact-btn">{{ c.contact_button }}</a>
<div class="social-links"><a href="{{ c.youtube_url }}">YouTube</a><a href="{{ c.spotify_url }}">Spotify</a><a href="{{ c.apple_music_url }}">Apple Music</a><a href="{{ c.instagram_url }}">Instagram</a></div>
</section><footer><p>{{ c.footer_text }} <span class="md-credit">Powered by MAYAKA'AL DIGITAL.</span></p></footer>
<script>window.NEON_DATA={{ payload|tojson }};</script><script src="/script.js"></script>
{% if preview %}<div class="preview-bar">MD SITE MANAGER PREVIEW — DRAFT CONTENT — NOT LIVE</div>{% endif %}
</body></html>'''

MANAGER_CSS = r'''
:root{--cyan:#00d9ff;--gold:#ffc02d;--bg:#040812;--panel:#08111f;--line:#12cfff42;--muted:#8fa4b7;--green:#3ee68b}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top right,#10204a 0,#040812 35%);color:#fff;font-family:Arial,sans-serif}
header{min-height:72px;padding:16px 5%;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);background:#040812e8;position:sticky;top:0;z-index:10}
.logo{font-weight:900;letter-spacing:2px;font-size:22px}.logo b{color:var(--cyan)}.logo span{color:var(--gold)}
.top{display:flex;gap:10px;flex-wrap:wrap}a{color:inherit}.top a,.btn{border:1px solid var(--line);padding:11px 15px;border-radius:9px;text-decoration:none;font-weight:800;font-size:11px;letter-spacing:.8px;background:#071426;color:#fff;cursor:pointer}
.btn.gold{background:var(--gold);color:#08111f;border-color:var(--gold)}.btn.publish{background:var(--green);color:#04140c;border-color:var(--green)}
main{max-width:1180px;margin:auto;padding:50px 5% 80px}.eyebrow{color:var(--cyan);font-size:12px;letter-spacing:3px;font-weight:900}.title,h1{font-size:48px;margin:8px 0 10px}.sub,.lead{color:var(--muted);line-height:1.6}
.heroRow{display:flex;justify-content:space-between;gap:20px;align-items:flex-end}.actions,.buttons{display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}
.statusbar,.grid,.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:28px}.stat,.tile,.card,form.editor{background:#07111f;border:1px solid var(--line);border-radius:16px;padding:22px}
.stat small{color:var(--muted);display:block;margin-bottom:8px}.live,.ready{color:var(--green)}.draft{color:var(--gold)}
.tile{text-decoration:none;transition:.2s}.tile:hover{transform:translateY(-3px);border-color:var(--cyan)}.tile i{font-style:normal;font-size:30px}.tile h3{margin:12px 0 8px}.tile p{color:var(--muted);line-height:1.5;font-size:14px}.status{font-size:10px;font-weight:900;letter-spacing:1px}
form.editor{margin-top:25px}.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.field.wide{grid-column:1/-1}.field label{display:block;color:var(--cyan);font-size:10px;font-weight:900;letter-spacing:1.3px;margin-bottom:7px}
input,textarea,select{width:100%;padding:13px;border-radius:9px;border:1px solid #173550;background:#020811;color:#fff;font:inherit}textarea{min-height:110px;resize:vertical}
.notice,.success,.error{padding:14px 16px;border-radius:10px;margin:18px 0;line-height:1.5}.notice{background:#0b1730;border:1px solid #1e4772}.success{background:#08291b;border:1px solid #1e8d5c}.error{background:#321014;border:1px solid #9d3540}
.back{color:var(--cyan);font-weight:800;text-decoration:none;font-size:12px}.protect{margin-top:22px;color:#71869a;font-size:10px;line-height:1.6}.locked-credit{margin-top:18px;padding:14px 16px;border:1px solid #173550;border-radius:9px;background:#020811;color:#8fa4b7}.locked-credit b{color:#ffc02d}.locked-credit code{color:#fff;font-family:inherit}
.media-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-top:24px}.media-card{background:#07111f;border:1px solid var(--line);border-radius:16px;padding:18px}.media-card img{width:100%;max-height:230px;object-fit:cover;border-radius:10px;background:#020811}.media-card audio{width:100%;margin:10px 0}
.list{display:grid;gap:12px;margin-top:22px}.item{background:#07111f;border:1px solid var(--line);border-radius:13px;padding:17px;display:flex;justify-content:space-between;align-items:center;gap:18px}.meta{color:var(--muted);font-size:12px;margin-top:5px}
@media(max-width:800px){header{padding:14px 18px;flex-wrap:wrap}.logo{font-size:19px}main{padding:30px 16px 60px}.title,h1{font-size:36px}.heroRow{display:block}.statusbar,.grid,.cards,.formgrid,.media-grid{grid-template-columns:1fr}.field.wide{grid-column:auto}.item{display:block}.item form{margin-top:12px}.actions .btn,.buttons .btn{flex:1 1 150px}}
'''

LOGIN = r'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>MD SITE MANAGER</title><style>''' + MANAGER_CSS + r'''
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;800;900&display=swap');
html,body{min-height:100%;height:100%}
body{background:#02050a url("/images/MD_SITE_MANAGER_LOGIN.png") center center/cover no-repeat fixed;overflow:auto}
.login-shell{min-height:100vh;display:flex;align-items:center;justify-content:flex-end;padding:5vh 7vw}
.login-panel{width:min(430px,100%);background:rgba(2,8,17,.88);border:1px solid rgba(18,207,255,.45);border-radius:18px;padding:30px;box-shadow:0 20px 60px rgba(0,0,0,.55);backdrop-filter:blur(8px)}
.login-brand{text-align:center;padding:2px 8px 4px}
.login-brand .eyebrow{text-align:center}
.login-panel h1{font-family:'Orbitron','Trebuchet MS',Arial,sans-serif;font-size:34px;line-height:1.15;letter-spacing:2px;margin:12px 0 10px;text-align:center;text-transform:uppercase}
.login-brand .lead{text-align:center;max-width:340px;margin:0 auto;line-height:1.55}
.login-panel form.editor{margin-top:20px;background:rgba(7,17,31,.72)}
@media(max-width:900px){body{background-position:center center}.login-shell{justify-content:center;padding:24px}.login-panel{margin-top:42vh;background:rgba(2,8,17,.94)}}
</style></head><body>
<div class="login-shell"><div class="login-panel"><div class="login-brand"><div class="eyebrow">MAYAKA'AL DIGITAL</div><h1>MD SITE MANAGER</h1><div class="lead">NEON HORIZON • Protected Design / Editable Content</div></div>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form class="editor" method="post"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">
<div class="field"><label>USERNAME</label><input name="username" autocomplete="username" required></div><br>
<div class="field"><label>PASSWORD</label><input name="password" type="password" autocomplete="current-password" required></div>
<div class="buttons"><button class="btn gold" type="submit">SIGN IN</button></div></form></div></div></body></html>'''

DASH = r'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>MD SITE MANAGER | Dashboard</title><style>''' + MANAGER_CSS + r'''</style></head><body>
<header><div class="logo"><b>M</b><span>D</span> SITE MANAGER</div><div class="top"><a href="/" target="_blank">VIEW LIVE SITE</a><a href="/manager/logout">SIGN OUT</a></div></header>
<main><div class="heroRow"><div><div class="eyebrow">NEON HORIZON</div><div class="title">Artist Website Dashboard</div><div class="sub">MD SITE MANAGER PLATFORM • Protected Design / Editable Content</div></div>
<div class="actions"><a class="btn" href="/manager/preview" target="_blank">PREVIEW DRAFT</a><a class="btn gold" href="/manager/content">EDIT SITE CONTENT</a></div></div>
<div class="statusbar"><div class="stat"><small>LIVE WEBSITE</small><b class="live">● PUBLISHED</b></div><div class="stat"><small>DRAFT WORKSPACE</small><b class="draft">● READY</b></div><div class="stat"><small>ACTIVE SITE</small><b>{{ c.site_name }}</b></div></div>
<div class="grid">
<a class="tile" href="/manager/content"><i>✎</i><h3>Site Content</h3><p>Edit artist identity, hero, section headings and contact call-to-action.</p><span class="status ready">LIVE MODULE</span></a>
<a class="tile" href="/manager/releases"><i>♫</i><h3>Music & Releases</h3><p>Manage all three releases, release types, track names and durations.</p><span class="status ready">LIVE MODULE</span></a>
<a class="tile" href="/manager/videos"><i>▶</i><h3>Videos</h3><p>Edit video titles, descriptions and YouTube embed links.</p><span class="status ready">LIVE MODULE</span></a>
<a class="tile" href="/manager/media"><i>▣</i><h3>Media</h3><p>Upload hero art, album covers, video thumbnails and MP3 audio.</p><span class="status ready">LIVE MODULE</span></a>
<a class="tile" href="/manager/contact"><i>✉</i><h3>Contact & Socials</h3><p>Manage booking email and artist platform links.</p><span class="status ready">LIVE MODULE</span></a>
<a class="tile" href="/manager/preview" target="_blank"><i>◉</i><h3>Preview</h3><p>Review the complete draft website before publishing.</p><span class="status ready">LIVE MODULE</span></a>
<a class="tile" href="/manager/backups"><i>↻</i><h3>Backups</h3><p>Restore a previously published content version safely.</p><span class="status ready">LIVE MODULE</span></a>
<div class="tile"><i>⚡</i><h3>Publish</h3><p>Publish from any editor after reviewing the draft. The design remains protected.</p><span class="status ready">LIVE MODULE</span></div>
</div></main></body></html>'''

def editor_template(title, lead, fields):
    field_html = ""
    for key, label, kind in fields:
        cls = "field wide" if kind == "textarea" else "field"
        if kind == "textarea":
            control = f'<textarea name="{key}" maxlength="500">{{{{ c.{key} }}}}</textarea>'
        else:
            control = f'<input name="{key}" value="{{{{ c.{key} }}}}" maxlength="300">'
        field_html += f'<div class="{cls}"><label>{label}</label>{control}</div>'
    return r'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>MD SITE MANAGER | ''' + title + r'''</title><style>''' + MANAGER_CSS + r'''</style></head><body>
<header><div class="logo"><b>M</b><span>D</span> SITE MANAGER</div><a class="back" href="/manager/dashboard">DASHBOARD</a></header><main>
<a class="back" href="/manager/dashboard">← BACK TO DASHBOARD</a><h1>''' + title + r'''</h1><div class="lead">''' + lead + r'''</div>
{% if message %}<div class="success">{{ message }}</div>{% endif %}
<div class="notice"><b>DRAFT WORKFLOW:</b> Save Draft → Preview → Publish. Saving a draft never changes the public website.</div>
<form class="editor" method="post"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><div class="formgrid">''' + field_html + r'''</div>
{% if show_locked_credit %}<div class="locked-credit"><b>🔒 MAYAKA'AL DIGITAL SITE CREDIT — LOCKED</b><br><code>Powered by MAYAKA'AL DIGITAL.</code><br><small>This protected developer credit is displayed automatically on the public website and cannot be changed from the Site Manager.</small></div>{% endif %}
<div class="buttons"><button class="btn gold" name="action" value="save">SAVE DRAFT</button><a class="btn" href="/manager/preview" target="_blank">PREVIEW DRAFT</a><button class="btn publish" name="action" value="publish">PUBLISH TO LIVE SITE</button></div>
<div class="protect">🔒 DESIGN PROTECTION ACTIVE — Content can change. NEON HORIZON's approved layout, styling, animation and structure remain protected.</div></form></main></body></html>'''

CONTENT_FIELDS = [
("site_name","SITE / BRAND NAME","text"),("artist_name","ARTIST NAME","text"),("hero_kicker","HERO KICKER","text"),("hero_headline","HERO HEADLINE","text"),
("hero_description","HERO DESCRIPTION","textarea"),("hero_button","HERO BUTTON","text"),("music_label","MUSIC SECTION LABEL","text"),("music_heading","MUSIC HEADING","text"),
("player_label","PLAYER SECTION LABEL","text"),("player_heading","PLAYER HEADING","text"),("video_label","VIDEO SECTION LABEL","text"),("video_heading","VIDEO HEADING","text"),
("contact_label","CONTACT SECTION LABEL","text"),("contact_heading","CONTACT HEADING","text"),("contact_text","CONTACT TEXT","textarea"),("contact_button","CONTACT BUTTON","text"),("footer_text","FOOTER TEXT","text")
]
CONTACT_FIELDS = [(k, k.replace("_"," ").upper(), "text") for k in CONTACT_KEYS]
RELEASE_FIELDS = [(k, k.replace("_"," ").upper(), "text") for k in RELEASE_KEYS]
VIDEO_FIELDS = [(k, k.replace("_"," ").upper(), "text") for k in VIDEO_KEYS]

@app.route("/")
def home():
    c = content("published")
    media = {k: media_url(k,"published") for k in MEDIA_DEFAULTS}
    return render_template_string(PUBLIC_TEMPLATE, c=c, media=media, payload=public_payload(c,"published"), preview=False)

@app.route("/style.css")
def style_css():
    return send_from_directory(BASE_DIR, "style.css", mimetype="text/css")

@app.route("/script.js")
def script_js():
    return send_from_directory(BASE_DIR, "script.js", mimetype="application/javascript")

@app.route("/images/<path:filename>")
def images(filename):
    return send_from_directory(os.path.join(BASE_DIR,"images"), filename)

@app.route("/music/<path:filename>")
def music(filename):
    return send_from_directory(os.path.join(BASE_DIR,"music"), filename)

@app.route("/md-media/<state>/<path:filename>")
def managed_media(state, filename):
    if state not in {"draft","published"}: abort(404)
    return send_from_directory(MEDIA_DRAFT if state=="draft" else MEDIA_PUBLISHED, filename)

@app.route("/manager/login", methods=["GET","POST"])
def manager_login():
    if session.get("md_logged_in"): return redirect(url_for("manager_dashboard"))
    error = ""
    if request.method == "POST":
        key = login_key()
        if rate_limited(key):
            error = "Too many failed attempts. Please wait before trying again."
        elif secrets.compare_digest(request.form.get("username",""), MD_MANAGER_USER) and secrets.compare_digest(request.form.get("password",""), MD_MANAGER_PASSWORD):
            LOGIN_ATTEMPTS.pop(key, None)
            session.clear()
            session["md_logged_in"] = True
            csrf_token()
            return redirect(url_for("manager_dashboard"))
        else:
            LOGIN_ATTEMPTS[key].append(time.time())
            error = "Invalid username or password."
    return render_template_string(LOGIN, error=error)

@app.route("/manager/logout")
def manager_logout():
    session.clear()
    return redirect(url_for("manager_login"))

@app.route("/manager")
@app.route("/manager/dashboard")
@login_required
def manager_dashboard():
    return render_template_string(DASH, c=content("published"))

def run_editor(keys, title, lead, fields):
    msg = ""
    if request.method == "POST":
        save_fields(keys)
        if request.form.get("action") == "publish":
            publish_all()
            msg = "Published successfully. The live NEON HORIZON website is updated."
        else:
            msg = "Draft saved. The public website has not changed."
    return render_template_string(editor_template(title,lead,fields), c=content("draft"), message=msg, show_locked_credit=("footer_text" in keys))

@app.route("/manager/content", methods=["GET","POST"])
@login_required
def manager_content():
    return run_editor(HOME_KEYS, "Site Content", "Edit NEON HORIZON's identity, hero, section headings and contact presentation without touching the design.", CONTENT_FIELDS)

@app.route("/manager/releases", methods=["GET","POST"])
@login_required
def manager_releases():
    return run_editor(RELEASE_KEYS, "Music & Releases", "Manage the three featured releases and their visible track lists.", RELEASE_FIELDS)

@app.route("/manager/videos", methods=["GET","POST"])
@login_required
def manager_videos():
    return run_editor(VIDEO_KEYS, "Videos", "Manage video titles, labels and YouTube embed URLs.", VIDEO_FIELDS)

@app.route("/manager/contact", methods=["GET","POST"])
@login_required
def manager_contact():
    return run_editor(CONTACT_KEYS, "Contact & Socials", "Manage booking email, artist platform links and client time zone.", CONTACT_FIELDS)

MEDIA_TEMPLATE = r'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>MD SITE MANAGER | Media</title><style>''' + MANAGER_CSS + r'''</style></head><body>
<header><div class="logo"><b>M</b><span>D</span> SITE MANAGER</div><a class="back" href="/manager/dashboard">DASHBOARD</a></header><main>
<a class="back" href="/manager/dashboard">← BACK TO DASHBOARD</a><h1>Media</h1><div class="lead">Upload replacement artwork and audio. Files enter Draft first and become public only when you publish.</div>
{% if message %}<div class="success">{{ message }}</div>{% endif %}{% if error %}<div class="error">{{ error }}</div>{% endif %}
<div class="notice"><b>MEDIA WORKFLOW:</b> Upload → Preview Draft → Publish. Images: PNG/JPG/JPEG/WEBP. Audio: MP3.</div>
<div class="media-grid">{% for slot in slots %}
<div class="media-card"><h3>{{ labels[slot] }}</h3>
{% if slot.startswith("audio_") %}<audio controls src="{{ urls[slot] }}"></audio>{% else %}<img src="{{ urls[slot] }}" alt="{{ labels[slot] }}">{% endif %}
<form method="post" enctype="multipart/form-data"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><input type="hidden" name="slot" value="{{ slot }}">
<input type="file" name="file" accept="{{ 'audio/mpeg,.mp3' if slot.startswith('audio_') else 'image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp' }}" required>
<div class="buttons"><button class="btn gold" name="action" value="upload">UPLOAD TO DRAFT</button></div></form></div>{% endfor %}</div>
<div class="buttons"><a class="btn" href="/manager/preview" target="_blank">PREVIEW DRAFT</a>
<form method="post" style="margin:0"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><input type="hidden" name="slot" value="__publish__"><button class="btn publish" name="action" value="publish">PUBLISH ALL DRAFT CHANGES</button></form></div>
<div class="protect">🔒 DESIGN PROTECTION ACTIVE — Media can be replaced without exposing website code or layout controls.</div>
</main></body></html>'''

@app.route("/manager/media", methods=["GET","POST"])
@login_required
def manager_media():
    message, error = "", ""
    if request.method == "POST":
        if request.form.get("action") == "publish":
            publish_all()
            message = "Draft content and media published successfully."
        else:
            slot = request.form.get("slot","")
            f = request.files.get("file")
            if slot not in MEDIA_DEFAULTS or not f or not f.filename:
                error = "Choose a valid media file."
            else:
                ext = f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
                allowed = {"mp3"} if slot.startswith("audio_") else {"png","jpg","jpeg","webp"}
                if ext not in allowed:
                    error = "That file type is not allowed for this media slot."
                else:
                    safe = secure_filename(f.filename)
                    unique = f"{slot}-{int(time.time())}-{secrets.token_hex(4)}.{ext}"
                    dest = os.path.join(MEDIA_DRAFT, unique)
                    f.save(dest)
                    if not slot.startswith("audio_"):
                        try:
                            with Image.open(dest) as im:
                                im.verify()
                        except Exception:
                            try: os.remove(dest)
                            except OSError: pass
                            error = "The uploaded image could not be validated."
                    if not error:
                        state = media_state()
                        old = state[slot].get("draft","")
                        state[slot]["draft"] = unique
                        save_json(MEDIA_JSON,state)
                        if old and old != unique:
                            oldpath = os.path.join(MEDIA_DRAFT,old)
                            if os.path.isfile(oldpath):
                                try: os.remove(oldpath)
                                except OSError: pass
                        message = f"{slot.replace('_',' ').title()} uploaded to Draft."
    labels = {
        "hero":"Hero Background","album_1":"Album Cover 1","album_2":"Album Cover 2","album_3":"Album Cover 3",
        "video_1":"Video Thumbnail 1","video_2":"Video Thumbnail 2","video_3":"Video Thumbnail 3",
        "audio_1":"Release Audio 1","audio_2":"Release Audio 2","audio_3":"Release Audio 3"
    }
    urls = {k: media_url(k,"draft") for k in MEDIA_DEFAULTS}
    return render_template_string(MEDIA_TEMPLATE, slots=list(MEDIA_DEFAULTS), labels=labels, urls=urls, message=message, error=error)

@app.route("/manager/preview")
@login_required
def manager_preview():
    c = content("draft")
    media = {k: media_url(k,"draft") for k in MEDIA_DEFAULTS}
    return render_template_string(PUBLIC_TEMPLATE, c=c, media=media, payload=public_payload(c,"draft"), preview=True)

BACKUP_TEMPLATE = r'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>MD SITE MANAGER | Backups</title><style>''' + MANAGER_CSS + r'''</style></head><body>
<header><div class="logo"><b>M</b><span>D</span> SITE MANAGER</div><a class="back" href="/manager/dashboard">DASHBOARD</a></header><main>
<a class="back" href="/manager/dashboard">← BACK TO DASHBOARD</a><h1>Backups & Restore</h1><div class="lead">Restore a previously published content snapshot without changing the protected website design.</div>
{% if message %}<div class="success">{{ message }}</div>{% endif %}
<div class="list">{% for b in backups %}<div class="item"><div><b>{{ b.name }}</b><div class="meta">{{ b.size }} KB • {{ b.time }}</div></div>
<form method="post"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><input type="hidden" name="backup" value="{{ b.name }}"><button class="btn" type="submit">RESTORE</button></form></div>{% else %}<div class="notice">No backups yet. A backup is created automatically before every publish.</div>{% endfor %}</div>
</main></body></html>'''

@app.route("/manager/backups", methods=["GET","POST"])
@login_required
def manager_backups():
    message = ""
    if request.method == "POST":
        name = os.path.basename(request.form.get("backup",""))
        src = os.path.join(BACKUPS,name)
        if os.path.isfile(src) and name.endswith(".json"):
            backup_live()
            shutil.copy2(src,PUBLISHED)
            shutil.copy2(src,DRAFT)
            message = "Backup restored to Live and Draft."
    tzname = content("published").get("timezone","America/New_York")
    try: tz = ZoneInfo(tzname)
    except ZoneInfoNotFoundError: tz = ZoneInfo("America/New_York")
    rows = []
    for name in sorted(os.listdir(BACKUPS), reverse=True):
        path = os.path.join(BACKUPS,name)
        if os.path.isfile(path) and name.endswith(".json"):
            dt = datetime.fromtimestamp(os.path.getmtime(path), tz)
            rows.append({"name":name,"size":round(os.path.getsize(path)/1024,1),"time":dt.strftime("%b %d, %Y • %I:%M %p")})
    return render_template_string(BACKUP_TEMPLATE, backups=rows, message=message)

@app.errorhandler(404)
def not_found(e):
    return "<h1>404</h1><p>Page not found.</p>",404

@app.errorhandler(413)
def too_large(e):
    return "<h1>Upload too large</h1><p>The maximum upload size is 250 MB.</p>",413

@app.errorhandler(500)
def server_error(e):
    return "<h1>Something went wrong</h1><p>Please try again.</p>",500

ensure_storage()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT","5000")), debug=not MD_PRODUCTION)
