from django.urls import path
from . import views

urlpatterns = [
   path('documents_upload', views.upload_document, name='upload_document'),
   path('search/', views.search_view, name='search_view'),
   path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
   path('update-role/',views.update_user_role, name='update_user_role'),
   path('delete-file/<str:model>/<int:file_id>/', views.delete_file, name='delete_file'),
   path('view-file/<str:model>/<int:file_id>/', views.view_file, name='view_file'),
   path('download-file/<str:category>/<int:file_id>/', views.download_file, name='download_file'),
   path('delete-pinecone-document/<int:doc_id>/', views.delete_pinecone_document, name='delete_pinecone_document'),
   path("delete_chat/<int:chat_id>/", views.delete_chat, name="delete_chat"),
]
