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
    path('portfolio/sell-shares/', views.sell_shares_view, name='sell_shares'),
    
    # Recommendation actions
    path('recommendations/buy-now/', views.buy_from_recommendations_view, name='buy_from_recommendations'),
    path('recommendations/sell-now/', views.sell_from_recommendations_view, name='sell_from_recommendations'),
    path('recommendations/smart-analysis/', views.smart_analysis_view, name='smart_analysis'),
    path('recommendations/advisor-details/<str:symbol>/', views.advisor_details_view, name='advisor_details'),
    path('recommendations/buy/<uuid:recommendation_id>/', views.quick_buy_from_recommendation, name='quick_buy_from_recommendation'),
    path('recommendations/sell/<uuid:recommendation_id>/', views.quick_sell_from_recommendation, name='quick_sell_from_recommendation'),
    
    # API endpoints
    path('api/stock-info/<str:symbol>/', views.get_stock_info, name='get_stock_info'),
    
    # Market data management
    path('trading/search-stocks/', views.search_stocks, name='search_stocks'),
    path('trading/update-stock/<str:symbol>/', views.update_stock_data, name='update_stock_data'),
    path('trading/market-data-status/', views.market_data_status, name='market_data_status'),
    
    # AI Advisors
    path('ai-advisors/', views.ai_advisors_dashboard, name='ai_advisors_dashboard'),
    path('ai-advisors/<int:advisor_id>/', views.advisor_detail, name='advisor_detail'),
    path('ai-advisors/consensus/', views.consensus_recommendations, name='consensus_recommendations'),
    path('ai-advisors/recommend/<str:symbol>/', views.get_stock_recommendations, name='get_stock_recommendations'),
    
    # User management
    path('profile/', views.profile_view, name='profile'),
    path('notifications/', views.notifications_view, name='notifications'),
]
