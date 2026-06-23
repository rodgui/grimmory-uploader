from __future__ import annotations

import html
import os
from pathlib import Path
from flask import Flask, request, Response
from werkzeug.utils import secure_filename

MAX_CONTENT_MB = int(os.environ.get("MAX_CONTENT_MB", "768"))
DESTINATIONS = {
    "grimmory": {
        "label": "Grimmory /books",
        "path": Path(os.environ.get("GRIMMORY_BOOKS_DIR", "/grimmory-books")),
        "restricted": "books",
        "folderize": True,
    },
    "grimmory-manga": {
        "label": "Grimmory /manga",
        "path": Path(os.environ.get("GRIMMORY_MANGA_DIR", "/grimmory-manga")),
        "restricted": "visual",
        "folderize": True,
    },
    "grimmory-comics": {
        "label": "Grimmory /comics",
        "path": Path(os.environ.get("GRIMMORY_COMICS_DIR", "/grimmory-comics")),
        "restricted": "visual",
        "folderize": True,
    },
    "grimmory-drop": {
        "label": "Grimmory BookDrop",
        "path": Path(os.environ.get("GRIMMORY_DROP_DIR", "/grimmory-drop")),
        "restricted": False,
        "folderize": False,
    },
    "downloads": {
        "label": "Home Downloads",
        "path": Path(os.environ.get("DOWNLOADS_DIR", "/downloads")),
        "restricted": False,
        "folderize": False,
    },
}
ALLOWED_EXTENSIONS = {
    "books": {".epub", ".pdf", ".mobi", ".azw", ".azw3", ".cbz", ".cbr", ".txt"},
    "visual": {".cbz", ".cbr", ".zip", ".rar", ".7z", ".pdf"},
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_MB * 1024 * 1024

CSS = """
:root { color-scheme: dark; --bg:#0d1117; --card:#161b22; --border:#30363d; --fg:#e6edf3; --muted:#8b949e; --blue:#58a6ff; --green:#3fb950; --red:#f85149; }
* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: var(--bg); color: var(--fg); font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 24px; }
main { width: min(680px, 100%); background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 28px; box-shadow: 0 18px 60px rgba(0,0,0,.28); }
h1 { margin: 0 0 8px; font-size: 1.45rem; }
p { margin: 0 0 22px; color: var(--muted); line-height: 1.5; }
form { display: grid; gap: 16px; }
label { color: var(--fg); font-weight: 700; display: grid; gap: 8px; }
select, input[type=file] { width: 100%; padding: 14px; border: 1px solid var(--border); border-radius: 8px; background: #0b1220; color: var(--fg); }
input[type=file] { border-style: dashed; }
button, a.button { appearance: none; border: 0; border-radius: 8px; background: var(--blue); color: #08111f; font-weight: 800; padding: 12px 16px; cursor: pointer; text-decoration: none; text-align: center; }
button:hover, a.button:hover { filter: brightness(1.08); }
.notice { border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; margin-bottom: 16px; }
.ok { border-color: rgba(63,185,80,.45); color: var(--green); }
.err { border-color: rgba(248,81,73,.45); color: var(--red); }
ul { margin: 8px 0 18px 20px; color: var(--fg); }
li { margin: 4px 0; }
small { color: var(--muted); }
code { background:#0b1220; border:1px solid var(--border); border-radius:6px; padding:2px 5px; }
"""

def page(body: str, status: int = 200) -> Response:
    return Response(f"""<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Upload</title><style>{CSS}</style></head><body><main>{body}</main></body></html>""", status=status, mimetype="text/html")

def unique_destination(directory: Path, filename: str) -> Path:
    safe = secure_filename(filename).strip("._") or "upload.bin"
    path = Path(safe)
    stem = path.stem or "upload"
    suffix = path.suffix.lower()
    dest = directory / f"{stem}{suffix}"
    if not dest.exists():
        return dest
    i = 2
    while True:
        candidate = directory / f"{stem}-{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1

def destination_options() -> str:
    return "\n".join(
        f"<option value=\"{html.escape(key)}\">{html.escape(cfg["label"])}</option>"
        for key, cfg in DESTINATIONS.items()
    )

@app.get("/")
def index():
    return page(f"""
<h1>Grimmory Upload</h1>
<p>Envie um ou varios arquivos. Destinos Grimmory salvam cada livro/manga/comic em subpasta propria. BookDrop faz auto-import com metadata (qualquer formato). Downloads aceita qualquer extensao. Formatos: Books (EPUB, PDF, MOBI, AZW/AZW3, CBZ/CBR, TXT). Manga/Comics (CBZ, CBR, ZIP, RAR, 7Z, PDF).</p>
<form action=\"/upload\" method=\"post\" enctype=\"multipart/form-data\">
  <label>Destino
    <select name=\"destination\" required>
      {destination_options()}
    </select>
  </label>
  <label>Arquivos
    <input type=\"file\" name=\"files\" multiple required>
  </label>
  <button type=\"submit\">Enviar</button>
  <small>Limite atual: {MAX_CONTENT_MB} MB por requisicao.</small>
</form>
""")

@app.post("/upload")
def upload():
    destination_key = request.form.get("destination", "kavita")
    cfg = DESTINATIONS.get(destination_key)
    if cfg is None:
        return page("<div class=\"notice err\">Destino invalido.</div><a class=\"button\" href=\"/\">Voltar</a>", 400)

    files = request.files.getlist("files")
    files = [f for f in files if f and f.filename]
    if not files:
        return page("<div class=\"notice err\">Nenhum arquivo enviado.</div><a class=\"button\" href=\"/\">Voltar</a>", 400)

    target_dir = cfg["path"]
    target_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    errors = []
    for file in files:
        ext = Path(file.filename).suffix.lower()
        restriction = cfg["restricted"]
        if restriction and ext not in ALLOWED_EXTENSIONS[restriction]:
            errors.append(f"{file.filename}: extensao nao permitida para {cfg['label']}")
            continue
        save_dir = target_dir
        if cfg["folderize"]:
            base_name = secure_filename(Path(file.filename).stem).strip("._") or "item"
            save_dir = target_dir / base_name
            save_dir.mkdir(parents=True, exist_ok=True)
        dest = unique_destination(save_dir, file.filename)
        file.save(dest)
        os.chmod(dest, 0o664)
        saved.append(str(dest.relative_to(target_dir)) if cfg["folderize"] else dest.name)

    parts = []
    if saved:
        items = "".join(f"<li>{html.escape(name)}</li>" for name in saved)
        parts.append(f"<div class=\"notice ok\">{len(saved)} arquivo(s) enviado(s) para <strong>{html.escape(cfg["label"])}</strong>.</div><ul>{items}</ul>")
    if errors:
        items = "".join(f"<li>{html.escape(err)}</li>" for err in errors)
        parts.append(f"<div class=\"notice err\">{len(errors)} erro(s):</div><ul>{items}</ul>")
    if cfg["folderize"] and saved:
        parts.append("<p>Agora va no Grimmory e rode <code>Scan Library</code> na biblioteca correspondente.</p>")
    parts.append("<a class=\"button\" href=\"/\">Enviar mais</a>")
    return page("".join(parts), 207 if errors and saved else (400 if errors and not saved else 200))

@app.get("/healthz")
def healthz():
    return Response("ok\n", mimetype="text/plain")

@app.errorhandler(413)
def too_large(_):
    return page(f"<div class=\"notice err\">Upload grande demais. Limite por requisicao: {MAX_CONTENT_MB} MB.</div><a class=\"button\" href=\"/\">Voltar</a>", 413)
