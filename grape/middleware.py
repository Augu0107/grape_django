"""
Middleware to detect if the request is from WiiU/portal or offdevice/web
"""


class InterfaceDetectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ua = request.META.get('HTTP_USER_AGENT', '').lower()
        # WiiU Miiverse browser contains 'miiverse' in UA
        request.is_wiiu = 'miiverse' in ua
        # Detect offdevice: requests to /web/ prefix are always offdevice
        request.is_offdevice = request.path.startswith('/web/')
        # For portal routes, use UA detection
        if not request.is_offdevice:
            request.is_portal = True
        else:
            request.is_portal = False

        response = self.get_response(request)
        return response
