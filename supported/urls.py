from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.main, name='main'),
    path('solve/', views.solve, name='solve'),
    path('optimize_cost/', views.optimize_cost, name='optimize_cost'),
    path("download_report/", views.download_report, name="download_report"),
    path("clear_data/", views.clear_data, name="clear_data"),

]