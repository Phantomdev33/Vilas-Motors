from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
router = DefaultRouter()
for prefix, view in [('equipment', views.EquipmentViewSet), ('readings', views.ReadingViewSet),
    ('maintenances', views.MaintenanceViewSet), ('users', views.UserViewSet), ('supplies', views.SupplyViewSet),
    ('alerts', views.AlertViewSet), ('audit', views.AuditViewSet)]:
    router.register(prefix, view)
urlpatterns = [path('', include(router.urls)), path('auth/csrf/', views.CSRFView.as_view()),
    path('auth/login/', views.LoginView.as_view()), path('auth/logout/', views.LogoutView.as_view()),
    path('auth/me/', views.MeView.as_view()), path('auth/reset/', views.PasswordResetView.as_view()),
    path('auth/reset/confirm/', views.PasswordResetConfirmView.as_view()), path('telemetry/', views.TelemetryView.as_view()),
    path('report/', views.ReportView.as_view()), path('migration-template/', views.MigrationTemplateView.as_view()),
    path('media/<path:path>', views.ProtectedMediaView.as_view())]
