"""
API URL Configuration for SOULTRADER iOS App
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'api'

urlpatterns = [
    # =============================================================================
    # AUTHENTICATION ENDPOINTS
    # =============================================================================
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/user/', views.get_current_user, name='current_user'),
    
    # =============================================================================
    # PORTFOLIO ENDPOINTS (iOS Tab 1: Portfolio)
    # =============================================================================
    path('portfolio/holdings/', views.get_portfolio_holdings, name='portfolio_holdings'),
    path('portfolio/summary/', views.get_portfolio_summary, name='portfolio_summary'),
    
    # =============================================================================
    # TRADES ENDPOINTS (iOS Tab 2: Trades)
    # =============================================================================
    path('trades/', views.get_all_trades, name='all_trades'),
    path('trades/recent/', views.get_recent_trades, name='recent_trades'),
    
    # =============================================================================
    # SMART ANALYSIS ENDPOINTS (iOS Tab 3: Analysis)
    # =============================================================================
    path('analysis/smart/', views.get_smart_analysis, name='smart_analysis'),
    path('analysis/sessions/', views.get_analysis_sessions, name='analysis_sessions'),
    
    # =============================================================================
    # UTILITY ENDPOINTS
    # =============================================================================
    path('health/', views.api_health_check, name='health_check'),
]

