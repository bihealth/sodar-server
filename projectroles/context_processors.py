from django.conf import settings


def settings_processor(request):
    """Context processor for providing settings values to templates"""
    context_settings = {}

    # Local demo includes
    # TODO: Deprecate this?
    if hasattr(settings, 'LOCAL_TEMPLATE_INCLUDES'):
        context_settings['LOCAL_TEMPLATE_INCLUDES'] = \
            settings.LOCAL_TEMPLATE_INCLUDES

    # Selenium timeout workaround
    if hasattr(settings, 'DISABLE_JAVASCRIPT_INCLUDES'):
        context_settings['DISABLE_JAVASCRIPT_INCLUDES'] =\
            settings.DISABLE_JAVASCRIPT_INCLUDES

    return context_settings
