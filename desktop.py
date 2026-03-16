import os
import base64
import shutil
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request

import django
import webview
from django.core.wsgi import get_wsgi_application
from django.contrib.staticfiles.handlers import StaticFilesHandler
from wsgiref.simple_server import make_server


# --- Helpers pour savoir si l'application est "frozen" (PyInstaller) ---
def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _app_dir() -> Path:
    """Renvoie le dossier de l'application (oÃ¹ est le .exe ou le script)."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _resource_path(relative: str) -> Path:
    """
    Renvoie le chemin complet d'une ressource incluse avec PyInstaller.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


# --- Gestion des fichiers de donnÃ©es (DB et media) ---
def _ensure_data_files() -> tuple[Path, Path]:
    """
    Place db.sqlite3 et media/ dans AppData de l'utilisateur
    pour Ã©viter PermissionError dans Program Files.
    """
    # CrÃ©e un dossier Boutique dans AppData
    user_data_dir = Path(os.getenv("APPDATA")) / "Boutique"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    db_path = user_data_dir / "db.sqlite3"
    media_dir = user_data_dir / "media"

    # Copier la base de donnÃ©es si elle n'existe pas
    bundled_db = _resource_path("db.sqlite3")
    if not db_path.exists() and bundled_db.exists():
        shutil.copy2(bundled_db, db_path)

    # Copier le dossier media si nÃ©cessaire
    bundled_media = _resource_path("media")
    if not media_dir.exists():
        if bundled_media.exists() and bundled_media.is_dir():
            shutil.copytree(bundled_media, media_dir)
        else:
            media_dir.mkdir(parents=True, exist_ok=True)

    return db_path, media_dir


# --- Attente du dÃ©marrage du serveur Django ---
def _wait_for_port(host: str, port: int, timeout: float = 10.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            try:
                sock.connect((host, port))
                return
            except OSError:
                time.sleep(0.1)
    raise RuntimeError("Le serveur Django n'a pas dÃ©marrÃ© Ã  temps.")



# --- Ouverture des PDF en dehors de la WebView ---
class DesktopApi:
    def __init__(self, data_dir: Path):
        self.download_dir = data_dir / "downloads"

    def open_pdf(self, url: str, cookies: str = ""):
        try:
            self.download_dir.mkdir(parents=True, exist_ok=True)
            name = Path(urlparse(url).path).name
            if not name.lower().endswith(".pdf"):
                name = f"document_{int(time.time())}.pdf"
            target = self.download_dir / name
            headers = {}
            if cookies:
                headers["Cookie"] = cookies
            request = Request(url, headers=headers)
            with urlopen(request) as response:
                content_type = response.headers.get("Content-Type", "")
                payload = response.read()
            if not payload or not payload.lstrip().startswith(b"%PDF"):
                return f"Réponse non PDF (Content-Type: {content_type or 'inconnu'})."
            with open(target, "wb") as handle:
                handle.write(payload)
            os.startfile(target)
            return True
        except Exception as exc:
            return str(exc)

    def open_pdf_bytes(self, name: str, data_b64: str):
        try:
            self.download_dir.mkdir(parents=True, exist_ok=True)
            safe_name = (name or "").strip() or f"document_{int(time.time())}.pdf"
            if not safe_name.lower().endswith(".pdf"):
                safe_name = f"{safe_name}.pdf"
            target = self.download_dir / safe_name
            payload = base64.b64decode(data_b64 or "")
            if not payload or not payload.lstrip().startswith(b"%PDF"):
                return "R?ponse non PDF (contenu invalide)."
            with open(target, "wb") as handle:
                handle.write(payload)
            os.startfile(target)
            return True
        except Exception as exc:
            return str(exc)

# --- DÃ©marrage du serveur Django ---
def _start_server(host: str, port: int, db_path: Path, media_dir: Path):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "boutique.settings")
    os.environ.setdefault("DJANGO_DEBUG", "True")
    os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")
    os.environ.setdefault("DJANGO_MEDIA_ROOT", str(media_dir))
    os.environ.setdefault("DESKTOP_PDF_INLINE", "1")

    django.setup()
    app = get_wsgi_application()
    app = StaticFilesHandler(app)
    httpd = make_server(host, port, app)

    # Lancer le serveur dans un thread
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


# --- Fonction principale ---
def main():
    host = "127.0.0.1"
    port = 8000

    db_path, media_dir = _ensure_data_files()

    httpd = _start_server(host, port, db_path, media_dir)
    _wait_for_port(host, port)

    # CrÃ©ation de la fenÃªtre desktop
    api = DesktopApi(db_path.parent)
    window = webview.create_window(
        "Boutique Inova",
        f"http://{host}:{port}/",
        width=1280,
        height=800,
        resizable=True,
        js_api=api,
    )

    
    def _inject_pdf_hook():
        script = r"""
        (function () {
          if (window.__pdf_hooked) return;
          window.__pdf_hooked = true;
          document.addEventListener('click', function (e) {
            var el = e.target;
            while (el && el.tagName !== 'A') {
              el = el.parentElement;
            }
            if (!el || !el.href) return;
            var href = el.href;
            var isPdf = href.indexOf('/pdf') !== -1 || href.indexOf('/ticket/') !== -1 || href.indexOf('/facture/') !== -1;
            if (!isPdf) return;
            e.preventDefault();
            if (window.pywebview && window.pywebview.api && window.pywebview.api.open_pdf_bytes) {
              fetch(href, { credentials: 'include' })
                .then(function (res) {
                  var ct = (res.headers.get('content-type') || '').toLowerCase();
                  if (!res.ok) {
                    throw new Error('HTTP ' + res.status);
                  }
                  if (ct && ct.indexOf('application/pdf') === -1 && ct.indexOf('application/octet-stream') === -1) {
                    throw new Error('R?ponse non PDF (Content-Type: ' + ct + ').');
                  }
                  return res.arrayBuffer();
                })
                .then(function (buffer) {
                  var bytes = new Uint8Array(buffer);
                  var binary = '';
                  var chunk = 0x8000;
                  for (var i = 0; i < bytes.length; i += chunk) {
                    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
                  }
                  var b64 = btoa(binary);
                  var urlObj = new URL(href);
                  var filename = urlObj.pathname.split('/').pop() || ('document_' + Date.now() + '.pdf');
                  return window.pywebview.api.open_pdf_bytes(filename, b64);
                })
                .then(function (result) {
                  if (result !== true) {
                    alert('PDF: ' + result);
                  }
                })
                .catch(function (err) {
                  alert('PDF: ' + err.message);
                });
            } else {
              window.location.href = href;
            }
          }, true);
        })();
        """
        window.evaluate_js(script)

    # Fermer le serveur Django proprement quand la fenÃªtre se ferme
    def _on_closed():
        httpd.shutdown()

    window.events.loaded += _inject_pdf_hook
    window.events.closed += _on_closed
    webview.start()


if __name__ == "__main__":
    main()



