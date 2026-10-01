from django.urls import path
from . import views

app_name = 'leads'

urlpatterns = [
    path('', views.lead_list, name='list'),
    path('create/', views.lead_create, name='create'),
    path('<int:pk>/', views.lead_detail, name='detail'),
    path('<int:pk>/status/', views.lead_update_status, name='update_status'),
    path('<int:pk>/note/', views.add_note, name='add_note'),
    path('assign/', views.assign_leads, name='assign'),
    path('excel/upload/', views.excel_upload, name='excel_upload'),
    path('excel/import/', views.excel_import_confirm, name='excel_import'),
    path('excel/export/', views.excel_export, name='excel_export'),
    path('excel/history/', views.import_history, name='import_history'),
    path('api/search/', views.lead_search_api, name='search_api'),
]
