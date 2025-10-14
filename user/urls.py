from django.urls import path
from .views import (
    UserListCreateAPIView,
    UserProfileView,
    UserRetrieveUpdateDeleteAPIView,
    UserChangePassword
)

urlpatterns = [
    path('', UserListCreateAPIView.as_view()),
    path('<pk>', UserRetrieveUpdateDeleteAPIView.as_view()),
    path('profile/', UserProfileView.as_view()),
    path('change_password/', UserChangePassword.as_view()),
]