"""
Portal views - WiiU Miiverse interface
"""
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone

from grape.models import (
    Person, Community, Post, Reply, Title, Empathy,
    Relationship, FriendRelationship, FriendRequest, Profile,
    News, Blacklist, Message, Conversation, SettingsTitle
)
from grape.helpers import (
    get_mii, human_timing, miitoo_can, can_user_view, get_or_create_profile,
    send_news, profile_relationship_visible, truncate_text, generate_post_id,
    get_post_id_encoded, hash_pid
)


def require_login(request):
    """Return redirect or None - use in views that need auth"""
    if not request.session.get('pid'):
        if request.headers.get('X-PJAX'):
            return JsonResponse({'success': 0, 'errors': [{'message': 'You have been logged out.', 'error_code': 1510110}], 'code': 401}, status=401)
        return redirect(f'/act/login?location={request.path}')
    return None


def get_me(request):
    pid = request.session.get('pid')
    if not pid:
        return None
    try:
        return Person.objects.get(pid=pid)
    except Person.DoesNotExist:
        return None


def get_theme_css(request):
    ua = request.META.get('HTTP_USER_AGENT', '')
    if 'miiverse' in ua.lower():
        return '/static/css/portal-grp.css'
    theme = request.COOKIES.get('grp_theme', '')
    if theme in ('grape', 'blueberry', 'cherry', 'orange'):
        return f'/static/css/portal-grp_offdevice_{theme}.css'
    return '/static/css/portal-grp_offdevice.css'


def is_pjax(request):
    return bool(request.headers.get('X-PJAX') or request.META.get('HTTP_X_PJAX'))


def is_ajax(request):
    return bool(request.headers.get('X-Requested-With') == 'XMLHttpRequest')


# ---- ROOT / ACTIVITY FEED ----

def root_view(request):
    me = get_me(request)
    theme_css = get_theme_css(request)

    if not me:
        # Show communities to guests
        return communities_view(request)

    # For AJAX activity feed request
    if is_ajax(request) and not is_pjax(request):
        return activity_feed_ajax(request, me)

    return render(request, 'portal/root.html', {
        'theme_css': theme_css,
        'pagetitle': 'Activity Feed',
    })


def activity_feed_ajax(request, me):
    """Load activity feed posts via AJAX"""
    from django.db.models import Max
    offset = int(request.GET.get('offset', 0))

    # Get followed users + friends pids
    following_pids = list(Relationship.objects.filter(source=me.pid, is_me2me=False).values_list('target', flat=True))
    friend_pids_1 = list(FriendRelationship.objects.filter(source=me.pid).values_list('target', flat=True))
    friend_pids_2 = list(FriendRelationship.objects.filter(target=me.pid).values_list('source', flat=True))
    all_pids = list(set(following_pids + friend_pids_1 + friend_pids_2))

    posts = []
    if all_pids:
        # Get latest post per person
        latest_posts = Post.objects.filter(
            pid__in=all_pids,
            is_hidden=False
        ).order_by('-created_at')[offset:offset + 50]
        posts = list(latest_posts)

    act_feed_community = Community.objects.filter(type=5).first()

    posts_ctx = []
    for post in posts:
        if can_user_view(me.pid, post.pid):
            continue
        try:
            user = Person.objects.get(pid=post.pid)
        except Person.DoesNotExist:
            continue
        try:
            community = Community.objects.get(community_id=post.community_id)
        except Community.DoesNotExist:
            continue

        usermii = get_mii(user, post.feeling_id)
        empathy_count = Empathy.objects.filter(id=post.id).count()
        reply_count = Reply.objects.filter(reply_to_id=post.id).count()
        my_empathy = Empathy.objects.filter(id=post.id, pid=me.pid).exists()
        can_yeah = miitoo_can(me.pid, post.id, 'posts')

        posts_ctx.append({
            'post': post,
            'user': user,
            'usermii': usermii,
            'community': community,
            'empathy_count': empathy_count,
            'reply_count': reply_count,
            'my_empathy': my_empathy,
            'can_yeah': can_yeah,
            'human_time': human_timing(post.created_at),
        })

    return render(request, 'portal/partials/activity_feed.html', {
        'posts_ctx': posts_ctx,
        'act_feed_community': act_feed_community,
        'me': me,
        'me_mii': get_mii(me, 0),
        'next_offset': offset + 50 if len(posts) >= 50 else None,
    })


# ---- COMMUNITIES ----

def communities_view(request):
    me = get_me(request)
    theme_css = get_theme_css(request)

    communities = Community.objects.exclude(type=5).order_by('name')

    return render(request, 'portal/communities.html', {
        'communities': communities,
        'theme_css': theme_css,
        'pagetitle': 'Community',
        'me': me,
    })


def community_posts_view(request, title_id, community_id):
    me = get_me(request)
    theme_css = get_theme_css(request)

    community = get_object_or_404(Community, olive_community_id=community_id)
    try:
        title = Title.objects.get(olive_title_id=community.olive_title_id)
    except Title.DoesNotExist:
        title = None

    offset = int(request.GET.get('offset', 0))
    posts_qs = Post.objects.filter(
        community_id=community.community_id,
        is_hidden=False
    ).order_by('-created_at')[offset:offset + 50]

    posts_ctx = _build_posts_ctx(posts_qs, me)

    pref_id = 0
    if me:
        try:
            st = SettingsTitle.objects.get(pid=me.pid, olive_title_id=community.olive_title_id)
            pref_id = st.value
        except SettingsTitle.DoesNotExist:
            pass

    return render(request, 'portal/community_posts.html', {
        'community': community,
        'title': title,
        'posts_ctx': posts_ctx,
        'theme_css': theme_css,
        'pagetitle': community.name,
        'me': me,
        'pref_id': pref_id,
    })


def _build_posts_ctx(posts_qs, me):
    posts_ctx = []
    for post in posts_qs:
        if me and can_user_view(me.pid, post.pid):
            continue
        try:
            user = Person.objects.get(pid=post.pid)
        except Person.DoesNotExist:
            continue
        try:
            community = Community.objects.get(community_id=post.community_id)
        except Community.DoesNotExist:
            continue

        usermii = get_mii(user, post.feeling_id)
        empathy_count = Empathy.objects.filter(id=post.id).count()
        reply_count = Reply.objects.filter(reply_to_id=post.id).count()
        my_empathy = Empathy.objects.filter(id=post.id, pid=me.pid).exists() if me else False
        can_yeah = miitoo_can(me.pid, post.id, 'posts') if me else False

        # Recent reply for preview
        recent_reply = None
        if not post.is_hidden:
            recent_replies_all = Reply.objects.filter(reply_to_id=post.id, is_hidden=False).order_by('-created_at')
            other_replies = recent_replies_all.exclude(pid=post.pid).exclude(is_spoiler=True)
            if other_replies.exists():
                rr = other_replies.first()
                try:
                    rr_user = Person.objects.get(pid=rr.pid)
                    recent_reply = {
                        'reply': rr,
                        'user': rr_user,
                        'mii': get_mii(rr_user, rr.feeling_id),
                        'human_time': human_timing(rr.created_at),
                        'total_count': recent_replies_all.count(),
                    }
                except Person.DoesNotExist:
                    pass

        posts_ctx.append({
            'post': post,
            'user': user,
            'usermii': usermii,
            'community': community,
            'empathy_count': empathy_count,
            'reply_count': reply_count,
            'my_empathy': my_empathy,
            'can_yeah': can_yeah,
            'human_time': human_timing(post.created_at),
            'recent_reply': recent_reply,
        })
    return posts_ctx


# ---- POSTS ----

def post_view(request, post_id):
    me = get_me(request)
    theme_css = get_theme_css(request)

    post = get_object_or_404(Post, id=post_id)
    if me and can_user_view(me.pid, post.pid):
        return render(request, 'portal/404.html', status=404)

    try:
        user = Person.objects.get(pid=post.pid)
    except Person.DoesNotExist:
        return render(request, 'portal/404.html', status=404)

    try:
        community = Community.objects.get(community_id=post.community_id)
    except Community.DoesNotExist:
        return render(request, 'portal/404.html', status=404)

    usermii = get_mii(user, post.feeling_id)
    empathies = list(Empathy.objects.filter(id=post_id).select_related())
    replies_qs = Reply.objects.filter(reply_to_id=post_id).order_by('created_at')

    pref_id = 0
    if me:
        try:
            st = SettingsTitle.objects.get(pid=me.pid, olive_title_id=community.olive_title_id)
            pref_id = st.value
        except SettingsTitle.DoesNotExist:
            pass

    my_empathy = Empathy.objects.filter(id=post_id, pid=me.pid).exists() if me else False
    can_yeah = miitoo_can(me.pid, post_id, 'posts') if me else False

    replies_ctx = []
    for reply in replies_qs:
        if reply.hidden_resp == '1':
            continue
        if me and can_user_view(me.pid, reply.pid):
            continue
        try:
            r_user = Person.objects.get(pid=reply.pid)
        except Person.DoesNotExist:
            continue
        r_mii = get_mii(r_user, reply.feeling_id)
        r_empathy_count = Empathy.objects.filter(id=reply.id).count()
        r_my_empathy = Empathy.objects.filter(id=reply.id, pid=me.pid).exists() if me else False
        r_can_yeah = miitoo_can(me.pid, reply.id, 'replies') if me else False
        show_spoiler = (me and me.pid == reply.pid) or pref_id == 1
        replies_ctx.append({
            'reply': reply,
            'user': r_user,
            'mii': r_mii,
            'empathy_count': r_empathy_count,
            'my_empathy': r_my_empathy,
            'can_yeah': r_can_yeah,
            'human_time': human_timing(reply.created_at),
            'show_spoiler': show_spoiler,
        })

    show_spoiler = (me and me.pid == post.pid) or pref_id == 1

    return render(request, 'portal/post.html', {
        'post': post,
        'user': user,
        'usermii': usermii,
        'community': community,
        'empathies': empathies,
        'empathy_count': len(empathies),
        'replies_ctx': replies_ctx,
        'my_empathy': my_empathy,
        'can_yeah': can_yeah,
        'show_spoiler': show_spoiler,
        'human_time': human_timing(post.created_at),
        'theme_css': theme_css,
        'pagetitle': f"{user.screen_name}'s Post",
        'me': me,
        'post_id_encoded': get_post_id_encoded(post_id),
        'pref_id': pref_id,
    })


@require_POST
def create_post_view(request):
    me = get_me(request)
    if not me:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    community_id = request.POST.get('community_id')
    body = request.POST.get('body', '').strip()
    feeling_id = int(request.POST.get('feeling_id', 0))
    screenshot = request.POST.get('screenshot', '').strip()
    url = request.POST.get('url', '').strip()
    is_spoiler = request.POST.get('is_spoiler') == '1'
    post_type = request.POST.get('_post_type', 'body')

    try:
        community = Community.objects.get(community_id=community_id)
    except Community.DoesNotExist:
        return JsonResponse({'success': 0, 'code': 404}, status=404)

    if not body and post_type != 'artwork':
        return JsonResponse({'success': 0, 'errors': [{'message': 'Post body is required.'}]}, status=400)

    post_id = generate_post_id()
    Post.objects.create(
        id=post_id,
        pid=me.pid,
        community_id=community.community_id,
        body=body,
        _post_type=post_type,
        feeling_id=feeling_id,
        screenshot=screenshot or None,
        url=url or None,
        is_spoiler=is_spoiler,
        created_from=request.META.get('REMOTE_ADDR'),
    )

    return JsonResponse({'success': 1, 'post_id': post_id})


@require_POST
def create_reply_view(request, post_id):
    me = get_me(request)
    if not me:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    post = get_object_or_404(Post, id=post_id)
    body = request.POST.get('body', '').strip()
    feeling_id = int(request.POST.get('feeling_id', 0))
    screenshot = request.POST.get('screenshot', '').strip()
    is_spoiler = request.POST.get('is_spoiler') == '1'

    if not body:
        return JsonResponse({'success': 0, 'errors': [{'message': 'Reply body is required.'}]}, status=400)

    reply_id = generate_post_id()
    Reply.objects.create(
        id=reply_id,
        pid=me.pid,
        reply_to_id=post_id,
        community_id=post.community_id,
        body=body,
        feeling_id=feeling_id,
        screenshot=screenshot or None,
        is_spoiler=is_spoiler,
        created_from=request.META.get('REMOTE_ADDR'),
    )

    send_news(me.pid, post.pid, 4, post_id)

    return JsonResponse({'success': 1, 'reply_id': reply_id})


# ---- YEAH (EMPATHY) ----

@require_POST
def add_empathy_view(request, post_id):
    me = get_me(request)
    if not me:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    post = get_object_or_404(Post, id=post_id)
    if not miitoo_can(me.pid, post_id, 'posts'):
        return JsonResponse({'success': 0, 'code': 400}, status=400)

    _, created = Empathy.objects.get_or_create(id=post_id, pid=me.pid)
    if not created:
        return JsonResponse({'success': 0, 'code': 400}, status=400)

    send_news(me.pid, post.pid, 2, post_id)
    return JsonResponse({'success': 1})


@require_POST
def remove_empathy_view(request, post_id):
    me = get_me(request)
    if not me:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    deleted, _ = Empathy.objects.filter(id=post_id, pid=me.pid).delete()
    if deleted == 0:
        return JsonResponse({'success': 0, 'code': 400}, status=400)
    return JsonResponse({'success': 1})


@require_POST
def add_reply_empathy_view(request, reply_id):
    me = get_me(request)
    if not me:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    reply = get_object_or_404(Reply, id=reply_id)
    if not miitoo_can(me.pid, reply_id, 'replies'):
        return JsonResponse({'success': 0, 'code': 400}, status=400)

    _, created = Empathy.objects.get_or_create(id=reply_id, pid=me.pid)
    if not created:
        return JsonResponse({'success': 0, 'code': 400}, status=400)

    send_news(me.pid, reply.pid, 3, reply_id)
    return JsonResponse({'success': 1})


@require_POST
def remove_reply_empathy_view(request, reply_id):
    me = get_me(request)
    if not me:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    deleted, _ = Empathy.objects.filter(id=reply_id, pid=me.pid).delete()
    if deleted == 0:
        return JsonResponse({'success': 0, 'code': 400}, status=400)
    return JsonResponse({'success': 1})


# ---- DELETE / SPOILER POST ----

@require_POST
def delete_post_view(request, post_id):
    me = get_me(request)
    if not me:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    post = get_object_or_404(Post, id=post_id)
    if post.pid != me.pid and me.privilege < 2:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    if post.pid == me.pid:
        post.delete()
    else:
        post.is_hidden = True
        post.hidden_resp = '0'
        post.save()

    return JsonResponse({'success': 1})


@require_POST
def set_spoiler_post_view(request, post_id):
    me = get_me(request)
    if not me:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    post = get_object_or_404(Post, id=post_id, pid=me.pid)
    post.is_spoiler = True
    post.save()
    return JsonResponse({'success': 1})


# ---- USERS ----

def user_profile_view(request, user_id):
    me = get_me(request)
    theme_css = get_theme_css(request)

    user = get_object_or_404(Person, user_id=user_id)
    if me and can_user_view(me.pid, user.pid):
        return render(request, 'portal/404.html', status=404)

    profile = get_or_create_profile(user)
    usermii = get_mii(user, 0)

    # Favorite post
    favorite_post = None
    if profile.favorite_screenshot:
        try:
            fp = Post.objects.get(id=profile.favorite_screenshot, is_hidden=False)
            favorite_post = fp
        except Post.DoesNotExist:
            pass

    # Friend/follow state
    is_me = me and me.pid == user.pid
    relationship = None
    friend_case = 0
    if me and not is_me:
        if Relationship.objects.filter(source=me.pid, target=user.pid).exists():
            relationship = 'following'
        friend_req_me = FriendRequest.objects.filter(sender=me.pid, recipient=user.pid, finished=False).first()
        friend_req_other = FriendRequest.objects.filter(sender=user.pid, recipient=me.pid, finished=False).first()
        friend_rel = FriendRelationship.objects.filter(
            Q(source=me.pid, target=user.pid) | Q(source=user.pid, target=me.pid)
        ).first()
        if friend_req_me:
            friend_case = 1
        elif friend_req_other:
            friend_case = 2
        elif friend_rel:
            friend_case = 3

    can_view = is_me or (me and profile_relationship_visible(me.pid, user.pid, profile.relationship_visibility))
    num_posts = Post.objects.filter(pid=user.pid, is_hidden=False).count()
    num_friends = FriendRelationship.objects.filter(Q(source=user.pid) | Q(target=user.pid)).count()
    num_following = Relationship.objects.filter(source=user.pid, is_me2me=False).count()
    num_followers = Relationship.objects.filter(target=user.pid, is_me2me=False).count()

    return render(request, 'portal/user_profile.html', {
        'profile_user': user,
        'profile': profile,
        'usermii': usermii,
        'favorite_post': favorite_post,
        'is_me': is_me,
        'relationship': relationship,
        'friend_case': friend_case,
        'friend_req_other': friend_req_other if me and not is_me else None,
        'can_view': can_view,
        'num_posts': num_posts,
        'num_friends': num_friends,
        'num_following': num_following,
        'num_followers': num_followers,
        'theme_css': theme_css,
        'pagetitle': f"{user.screen_name}'s Profile",
        'me': me,
        'page': 'profile',
    })


def user_posts_view(request, user_id):
    me = get_me(request)
    theme_css = get_theme_css(request)

    user = get_object_or_404(Person, user_id=user_id)
    profile = get_or_create_profile(user)
    usermii = get_mii(user, 0)
    offset = int(request.GET.get('offset', 0))

    posts_qs = Post.objects.filter(pid=user.pid, is_hidden=False).order_by('-created_at')[offset:offset + 50]
    posts_ctx = _build_posts_ctx(posts_qs, me)

    empathies_count = Empathy.objects.filter(pid=user.pid).count()
    num_posts = Post.objects.filter(pid=user.pid, is_hidden=False).count()

    return render(request, 'portal/user_posts.html', {
        'profile_user': user,
        'profile': profile,
        'usermii': usermii,
        'posts_ctx': posts_ctx,
        'theme_css': theme_css,
        'pagetitle': f"{user.screen_name}'s Posts",
        'me': me,
        'page': 'posts',
        'num_posts': num_posts,
        'empathies_count': empathies_count,
    })


def user_followers_view(request, user_id):
    me = get_me(request)
    theme_css = get_theme_css(request)
    user = get_object_or_404(Person, user_id=user_id)

    followers_pids = Relationship.objects.filter(target=user.pid, is_me2me=False).values_list('source', flat=True)
    followers = Person.objects.filter(pid__in=followers_pids)

    return render(request, 'portal/user_followers.html', {
        'profile_user': user,
        'followers': followers,
        'theme_css': theme_css,
        'pagetitle': f"{user.screen_name}'s Followers",
        'me': me,
        'page': 'followers',
    })


def user_following_view(request, user_id):
    me = get_me(request)
    theme_css = get_theme_css(request)
    user = get_object_or_404(Person, user_id=user_id)

    following_pids = Relationship.objects.filter(source=user.pid, is_me2me=False).values_list('target', flat=True)
    following = Person.objects.filter(pid__in=following_pids)

    return render(request, 'portal/user_following.html', {
        'profile_user': user,
        'following': following,
        'theme_css': theme_css,
        'pagetitle': f"{user.screen_name} Following",
        'me': me,
        'page': 'following',
    })


# ---- FOLLOW / UNFOLLOW ----

@require_POST
def follow_user_view(request, user_id):
    me = get_me(request)
    if not me:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    target = get_object_or_404(Person, user_id=user_id)
    if target.pid == me.pid:
        return JsonResponse({'success': 0, 'code': 400}, status=400)

    Relationship.objects.get_or_create(source=me.pid, target=target.pid)
    send_news(me.pid, target.pid, 6, None)
    return JsonResponse({'success': 1})


@require_POST
def unfollow_user_view(request, user_id):
    me = get_me(request)
    if not me:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    target = get_object_or_404(Person, user_id=user_id)
    Relationship.objects.filter(source=me.pid, target=target.pid).delete()
    return JsonResponse({'success': 1})


# ---- MY MENU / USER MENU ----

def my_menu_view(request):
    me = get_me(request)
    if not me:
        return redirect('/guest_menu')

    theme_css = get_theme_css(request)
    return render(request, 'portal/my_menu.html', {
        'theme_css': theme_css,
        'pagetitle': 'User Menu',
        'me': me,
    })


def guest_menu_view(request):
    theme_css = get_theme_css(request)
    return render(request, 'portal/guest_menu.html', {
        'theme_css': theme_css,
        'pagetitle': 'Guest Menu',
    })


# ---- NEWS ----

def news_view(request):
    me = get_me(request)
    if not me:
        auth_fail = require_login(request)
        return auth_fail

    theme_css = get_theme_css(request)
    news_items = News.objects.filter(to_pid=me.pid, merged__isnull=True).order_by('-created_at')[:50]

    News.objects.filter(to_pid=me.pid, has_read=False).update(has_read=True)

    news_ctx = []
    for item in news_items:
        try:
            from_user = Person.objects.get(pid=item.from_pid)
        except Person.DoesNotExist:
            continue
        merged = list(News.objects.filter(merged=item.news_id).order_by('created_at')[:20])
        news_ctx.append({
            'item': item,
            'from_user': from_user,
            'from_mii': get_mii(from_user, 0),
            'merged': merged,
            'human_time': human_timing(item.created_at),
        })

    return render(request, 'portal/news.html', {
        'news_ctx': news_ctx,
        'theme_css': theme_css,
        'pagetitle': 'News',
        'me': me,
    })


# ---- MESSAGES ----

def messages_view(request):
    me = get_me(request)
    if not me:
        return require_login(request)

    theme_css = get_theme_css(request)

    conversations = Conversation.objects.filter(
        Q(sender=me.pid) | Q(recipient=me.pid)
    ).order_by('-created_at')

    convs_ctx = []
    for conv in conversations:
        other_pid = conv.recipient if conv.sender == me.pid else conv.sender
        try:
            other = Person.objects.get(pid=other_pid)
        except Person.DoesNotExist:
            continue
        last_msg = Message.objects.filter(conversation_id=conv.conversation_id).order_by('-created_at').first()
        convs_ctx.append({
            'conv': conv,
            'other': other,
            'other_mii': get_mii(other, 0),
            'last_msg': last_msg,
        })

    return render(request, 'portal/messages.html', {
        'convs_ctx': convs_ctx,
        'theme_css': theme_css,
        'pagetitle': 'Messages',
        'me': me,
    })


# ---- USER SEARCH ----

def user_search_view(request):
    me = get_me(request)
    theme_css = get_theme_css(request)
    query = request.GET.get('query', '').strip()
    offset = int(request.GET.get('offset', 0))

    users = []
    if query:
        users = Person.objects.filter(
            Q(user_id__istartswith=query) | Q(screen_name__istartswith=query)
        ).order_by('-created_at')[offset:offset + 50]

    return render(request, 'portal/user_search.html', {
        'users': users,
        'query': query,
        'theme_css': theme_css,
        'pagetitle': 'Search Users',
        'me': me,
    })


# ---- PROFILE SETTINGS ----

def profile_settings_view(request):
    me = get_me(request)
    if not me:
        return redirect('/act/login')

    theme_css = get_theme_css(request)
    profile = get_or_create_profile(me)

    if request.method == 'POST':
        comment = request.POST.get('comment', '').strip()[:1000]
        allow_request = int(request.POST.get('allow_request', 1))
        rel_vis = request.POST.get('relationship_visibility', '1')
        gender = request.POST.get('gender', '3')
        country = request.POST.get('country', '')[:50]
        game_skill = request.POST.get('game_skill', '1')

        try:
            rel_vis = max(1, min(3, int(rel_vis)))
        except (ValueError, TypeError):
            rel_vis = 1
        try:
            gender = str(max(1, min(3, int(gender))))
        except (ValueError, TypeError):
            gender = '3'
        try:
            game_skill = str(max(0, min(2, int(game_skill))))
        except (ValueError, TypeError):
            game_skill = '1'

        profile.comment = comment
        profile.allow_request = allow_request
        profile.relationship_visibility = rel_vis
        profile.gender = gender
        profile.country = country
        profile.game_experience = game_skill
        profile.save()

        return redirect(f'/users/{me.user_id}')

    favorite_screenshot = None
    if profile.favorite_screenshot:
        try:
            from grape.models import Post
            fp = Post.objects.get(id=profile.favorite_screenshot, is_hidden=False)
            if fp.screenshot:
                favorite_screenshot = fp.screenshot
        except Exception:
            pass

    return render(request, 'portal/profile_settings.html', {
        'profile': profile,
        'favorite_screenshot': favorite_screenshot,
        'theme_css': theme_css,
        'pagetitle': 'Profile Settings',
        'me': me,
    })


# ---- ACCOUNT SETTINGS ----

def account_settings_view(request):
    me = get_me(request)
    if not me:
        return redirect('/act/login')

    theme_css = get_theme_css(request)
    profile = get_or_create_profile(me)

    if request.method == 'POST':
        empathy_optout = request.POST.get('empathy_optout') == '1'
        profile.empathy_optout = empathy_optout
        profile.save()
        return redirect('/my_menu')

    return render(request, 'portal/account_settings.html', {
        'profile': profile,
        'theme_css': theme_css,
        'pagetitle': 'Account Settings',
        'me': me,
    })


# ---- THEME ----

def theme_set_view(request):
    theme = request.GET.get('theme', 'default')
    if theme not in ('default', 'grape', 'blueberry', 'cherry', 'orange'):
        theme = 'default'
    response = redirect(request.META.get('HTTP_REFERER', '/'))
    response.set_cookie('grp_theme', theme, max_age=664800)
    return response


# ---- BLACKLIST ----

def my_blacklist_view(request):
    me = get_me(request)
    if not me:
        return redirect('/act/login')

    theme_css = get_theme_css(request)
    blocked_pids = Blacklist.objects.filter(source=me.pid).values_list('target', flat=True)
    blocked_users = Person.objects.filter(pid__in=blocked_pids)

    return render(request, 'portal/my_blacklist.html', {
        'blocked_users': blocked_users,
        'theme_css': theme_css,
        'pagetitle': 'Blocked Users',
        'me': me,
    })


@require_POST
def block_user_view(request, user_id):
    me = get_me(request)
    if not me:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    target = get_object_or_404(Person, user_id=user_id)
    Blacklist.objects.get_or_create(source=me.pid, target=target.pid)
    Relationship.objects.filter(source=me.pid, target=target.pid).delete()
    return JsonResponse({'success': 1})


@require_POST
def unblock_user_view(request, user_id):
    me = get_me(request)
    if not me:
        return JsonResponse({'success': 0, 'code': 403}, status=403)

    target = get_object_or_404(Person, user_id=user_id)
    Blacklist.objects.filter(source=me.pid, target=target.pid).delete()
    return JsonResponse({'success': 1})


# ---- FRIEND REQUESTS ----

def friend_requests_view(request):
    me = get_me(request)
    if not me:
        return redirect('/act/login')

    theme_css = get_theme_css(request)
    requests_qs = FriendRequest.objects.filter(recipient=me.pid, finished=False).order_by('-created_at')

    reqs_ctx = []
    for fr in requests_qs:
        try:
            sender = Person.objects.get(pid=fr.sender)
            reqs_ctx.append({
                'fr': fr,
                'sender': sender,
                'sender_mii': get_mii(sender, 0),
            })
        except Person.DoesNotExist:
            pass

    FriendRequest.objects.filter(recipient=me.pid, has_read=False).update(has_read=True)

    return render(request, 'portal/friend_requests.html', {
        'reqs_ctx': reqs_ctx,
        'theme_css': theme_css,
        'pagetitle': 'Friend Requests',
        'me': me,
    })


# ---- RULES PAGE ----

def rules_view(request):
    me = get_me(request)
    theme_css = get_theme_css(request)
    return render(request, 'portal/rules.html', {
        'theme_css': theme_css,
        'pagetitle': 'Rules & Guidelines',
        'me': me,
    })
