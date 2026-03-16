from django.shortcuts import redirect
from django.urls import reverse


class SpaceAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.public_paths = {
            "/connexion/",
            "/deconnexion/",
            "/admin/login/",
            "/favicon.ico",
            "/robots.txt",
        }
        self.caissier_blocked_prefixes = (
            "/boutique/comptabilite/",
            "/boutique/personnel/",
            "/boutique/personnel/export/",
            "/boutique/salaires/",
            "/boutique/salaires/export/",
        )
        self.comptable_blocked_prefixes = ()

    def __call__(self, request):
        path = request.path or "/"

        if path.startswith("/static/") or path.startswith("/media/") or path.startswith("/admin/"):
            return self.get_response(request)

        if path in self.public_paths:
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            login_url = reverse("login_page")
            return redirect(f"{login_url}?next={path}")

        if user.is_superuser:
            return self.get_response(request)

        role = getattr(user, "role", "")

        # Magasin: only magasinier can access
        if path.startswith("/magasin/") and role != "magasinier":
            return redirect("portal_entry")

        # Boutique: magasinier blocked
        if path.startswith("/boutique/") and role == "magasinier":
            return redirect("portal_entry")

        # Fine-grained boutique restrictions
        if role == "caissier":
            if any(path.startswith(prefix) for prefix in self.caissier_blocked_prefixes):
                return redirect("dashboard")

        if role == "comptable":
            if any(path.startswith(prefix) for prefix in self.comptable_blocked_prefixes):
                return redirect("dashboard")

        # Root redirection for magasinier
        if path == "/" and role == "magasinier":
            return redirect("magasin_dashboard")

        return self.get_response(request)
