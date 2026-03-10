"""
URL patterns for the WiiU portal interface (/)
"""
from django.urls import path
from grape.views import auth_views, portal_views, error_views

urlpatterns = [
    # Root / Activity Feed
    path('', portal_views.root_view, name='portal_root'),

    # Auth
    path('act/login', auth_views.login_view, name='login'),
    path('act/logout', auth_views.logout_view, name='logout'),
    path('act/create', auth_views.create_account_view, name='create_account'),
    path('act/edit', auth_views.edit_account_view, name='edit_account'),

    # Menus
    path('my_menu', portal_views.my_menu_view, name='my_menu'),
    path('guest_menu', portal_views.guest_menu_view, name='guest_menu'),

    # Communities
    path('communities', portal_views.communities_view, name='communities'),
    path('titles/<str:title_id>/<str:community_id>', portal_views.community_posts_view, name='community_posts'),

    # Posts
    path('posts/<str:post_id>', portal_views.post_view, name='post_detail'),
    path('posts', portal_views.create_post_view, name='create_post'),
    path('posts/<str:post_id>/replies', portal_views.create_reply_view, name='create_reply'),
    path('posts/<str:post_id>/empathies', portal_views.add_empathy_view, name='add_empathy'),
    path('posts/<str:post_id>/empathies/delete', portal_views.remove_empathy_view, name='remove_empathy'),
    path('posts/<str:post_id>.delete', portal_views.delete_post_view, name='delete_post'),
    path('posts/<str:post_id>.set_spoiler', portal_views.set_spoiler_post_view, name='set_spoiler_post'),

    # Replies
    path('replies/<str:reply_id>/empathies', portal_views.add_reply_empathy_view, name='add_reply_empathy'),
    path('replies/<str:reply_id>/empathies/delete', portal_views.remove_reply_empathy_view, name='remove_reply_empathy'),

    # Users
    path('users/<str:user_id>', portal_views.user_profile_view, name='user_profile'),
    path('users/<str:user_id>/posts', portal_views.user_posts_view, name='user_posts'),
    path('users/<str:user_id>/followers', portal_views.user_followers_view, name='user_followers'),
    path('users/<str:user_id>/following', portal_views.user_following_view, name='user_following'),
    path('users/<str:user_id>.follow.json', portal_views.follow_user_view, name='follow_user'),
    path('users/<str:user_id>.unfollow.json', portal_views.unfollow_user_view, name='unfollow_user'),
    path('users/<str:user_id>/blacklist.create.json', portal_views.block_user_view, name='block_user'),
    path('users/<str:user_id>/blacklist.delete.json', portal_views.unblock_user_view, name='unblock_user'),

    # News & Messages
    path('news/my_news', portal_views.news_view, name='news'),
    path('friend_messages', portal_views.messages_view, name='messages'),
    path('friend_requests', portal_views.friend_requests_view, name='friend_requests'),

    # Settings
    path('settings/profile', portal_views.profile_settings_view, name='profile_settings'),
    path('settings/account', portal_views.account_settings_view, name='account_settings'),

    # Search
    path('users-search', portal_views.user_search_view, name='user_search'),

    # Blacklist
    path('my_blacklist', portal_views.my_blacklist_view, name='my_blacklist'),

    # Theme
    path('theme-set', portal_views.theme_set_view, name='theme_set'),

    # Rules
    path('rules', portal_views.rules_view, name='rules'),
]
