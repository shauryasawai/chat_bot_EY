# urls.py

from django.urls import path
from . import views

app_name = 'base'

urlpatterns = [
    # Main chat interface
    path('', views.index, name='index'),
    
    # Chat endpoints
    path('start_chat/', views.start_chat, name='start_chat'),
    path('chat/', views.chat, name='chat'),
    
    # Document upload endpoints
    path('upload_pan_card/', views.upload_pan_card, name='upload_pan_card'),
    path('upload_selfie/', views.upload_selfie, name='upload_selfie'),
    path('upload_salary_slip/', views.upload_salary_slip, name='upload_salary_slip'),
    
    # Document download
    path('download_sanction_letter/<int:loan_id>/', views.download_sanction_letter, name='download_sanction_letter'),
]