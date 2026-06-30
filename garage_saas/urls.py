from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="dashboard/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
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
    path("rapports/", include("dashboard.report_urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
