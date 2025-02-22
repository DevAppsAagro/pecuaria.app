from django.conf import settings
from decouple import config

def debug(request):
    return {'DEBUG': settings.DEBUG}

def supabase_config(request):
    return {
        'SUPABASE_URL': config('SUPABASE_URL'),
        'SUPABASE_KEY': config('SUPABASE_KEY')
    }
