from django.contrib import admin
from django.urls import path

from pages import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    # Catch-all top-level slug -> a published Page. Keep last.
    path("<slug:slug>/", views.page_detail, name="page_detail"),
]
