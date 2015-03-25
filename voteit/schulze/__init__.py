from pyramid.i18n import TranslationStringFactory


_ = TranslationStringFactory('voteit.schulze')


def includeme(config):
    config.add_translation_dirs('voteit.schulze:locale/')
    config.include('.models')
