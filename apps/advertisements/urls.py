from django.urls import path
from apps.advertisements.views import (
    AdvertisementCreateView, AdvertisementUpdateView, AdvertisementListView, AdvertisementDetailView,
    UserAdvertisementListView
)

urlpatterns = [
    path('user/', UserAdvertisementListView.as_view(), name='user-advertisement-list'),
    
    path('', AdvertisementListView.as_view(), name='advertisement-list'),
    path('create/', AdvertisementCreateView.as_view(), name='advertisement-create'),
    path('<uuid:pk>/', AdvertisementDetailView.as_view(), name='advertisement-detail'),
    path('update/<uuid:pk>/', AdvertisementUpdateView.as_view(), name='advertisement-update'),
]
