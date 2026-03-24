from django.urls import path
from . import views

urlpatterns = [
    path('p2p/', views.index, name='p2p_index'),
]
