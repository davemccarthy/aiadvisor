from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'soulstrader'

urlpatterns = [
    # Main pages
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='soulstrader/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Portfolio and trading
    path('portfolio/', views.portfolio_view, name='portfolio'),
    path('recommendations/', views.recommendations_view, name='recommendations'),
    path('stock/<str:symbol>/', views.stock_detail, name='stock_detail'),
    
    # User management
    path('profile/', views.profile_view, name='profile'),
    path('notifications/', views.notifications_view, name='notifications'),
]
