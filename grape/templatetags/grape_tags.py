from django import template
from grape.helpers import human_timing, get_mii, truncate_text, get_post_id_encoded
from grape.models import Empathy, Reply

register = template.Library()


@register.filter
def humantiming(value):
    return human_timing(value)


@register.filter
def truncate_body(value, chars=200):
    return truncate_text(value, chars)


@register.simple_tag
def mii_face(user, feeling_id=0):
    return get_mii(user, feeling_id)['output']


@register.simple_tag
def empathy_count(post_id):
    return Empathy.objects.filter(id=post_id).count()


@register.simple_tag
def reply_count(post_id):
    return Reply.objects.filter(reply_to_id=post_id).count()


@register.filter
def post_id_encoded(value):
    return get_post_id_encoded(value)


@register.simple_tag(takes_context=True)
def user_has_yeah(context, post_id):
    request = context.get('request')
    if not request:
        return False
    pid = request.session.get('pid')
    if not pid:
        return False
    return Empathy.objects.filter(id=post_id, pid=pid).exists()
