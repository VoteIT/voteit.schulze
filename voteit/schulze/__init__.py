from pyramid.i18n import TranslationStringFactory


VoteITSchulzeMF = TranslationStringFactory('voteit.schulze')


def includeme(config):
    from voteit.core.models.interfaces import IPoll
    from voteit.core.models.interfaces import IPollPlugin

    from voteit.schulze.models import SchulzePollPlugin
    
    config.registry.registerAdapter(SchulzePollPlugin, (IPoll,), IPollPlugin, SchulzePollPlugin.name)
    config.add_translation_dirs('voteit.schulze:locale/')
