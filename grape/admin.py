from django.contrib import admin
from grape.models import (
    Person, Community, Post, Reply, Title, Empathy,
    Relationship, FriendRelationship, FriendRequest, Profile,
    News, Blacklist, Conversation, Message
)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'screen_name', 'pid', 'official_user', 'ban_status', 'created_at']
    search_fields = ['user_id', 'screen_name']
    list_filter = ['official_user', 'ban_status', 'privilege']


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ['name', 'olive_community_id', 'olive_title_id', 'type']
    search_fields = ['name']


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'pid', 'community_id', 'is_hidden', 'created_at']
    list_filter = ['is_hidden', 'is_spoiler']
    search_fields = ['body']


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ['id', 'pid', 'reply_to_id', 'is_hidden', 'created_at']
    list_filter = ['is_hidden']


@admin.register(Title)
class TitleAdmin(admin.ModelAdmin):
    list_display = ['olive_title_id', 'name', 'platform_id']
    search_fields = ['name']


@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    list_display = ['source', 'target', 'created_at']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['pid', 'allow_request', 'empathy_optout']
