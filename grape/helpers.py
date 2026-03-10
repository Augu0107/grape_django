"""
Grape helpers - equivalent to PHP grplib-php helpers
"""
import hashlib
import time
import uuid
from django.utils import timezone
from django.db import models as djmodels


def generate_pid():
    """Generate a unique PID (equivalent to PIDgen in PHP)"""
    from grape.models import Person
    try:
        first = Person.objects.order_by('pid').first()
        if first:
            return 1799999999 - (1799999999 - first.pid) - 1
        return 1799999999
    except Exception:
        return 1799999999


def generate_post_id():
    """Generate a unique post/reply ID"""
    return uuid.uuid4().hex[:32]


def human_timing(dt):
    """Convert datetime to human-readable relative time"""
    if dt is None:
        return ''
    now = timezone.now()
    if hasattr(dt, 'timestamp'):
        diff = now - dt
    else:
        return str(dt)

    total_seconds = int(diff.total_seconds())

    if total_seconds < 0:
        return 'just now'

    if diff.days >= 4:
        return dt.strftime('%m/%d/%Y')

    if total_seconds < 60:
        return 'within a minute'
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        return f'{hours} hour{"s" if hours != 1 else ""} ago'
    else:
        days = diff.days
        return f'{days} day{"s" if days != 1 else ""} ago'


def get_mii(user, feeling_id=0):
    """Get Mii face URL and feeling metadata"""
    feeling_map = {0: 'normal', 1: 'happy', 2: 'like', 3: 'surprised', 4: 'frustrated', 5: 'puzzled'}
    feeling = feeling_map.get(feeling_id or 0, 'normal')

    miitoo_labels = {
        'normal': 'Yeah!',
        'happy': 'Happy Yeah!',
        'like': 'Like Yeah!',
        'surprised': 'Wow Yeah!',
        'frustrated': 'Ugh Yeah!',
        'puzzled': 'Hmm Yeah!',
    }

    miitoo_delete_labels = {
        'normal': 'Yeah!',
        'happy': 'Happy Yeah!',
        'like': 'Like Yeah!',
        'surprised': 'Wow Yeah!',
        'frustrated': 'Ugh Yeah!',
        'puzzled': 'Hmm Yeah!',
    }

    if user and user.mii_hash:
        face = f'https://mii-secure.cdn.nintendo.net/{user.mii_hash}_{feeling}_face.png'
    elif user and user.face:
        face = user.face
    else:
        face = '/static/img/mii/img_unknown_MiiIcon.png'

    return {
        'output': face,
        'feeling': feeling,
        'miitoo': miitoo_labels.get(feeling, 'Yeah!'),
        'miitoo_delete': miitoo_delete_labels.get(feeling, 'Yeah!'),
        'official': bool(user and user.official_user),
    }


def can_user_view(session_pid, target_pid):
    """Check if session user has blocked or is blocked by target"""
    if not session_pid or not target_pid:
        return False
    from grape.models import Blacklist
    return Blacklist.objects.filter(
        djmodels.Q(source=session_pid, target=target_pid) |
        djmodels.Q(source=target_pid, target=session_pid)
    ).exists()


def miitoo_can(pid, post_id, post_type='posts'):
    """Check if user can give a Yeah to a post/reply"""
    from grape.models import Post, Reply, Restriction
    if post_type == 'replies':
        try:
            obj = Reply.objects.get(id=post_id)
        except Reply.DoesNotExist:
            return False
    else:
        try:
            obj = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return False

    if obj.pid == pid:
        return False

    from grape.models import Person
    try:
        user = Person.objects.get(pid=pid)
        if user.status >= 3:
            return False
    except Person.DoesNotExist:
        return False

    # Check restrictions
    restricted = Restriction.objects.filter(
        id=post_id,
        operation=0
    ).filter(
        djmodels.Q(recipients__icontains=str(pid)) | djmodels.Q(recipients__isnull=True)
    ).exists()

    return not restricted


def get_or_create_profile(user):
    """Get or create a profile for a user"""
    from grape.models import Profile
    profile, created = Profile.objects.get_or_create(
        pid=user.pid,
        defaults={'platform_id': user.platform_id}
    )
    return profile


def send_news(from_pid, to_pid, news_type, subject_id):
    """Send a news notification"""
    if from_pid == to_pid:
        return
    from grape.models import News, Profile
    import django.utils.timezone as tz
    from datetime import timedelta

    # Empathy optout check
    if news_type in (2, 3):
        if Profile.objects.filter(pid=to_pid, empathy_optout=True).exists():
            return

    # Rate limit: don't send same notification within 8 seconds
    eight_secs_ago = tz.now() - timedelta(seconds=8)
    if News.objects.filter(
        from_pid=from_pid, to_pid=to_pid,
        news_context=news_type, created_at__gt=eight_secs_ago
    ).exists():
        return

    two_hours_ago = tz.now() - timedelta(hours=2)

    # Check if we can merge with existing
    existing_kwargs = {
        'from_pid': from_pid, 'to_pid': to_pid,
        'news_context': news_type, 'merged__isnull': True,
        'created_at__gt': two_hours_ago
    }
    if news_type != 6:
        existing_kwargs['id'] = subject_id

    existing = News.objects.filter(**existing_kwargs).first()

    if existing:
        # Create merged notification
        News.objects.create(
            from_pid=from_pid, to_pid=to_pid,
            id=subject_id, news_context=news_type,
            merged=existing.news_id
        )
        existing.has_read = False
        existing.created_at = tz.now()
        existing.save()
    else:
        News.objects.create(
            from_pid=from_pid, to_pid=to_pid,
            id=subject_id, news_context=news_type
        )


def profile_relationship_visible(viewer_pid, target_pid, visibility):
    """Check if profile relationships are visible"""
    if viewer_pid == target_pid:
        return True
    if visibility == 0:
        return True  # public
    if visibility == 1:
        from grape.models import FriendRelationship
        return FriendRelationship.objects.filter(
            djmodels.Q(source=viewer_pid, target=target_pid) |
            djmodels.Q(source=target_pid, target=viewer_pid)
        ).exists()
    return False


def truncate_text(text, chars):
    if not text:
        return ''
    if len(text) >= chars + 1:
        return text[:chars] + '...'
    return text


def get_post_id_encoded(post_id):
    """Encode post ID for display (simple version)"""
    return post_id[:8].upper() if post_id else ''


def hash_pid(pid):
    return hashlib.sha1(str(pid).encode()).hexdigest()


def get_updates(pid):
    """Get unread notification counts"""
    from grape.models import News, FriendRequest, Message, Conversation
    from django.db import models as M

    news_count = News.objects.filter(to_pid=pid, has_read=False, merged__isnull=True).count()
    friend_req_count = FriendRequest.objects.filter(recipient=pid, has_read=False, finished=False).count()

    # Messages unread count (approximate)
    msg_count = Message.objects.filter(
        conversation_id__in=Conversation.objects.filter(
            M.Q(sender=pid) | M.Q(recipient=pid)
        ).values('conversation_id')
    ).exclude(pid=pid).filter(has_read=False).count()

    return {
        'news': news_count,
        'friend_requests': friend_req_count,
        'messages': msg_count,
    }
