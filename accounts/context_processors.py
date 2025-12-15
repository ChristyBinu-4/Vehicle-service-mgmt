"""
Context processors for making system-wide data available to all templates.
"""
from .models import SystemSettings


def system_settings(request):
    """
    Context processor to make SystemSettings available to all templates.
    Provides background images for User and Servicer interfaces.
    
    Returns:
        dict: Contains 'system_settings' with SystemSettings instance
    """
    try:
        settings = SystemSettings.get_settings()
    except Exception:
        # Fallback: create a default instance if something goes wrong
        settings = SystemSettings.objects.first()
        if not settings:
            settings = SystemSettings.objects.create(pk=1)
    
    return {
        'system_settings': settings,
    }
