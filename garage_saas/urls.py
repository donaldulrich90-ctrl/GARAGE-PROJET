from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.static import serve as _media_serve

from accounts.views import post_login_redirect

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="dashboard/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("apres-login/", post_login_redirect, name="post_login_redirect"),
    path("fournisseur/", include("supplier_portal.urls")),
    path("", include("dashboard.urls")),
    path("compte/", include("accounts.urls")),
    path("clients/", include("clients.urls")),
    path("vehicules/", include("clients.vehicle_urls")),
    path("ordres/", include("repair_orders.urls")),
    path("stock/", include("inventory.urls")),
    path("caisse/", include("invoicing.urls")),
    path("depenses/", include("expenses.urls")),
    path("rh/", include("hr.urls")),
    path("garages/", include("tenants.urls")),
    path("plateforme/", include("core.urls")),
    path("rapports/", include("dashboard.report_urls")),
    path("messages/", include("messaging.urls")),
    path("messagerie/", include("chat.urls")),
    path("visites/", include("technical_visits.urls")),
    path("assurances/", include("insurance.urls")),
    path("taxes/", include("taxes.urls")),
    path("ateliers/", include("workshops.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Sert les fichiers média (photos du chat, logos, images pièces) même en
# production. Convient à cette petite application ; les fichiers sont stockés
# sur un volume persistant monté sur /app/media dans Coolify.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", _media_serve, {"document_root": settings.MEDIA_ROOT}),
]
