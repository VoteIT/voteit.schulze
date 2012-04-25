from pyramid.i18n import TranslationStringFactory


VoteITSchulzeMF = TranslationStringFactory('voteit.schulze')


def includeme(config):
    from voteit.core.models.interfaces import IPoll
    from voteit.core.models.interfaces import IPollPlugin
    config.add_translation_dirs('voteit.schulze:locale/')

    from voteit.schulze.models import SchulzeSTVPollPlugin
    config.registry.registerAdapter(SchulzeSTVPollPlugin, (IPoll,), IPollPlugin, SchulzeSTVPollPlugin.name)
    from voteit.schulze.models import SchulzePRPollPlugin
    config.registry.registerAdapter(SchulzePRPollPlugin, (IPoll,), IPollPlugin, SchulzePRPollPlugin.name)
