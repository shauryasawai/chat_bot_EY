from django.urls import path
from . import views_api

urlpatterns = [
    path('api/chat/start/', views_api.start_chat, name='start_chat'),
    path('api/chat/', views_api.chat, name='chat'),
]