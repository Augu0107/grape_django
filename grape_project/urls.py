from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os

# Serve /css/, /img/, /js/ directly (matching original PHP grape paths used in CSS/HTML)
_static_root = settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^css/(?P<path>.*)$', serve, {'document_root': os.path.join(_static_root, 'css')}),
    re_path(r'^img/(?P<path>.*)$', serve, {'document_root': os.path.join(_static_root, 'img')}),
    re_path(r'^js/(?P<path>.*)$', serve, {'document_root': os.path.join(_static_root, 'js')}),
    path('web/', include('grape.urls_offdevice')),
    path('', include('grape.urls_portal')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'grape.views.error_views.handler404'
handler500 = 'grape.views.error_views.handler500'
