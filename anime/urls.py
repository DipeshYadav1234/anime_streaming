from django.urls import path
from . import views

app_name = 'anime'

urlpatterns = [
    path('', views.home, name='home'),
    path('anime/<int:mal_id>/', views.anime_detail, name='anime_detail'),
    path('anime/<int:mal_id>/watch/<int:episode_number>/', views.watch_episode, name='watch_episode'),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("watchlist/", views.watchlist, name="watchlist"),
    path("watchlist/add/<int:mal_id>/", views.add_to_watchlist, name="add_watchlist"),
    path("watchlist/remove/<int:mal_id>/", views.remove_from_watchlist, name="remove_watchlist"),
    path("trending/", views.trending, name="trending"),
    path("subscriptions/", views.subscription_plans, name="subscription_plans"),
    path("subscriptions/upgrade/<int:plan_id>/", views.upgrade_subscription, name="upgrade_subscription"),
    path("subscriptions/", views.subscription_plans, name="subscriptions"),
    path("upgrade/", views.create_payment, name="upgrade"),
    path("payment/success/", views.payment_success, name="payment_success"),

]