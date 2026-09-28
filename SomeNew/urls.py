"""
URL configuration for SomeNew project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('homepage.urls')),
]

# ---------------------------------------------------------------------------
# Media files (user-uploaded content)
# ---------------------------------------------------------------------------
# NOTE:
# * Agar cloud storage (S3 / Supabase Storage / R2) use kar rahe ho, to Django
#   khud bucket ka URL deta hai -> yahan kuch add karne ki zarurat nahi.
# * Warna repo/disk me padi media files yahan se serve hongi.
#   Django ka `static()` helper DEBUG=False pe kuch nahi karta, isliye
#   `django.views.static.serve` ko directly use kiya gaya hai.
# * Yaad rakho: Vercel ka filesystem read-only hai, isliye naye uploads tab tak
#   save nahi honge jab tak cloud storage (AWS_STORAGE_BUCKET_NAME env var)
#   configure na ho jaye.
if not getattr(settings, "USING_CLOUD_MEDIA", False):
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
