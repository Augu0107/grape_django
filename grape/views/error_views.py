from django.shortcuts import render


def handler404(request, exception=None):
    is_offdevice = request.path.startswith('/web/')
    if is_offdevice:
        tpl = 'offdevice/404.html'
    else:
        tpl = 'portal/404.html'
    return render(request, tpl, status=404)


def handler500(request):
    is_offdevice = request.path.startswith('/web/')
    if is_offdevice:
        tpl = 'offdevice/404.html'
    else:
        tpl = 'portal/404.html'
    return render(request, tpl, {'error': 'Internal server error.'}, status=500)
