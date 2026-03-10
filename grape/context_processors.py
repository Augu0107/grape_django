from grape.helpers import get_mii, hash_pid, get_updates
from grape.models import Person


def grape_context(request):
    """Add global context variables to all templates"""
    ctx = {
        'is_wiiu': getattr(request, 'is_wiiu', False),
        'is_offdevice': getattr(request, 'is_offdevice', False),
        'is_portal': getattr(request, 'is_portal', True),
        'grp_theme': request.COOKIES.get('grp_theme', 'default'),
    }

    pid = request.session.get('pid')
    user_id = request.session.get('user_id')

    if pid:
        try:
            me = Person.objects.get(pid=pid)
            ctx['me'] = me
            ctx['me_mii'] = get_mii(me, 0)
            ctx['me_pid_hash'] = hash_pid(pid)
            ctx['updates'] = get_updates(pid)
        except Person.DoesNotExist:
            request.session.flush()

    return ctx
