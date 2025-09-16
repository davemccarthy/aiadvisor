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
    
    # Trading functionality
    path('trading/', views.trading_view, name='trading'),
    path('trading/place-order/', views.place_order_view, name='place_order'),
    path('trading/order-history/', views.order_history_view, name='order_history'),
    path('trading/cancel-order/<uuid:trade_id>/', views.cancel_order_view, name='cancel_order'),
    path('trading/quick-trade/<str:symbol>/', views.quick_trade_view, name='quick_trade'),
    path('trading/simulate-market/', views.simulate_market, name='simulate_market'),
    
    # Recommendation actions
    path('recommendations/buy/<uuid:recommendation_id>/', views.quick_buy_from_recommendation, name='quick_buy_from_recommendation'),
    path('recommendations/sell/<uuid:recommendation_id>/', views.quick_sell_from_recommendation, name='quick_sell_from_recommendation'),
    
    # API endpoints
    path('api/stock-info/<str:symbol>/', views.get_stock_info, name='get_stock_info'),
    
    # Market data management
    path('trading/search-stocks/', views.search_stocks, name='search_stocks'),
    path('trading/update-stock/<str:symbol>/', views.update_stock_data, name='update_stock_data'),
    path('trading/market-data-status/', views.market_data_status, name='market_data_status'),
    
    # User management
    path('profile/', views.profile_view, name='profile'),
    path('notifications/', views.notifications_view, name='notifications'),
]
