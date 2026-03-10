"""
URL patterns for the offdevice (web browser) interface (/web/)
"""
from django.urls import path
from grape.views import auth_views, offdevice_views

urlpatterns = [
    # Root
    path('', offdevice_views.od_root_view, name='od_root'),

    # Auth
    path('act/login', auth_views.login_view, name='od_login'),
    path('act/logout', auth_views.logout_view, name='od_logout'),
    path('act/create', auth_views.create_account_view, name='od_create_account'),
    path('act/edit', auth_views.edit_account_view, name='od_edit_account'),

    # Menu
    path('my_menu', offdevice_views.od_my_menu_view, name='od_my_menu'),

    # Communities
    path('communities', offdevice_views.od_communities_view, name='od_communities'),
    path('titles/<str:title_id>/<str:community_id>', offdevice_views.od_community_posts_view, name='od_community_posts'),

    # Activity
    path('activity', offdevice_views.od_activity_view, name='od_activity'),

    # Posts
    path('posts/<str:post_id>', offdevice_views.od_post_view, name='od_post_detail'),
    path('posts', offdevice_views.od_create_post_view, name='od_create_post'),
    path('posts/<str:post_id>/replies', offdevice_views.od_create_reply_view, name='od_create_reply'),
    path('posts/<str:post_id>/empathies', offdevice_views.od_empathy_view, name='od_empathy'),
    path('replies/<str:reply_id>/empathies', offdevice_views.od_reply_empathy_view, name='od_reply_empathy'),

    # Users
    path('users/<str:user_id>', offdevice_views.od_user_profile_view, name='od_user_profile'),
    path('users/<str:user_id>/posts', offdevice_views.od_user_posts_view, name='od_user_posts'),
    path('users/<str:user_id>/friends', offdevice_views.od_user_friends_view, name='od_user_friends'),
    path('users/<str:user_id>/following', offdevice_views.od_user_following_view, name='od_user_following'),
    path('users/<str:user_id>/followers', offdevice_views.od_user_followers_view, name='od_user_followers'),
    path('users/<str:user_id>/follow', offdevice_views.od_follow_view, name='od_follow'),
    path('users/<str:user_id>/unfollow', offdevice_views.od_unfollow_view, name='od_unfollow'),

    # News
    path('news/my_news', offdevice_views.od_news_view, name='od_news'),

    # Settings
    path('settings/profile', offdevice_views.od_profile_settings_view, name='od_profile_settings'),
    path('settings/account', offdevice_views.od_account_settings_view, name='od_account_settings'),

    # Search
    path('users-search', offdevice_views.od_user_search_view, name='od_user_search'),

    # Rules
    path('rules', offdevice_views.od_rules_view, name='od_rules'),
]
