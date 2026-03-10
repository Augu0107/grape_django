from django.db import models
from django.utils import timezone


class Person(models.Model):
    """Users table (people in original)"""
    pid = models.BigIntegerField(primary_key=True)
    user_id = models.CharField(max_length=20, unique=True)
    screen_name = models.CharField(max_length=17)
    password = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, blank=True, null=True)
    mii_hash = models.CharField(max_length=255, blank=True, null=True)
    face = models.TextField(blank=True, null=True)
    mii = models.TextField(blank=True, null=True)
    official_user = models.BooleanField(default=False)
    organization = models.CharField(max_length=255, blank=True, null=True)
    platform_id = models.IntegerField(default=1)  # 1=WiiU, 0=3DS
    privilege = models.IntegerField(default=0)
    image_perm = models.BooleanField(default=False)
    status = models.IntegerField(default=0)
    ban_status = models.IntegerField(default=0)
    nnas_info = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'people'

    def get_mii_url(self, feeling_id=0):
        feeling_map = {0: 'normal', 1: 'happy', 2: 'like', 3: 'surprised', 4: 'frustrated', 5: 'puzzled'}
        feeling = feeling_map.get(feeling_id, 'normal')
        if self.mii_hash:
            return f'https://mii-secure.cdn.nintendo.net/{self.mii_hash}_{feeling}_face.png'
        elif self.face:
            return self.face
        return '/static/img/mii/img_unknown_MiiIcon.png'

    def __str__(self):
        return self.user_id


class Title(models.Model):
    olive_title_id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=255)
    platform_id = models.IntegerField(blank=True, null=True)  # None=special, 0=3DS, 1=WiiU
    icon = models.TextField(blank=True, null=True)
    hidden = models.BooleanField(default=False)
    banner_3ds = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'titles'

    def __str__(self):
        return self.name

    @property
    def first_community(self):
        return Community.objects.filter(
            olive_title_id=self.olive_title_id
        ).exclude(type=5).first()


class Community(models.Model):
    community_id = models.AutoField(primary_key=True)
    olive_community_id = models.CharField(max_length=64, unique=True)
    olive_title_id = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    icon = models.TextField(blank=True, null=True)
    type = models.IntegerField(default=0)  # 0=normal,1=main,2=announcement,5=activity
    platform_type = models.IntegerField(blank=True, null=True)
    platform_id = models.IntegerField(blank=True, null=True)
    min_perm = models.IntegerField(default=0)
    allowed_pids = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'communities'

    def get_icon(self):
        if not self.icon or len(self.icon) <= 1:
            return '/static/img/title-icon-default.png'
        return self.icon

    def __str__(self):
        return self.name


class Post(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    pid = models.BigIntegerField()
    community_id = models.IntegerField()
    body = models.TextField(blank=True, null=True)
    _post_type = models.CharField(max_length=64, default='body')  # 'body','artwork', or reply_to_id
    screenshot = models.TextField(blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    feeling_id = models.IntegerField(default=0)
    is_spoiler = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    hidden_resp = models.CharField(max_length=1, blank=True, null=True)  # '1' = silent hide
    created_at = models.DateTimeField(default=timezone.now)
    created_from = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = 'posts'

    @property
    def post_type(self):
        return self._post_type

    def is_reply(self):
        return self._post_type and len(self._post_type) > 10

    def __str__(self):
        return f'Post {self.id}'


class Reply(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    pid = models.BigIntegerField()
    reply_to_id = models.CharField(max_length=64)
    community_id = models.IntegerField()
    body = models.TextField(blank=True, null=True)
    screenshot = models.TextField(blank=True, null=True)
    feeling_id = models.IntegerField(default=0)
    is_spoiler = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    hidden_resp = models.CharField(max_length=1, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_from = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = 'replies'


class Empathy(models.Model):
    empathy_id = models.AutoField(primary_key=True)
    id = models.CharField(max_length=64)  # post or reply id
    pid = models.BigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    created_from = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = 'empathies'
        unique_together = ('id', 'pid')


class Relationship(models.Model):
    relationship_id = models.AutoField(primary_key=True)
    source = models.BigIntegerField()  # follower
    target = models.BigIntegerField()  # following
    is_me2me = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'relationships'
        unique_together = ('source', 'target')


class FriendRelationship(models.Model):
    relationship_id = models.AutoField(primary_key=True)
    source = models.BigIntegerField()
    target = models.BigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'friend_relationships'


class FriendRequest(models.Model):
    request_id = models.AutoField(primary_key=True)
    sender = models.BigIntegerField()
    recipient = models.BigIntegerField()
    message = models.TextField(blank=True, null=True)
    finished = models.BooleanField(default=False)
    has_read = models.BooleanField(default=False)
    news_id = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'friend_requests'


class Profile(models.Model):
    pid = models.BigIntegerField(primary_key=True)
    comment = models.TextField(blank=True, null=True)
    favorite_screenshot = models.CharField(max_length=64, blank=True, null=True)
    platform_id = models.IntegerField(default=1)
    allow_request = models.IntegerField(default=1)
    relationship_visibility = models.IntegerField(default=0)
    empathy_optout = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'profiles'


class News(models.Model):
    news_id = models.AutoField(primary_key=True)
    from_pid = models.BigIntegerField()
    to_pid = models.BigIntegerField()
    id = models.CharField(max_length=64, blank=True, null=True)  # post/reply id
    news_context = models.IntegerField()
    has_read = models.BooleanField(default=False)
    merged = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'news'


class Blacklist(models.Model):
    id = models.AutoField(primary_key=True)
    source = models.BigIntegerField()
    target = models.BigIntegerField()
    type = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'blacklist'
        unique_together = ('source', 'target')


class Conversation(models.Model):
    conversation_id = models.AutoField(primary_key=True)
    sender = models.BigIntegerField()
    recipient = models.BigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'conversations'


class Message(models.Model):
    id = models.AutoField(primary_key=True)
    conversation_id = models.IntegerField()
    pid = models.BigIntegerField()
    body = models.TextField()
    feeling_id = models.IntegerField(default=0)
    screenshot = models.TextField(blank=True, null=True)
    has_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'messages'


class Restriction(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    type = models.IntegerField()
    operation = models.IntegerField(default=0)
    recipients = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'restrictions'


class SettingsTitle(models.Model):
    pid = models.BigIntegerField()
    olive_title_id = models.CharField(max_length=64)
    value = models.IntegerField(default=0)

    class Meta:
        db_table = 'settings_title'
        unique_together = ('pid', 'olive_title_id')


class Favorite(models.Model):
    pid = models.BigIntegerField()
    community_id = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'favorites'
        unique_together = ('pid', 'community_id')


class EmailConfirmation(models.Model):
    id = models.AutoField(primary_key=True)
    pid = models.BigIntegerField()
    state = models.CharField(max_length=64)
    finished = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'email_confirmation'
