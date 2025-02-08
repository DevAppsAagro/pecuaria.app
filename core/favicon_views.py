import os
from django.conf import settings
from django.http import HttpResponse, FileResponse

def serve_favicon(request):
    """View pública para servir o favicon.ico da pasta public"""
    favicon_path = os.path.join(settings.BASE_DIR, 'public', 'favicon.ico')
    if os.path.exists(favicon_path):
        return FileResponse(open(favicon_path, 'rb'), content_type='image/x-icon')
    return HttpResponse(status=404)
