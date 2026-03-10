"""
Offdevice views - standard web browser interface at /web/
These mirror the portal views but use offdevice templates
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_POST

from grape.models import (
    Person, Community, Post, Reply, Title, Empathy,
    Relationship, FriendRelationship, FriendRequest, Profile,
    News, Blacklist, Conversation, Message, SettingsTitle, Favorite
)
from grape.helpers import (
    get_mii, human_timing, miitoo_can, can_user_view, get_or_create_profile,
    send_news, profile_relationship_visible, truncate_text, generate_post_id,
    get_post_id_encoded, hash_pid
)
from grape.views.portal_views import (
    get_me, _build_posts_ctx, require_login
)


def od_root_view(request):
    me = get_me(request)
    communities = Community.objects.exclude(type=5).order_by('name')
    return render(request, 'offdevice/communities.html', {
        'communities': communities,
        'pagetitle': 'Communities',
        'me': me,
        'me_mii': get_mii(me, 0) if me else None,
    })


def od_activity_view(request):
    me = get_me(request)
    if not me:
        return redirect('/web/act/login?location=/web/activity')

    offset = int(request.GET.get('offset', 0))
    following_pids = list(Relationship.objects.filter(source=me.pid, is_me2me=False).values_list('target', flat=True))
    friend_pids_1 = list(FriendRelationship.objects.filter(source=me.pid).values_list('target', flat=True))
    friend_pids_2 = list(FriendRelationship.objects.filter(target=me.pid).values_list('source', flat=True))
    all_pids = list(set(following_pids + friend_pids_1 + friend_pids_2))

    posts = []
    if all_pids:
        posts = list(Post.objects.filter(pid__in=all_pids, is_hidden=False).order_by('-created_at')[offset:offset + 50])

    posts_ctx = _build_posts_ctx(posts, me)

    return render(request, 'offdevice/activity.html', {
        'posts_ctx': posts_ctx,
        'pagetitle': 'Activity Feed',
        'me': me,
        'me_mii': get_mii(me, 0),
        'mnselect': 'feed',
    })


def od_communities_view(request):
    me = get_me(request)

    # Favorites (if logged in)
    fav_communities = []
    if me:
        fav_ids = Favorite.objects.filter(pid=me.pid).values_list('community_id', flat=True).order_by('-created_at')
        for cid in fav_ids:
            try:
                fav_communities.append(Community.objects.get(community_id=cid))
            except Community.DoesNotExist:
                pass

    # WiiU/3DS titles (platform_id NOT NULL, not hidden)
    wiiu_titles = Title.objects.filter(
        platform_id__isnull=False, hidden=False
    ).order_by('-created_at')[:20]

    # Special communities (platform_id IS NULL, not hidden)
    special_titles = Title.objects.filter(
        platform_id__isnull=True, hidden=False
    ).order_by('-created_at')[:20]

    return render(request, 'offdevice/communities.html', {
        'fav_communities': fav_communities,
        'wiiu_titles': wiiu_titles,
        'special_titles': special_titles,
        'pagetitle': 'Communities',
        'me': me,
        'me_mii': get_mii(me, 0) if me else None,
        'mnselect': 'community',
    })


def od_community_posts_view(request, title_id, community_id):
    me = get_me(request)
    community = get_object_or_404(Community, olive_community_id=community_id)
    try:
        title = Title.objects.get(olive_title_id=community.olive_title_id)
    except Title.DoesNotExist:
        title = None

    offset = int(request.GET.get('offset', 0))
    posts_qs = Post.objects.filter(
        community_id=community.community_id, is_hidden=False
    ).order_by('-created_at')[offset:offset + 50]

    posts_ctx = _build_posts_ctx(posts_qs, me)

    return render(request, 'offdevice/community_posts.html', {
        'community': community,
        'title': title,
        'posts_ctx': posts_ctx,
        'pagetitle': community.name,
        'me': me,
        'me_mii': get_mii(me, 0) if me else None,
    })


def od_post_view(request, post_id):
    me = get_me(request)
    post = get_object_or_404(Post, id=post_id)
    if me and can_user_view(me.pid, post.pid):
        return render(request, 'offdevice/404.html', status=404)

    try:
        user = Person.objects.get(pid=post.pid)
    except Person.DoesNotExist:
        return render(request, 'offdevice/404.html', status=404)

    try:
        community = Community.objects.get(community_id=post.community_id)
    except Community.DoesNotExist:
        return render(request, 'offdevice/404.html', status=404)

    usermii = get_mii(user, post.feeling_id)
    empathy_count = Empathy.objects.filter(id=post_id).count()
    replies_qs = Reply.objects.filter(reply_to_id=post_id, is_hidden=False).order_by('created_at')

    my_empathy = Empathy.objects.filter(id=post_id, pid=me.pid).exists() if me else False
    can_yeah = miitoo_can(me.pid, post_id, 'posts') if me else False

    pref_id = 0
    if me:
        try:
            st = SettingsTitle.objects.get(pid=me.pid, olive_title_id=community.olive_title_id)
            pref_id = st.value
        except SettingsTitle.DoesNotExist:
            pass

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

    return render(request, 'offdevice/post.html', {
        'post': post,
        'user': user,
        'usermii': usermii,
        'community': community,
        'empathy_count': empathy_count,
        'replies_ctx': replies_ctx,
        'my_empathy': my_empathy,
        'can_yeah': can_yeah,
        'show_spoiler': (me and me.pid == post.pid) or pref_id == 1,
        'human_time': human_timing(post.created_at),
        'pagetitle': f"{user.screen_name}'s Post",
        'me': me,
        'me_mii': get_mii(me, 0) if me else None,
    })


def od_user_profile_view(request, user_id):
    me = get_me(request)
    user = get_object_or_404(Person, user_id=user_id)
    if me and can_user_view(me.pid, user.pid):
        return render(request, 'offdevice/404.html', status=404)

    profile = get_or_create_profile(user)
    usermii = get_mii(user, 0)
    is_me = me and me.pid == user.pid

    favorite_post = None
    if profile.favorite_screenshot:
        try:
            fp = Post.objects.get(id=profile.favorite_screenshot, is_hidden=False)
            if fp.screenshot:
                favorite_post = fp
        except Post.DoesNotExist:
            pass

    following = False
    if me and not is_me:
        following = Relationship.objects.filter(source=me.pid, target=user.pid).exists()

    num_posts = Post.objects.filter(pid=user.pid, is_hidden=False).count()
    num_friends = FriendRelationship.objects.filter(Q(source=user.pid) | Q(target=user.pid)).count()
    num_following = Relationship.objects.filter(source=user.pid, is_me2me=False).count()
    num_followers = Relationship.objects.filter(target=user.pid, is_me2me=False).count()

    can_view = is_me or (me and profile_relationship_visible(me.pid, user.pid, profile.relationship_visibility))

    return render(request, 'offdevice/user_profile.html', {
        'profile_user': user,
        'profile': profile,
        'usermii': usermii,
        'favorite_post': favorite_post,
        'is_me': is_me,
        'following': following,
        'num_posts': num_posts,
        'num_friends': num_friends,
        'num_following': num_following,
        'num_followers': num_followers,
        'can_view': can_view,
        'pagetitle': f"{user.screen_name}'s Profile",
        'me': me,
        'me_mii': get_mii(me, 0) if me else None,
        'page': 'profile',
        'mnselect': 'users',
    })


def od_user_posts_view(request, user_id):
    me = get_me(request)
    user = get_object_or_404(Person, user_id=user_id)
    profile = get_or_create_profile(user)
    offset = int(request.GET.get('offset', 0))

    posts_qs = Post.objects.filter(pid=user.pid, is_hidden=False).order_by('-created_at')[offset:offset + 50]
    posts_ctx = _build_posts_ctx(posts_qs, me)
    num_posts = Post.objects.filter(pid=user.pid, is_hidden=False).count()
    num_empathies = Empathy.objects.filter(pid=user.pid).count()

    return render(request, 'offdevice/user_posts.html', {
        'profile_user': user,
        'profile': profile,
        'usermii': get_mii(user, 0),
        'posts_ctx': posts_ctx,
        'num_posts': num_posts,
        'num_empathies': num_empathies,
        'pagetitle': f"{user.screen_name}'s Posts",
        'me': me,
        'me_mii': get_mii(me, 0) if me else None,
        'page': 'posts',
    })


def _build_user_list_ctx(pids, offset):
    """Helper to build list of users with mii for follow/friend lists"""
    users_ctx = []
    for pid in pids:
        try:
            u = Person.objects.get(pid=pid)
            users_ctx.append({'user': u, 'mii': get_mii(u, 0)})
        except Person.DoesNotExist:
            pass
    return users_ctx


def od_user_friends_view(request, user_id):
    me = get_me(request)
    user = get_object_or_404(Person, user_id=user_id)
    offset = int(request.GET.get('offset', 0))

    rels = FriendRelationship.objects.filter(
        Q(source=user.pid) | Q(target=user.pid)
    ).order_by('-relationship_id')[offset:offset + 50]

    friend_pids = [
        r.target if r.source == user.pid else r.source
        for r in rels
    ]
    users_ctx = _build_user_list_ctx(friend_pids, offset)

    return render(request, 'offdevice/user_follow_list.html', {
        'profile_user': user,
        'usermii': get_mii(user, 0),
        'users_ctx': users_ctx,
        'list_type': 'friends',
        'pagetitle': f"{user.screen_name}'s Friends",
        'me': me,
        'me_mii': get_mii(me, 0) if me else None,
        'next_offset': offset + 50 if len(rels) >= 50 else None,
    })


def od_user_following_view(request, user_id):
    me = get_me(request)
    user = get_object_or_404(Person, user_id=user_id)
    offset = int(request.GET.get('offset', 0))

    rels = Relationship.objects.filter(
        source=user.pid, is_me2me=False
    ).order_by('-relationship_id')[offset:offset + 50]

    following_pids = [r.target for r in rels]
    users_ctx = _build_user_list_ctx(following_pids, offset)

    return render(request, 'offdevice/user_follow_list.html', {
        'profile_user': user,
        'usermii': get_mii(user, 0),
        'users_ctx': users_ctx,
        'list_type': 'following',
        'pagetitle': f"{user.screen_name}'s Following",
        'me': me,
        'me_mii': get_mii(me, 0) if me else None,
        'next_offset': offset + 50 if len(rels) >= 50 else None,
    })


def od_user_followers_view(request, user_id):
    me = get_me(request)
    user = get_object_or_404(Person, user_id=user_id)
    offset = int(request.GET.get('offset', 0))

    rels = Relationship.objects.filter(
        target=user.pid, is_me2me=False
    ).order_by('-relationship_id')[offset:offset + 50]

    follower_pids = [r.source for r in rels]
    users_ctx = _build_user_list_ctx(follower_pids, offset)

    return render(request, 'offdevice/user_follow_list.html', {
        'profile_user': user,
        'usermii': get_mii(user, 0),
        'users_ctx': users_ctx,
        'list_type': 'followers',
        'pagetitle': f"{user.screen_name}'s Followers",
        'me': me,
        'me_mii': get_mii(me, 0) if me else None,
        'next_offset': offset + 50 if len(rels) >= 50 else None,
    })


    me = get_me(request)
    if not me:
        return redirect('/web/act/login?location=/web/news/my_news')

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

    return render(request, 'offdevice/news.html', {
        'news_ctx': news_ctx,
        'pagetitle': 'News',
        'me': me,
        'me_mii': get_mii(me, 0),
        'mnselect': 'news',
    })


def od_my_menu_view(request):
    me = get_me(request)
    if not me:
        return HttpResponse('403 Forbidden', content_type='text/plain', status=403)

    return render(request, 'offdevice/my_menu.html', {
        'pagetitle': 'User Menu',
        'me': me,
        'me_mii': get_mii(me, 0),
    })


def od_profile_settings_view(request):
    me = get_me(request)
    if not me:
        return redirect('/web/act/login')

    profile = get_or_create_profile(me)

    if request.method == 'POST':
        comment = request.POST.get('comment', '').strip()[:255]
        allow_request = int(request.POST.get('allow_request', 1))
        profile.comment = comment
        profile.allow_request = allow_request
        profile.save()
        return redirect(f'/web/users/{me.user_id}')

    return render(request, 'offdevice/profile_settings.html', {
        'profile': profile,
        'pagetitle': 'Profile Settings',
        'me': me,
        'me_mii': get_mii(me, 0),
    })


def od_user_search_view(request):
    me = get_me(request)
    query = request.GET.get('query', '').strip()
    offset = int(request.GET.get('offset', 0))

    users = []
    if query:
        users = Person.objects.filter(
            Q(user_id__istartswith=query) | Q(screen_name__istartswith=query)
        ).order_by('-created_at')[offset:offset + 50]

    return render(request, 'offdevice/user_search.html', {
        'users': users,
        'query': query,
        'pagetitle': 'Search Users',
        'me': me,
        'me_mii': get_mii(me, 0) if me else None,
    })


@require_POST
def od_create_post_view(request):
    me = get_me(request)
    if not me:
        return redirect('/web/act/login')

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
        return redirect('/web/')

    if not body and post_type != 'artwork':
        return redirect(request.META.get('HTTP_REFERER', '/web/'))

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
    return redirect(f'/web/titles/{community.olive_title_id}/{community.olive_community_id}')


@require_POST
def od_create_reply_view(request, post_id):
    me = get_me(request)
    if not me:
        return redirect('/web/act/login')

    post = get_object_or_404(Post, id=post_id)
    body = request.POST.get('body', '').strip()
    feeling_id = int(request.POST.get('feeling_id', 0))
    is_spoiler = request.POST.get('is_spoiler') == '1'

    if not body:
        return redirect(f'/web/posts/{post_id}')

    reply_id = generate_post_id()
    Reply.objects.create(
        id=reply_id,
        pid=me.pid,
        reply_to_id=post_id,
        community_id=post.community_id,
        body=body,
        feeling_id=feeling_id,
        is_spoiler=is_spoiler,
        created_from=request.META.get('REMOTE_ADDR'),
    )
    send_news(me.pid, post.pid, 4, post_id)
    return redirect(f'/web/posts/{post_id}')


@require_POST
def od_empathy_view(request, post_id):
    me = get_me(request)
    if not me:
        return redirect('/web/act/login')

    if not miitoo_can(me.pid, post_id, 'posts'):
        return redirect(f'/web/posts/{post_id}')

    existing = Empathy.objects.filter(id=post_id, pid=me.pid)
    if existing.exists():
        existing.delete()
    else:
        Empathy.objects.create(id=post_id, pid=me.pid)
        try:
            post = Post.objects.get(id=post_id)
            send_news(me.pid, post.pid, 2, post_id)
        except Post.DoesNotExist:
            pass

    return redirect(f'/web/posts/{post_id}')


@require_POST
def od_reply_empathy_view(request, reply_id):
    me = get_me(request)
    if not me:
        return redirect('/web/act/login')

    existing = Empathy.objects.filter(id=reply_id, pid=me.pid)
    if existing.exists():
        existing.delete()
    else:
        Empathy.objects.create(id=reply_id, pid=me.pid)
        try:
            reply = Reply.objects.get(id=reply_id)
            send_news(me.pid, reply.pid, 3, reply_id)
        except Reply.DoesNotExist:
            pass

    # Redirect back to post
    try:
        reply = Reply.objects.get(id=reply_id)
        return redirect(f'/web/posts/{reply.reply_to_id}')
    except Reply.DoesNotExist:
        return redirect('/web/')


@require_POST
def od_follow_view(request, user_id):
    me = get_me(request)
    if not me:
        return redirect('/web/act/login')

    target = get_object_or_404(Person, user_id=user_id)
    if target.pid != me.pid:
        Relationship.objects.get_or_create(source=me.pid, target=target.pid)
        send_news(me.pid, target.pid, 6, None)

    return redirect(f'/web/users/{user_id}')


@require_POST
def od_unfollow_view(request, user_id):
    me = get_me(request)
    if not me:
        return redirect('/web/act/login')

    target = get_object_or_404(Person, user_id=user_id)
    Relationship.objects.filter(source=me.pid, target=target.pid).delete()
    return redirect(f'/web/users/{user_id}')


def od_account_settings_view(request):
    me = get_me(request)
    if not me:
        return redirect('/web/act/login')

    profile = get_or_create_profile(me)
    if request.method == 'POST':
        empathy_optout = request.POST.get('empathy_optout') == '1'
        profile.empathy_optout = empathy_optout
        profile.save()
        return redirect('/web/my_menu')

    return render(request, 'offdevice/account_settings.html', {
        'profile': profile,
        'pagetitle': 'Account Settings',
        'me': me,
        'me_mii': get_mii(me, 0),
    })


def od_rules_view(request):
    me = get_me(request)
    return render(request, 'offdevice/rules.html', {
        'pagetitle': 'Rules & Guidelines',
        'me': me,
        'me_mii': get_mii(me, 0) if me else None,
    })


from django.http import HttpResponse
