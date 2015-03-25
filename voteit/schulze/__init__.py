from pyramid.i18n import TranslationStringFactory
from pyramid_deform import configure_zpt_renderer


_ = TranslationStringFactory('voteit.schulze')


def includeme(config):
    config.add_translation_dirs('voteit.schulze:locale/')
    config.include('.models')
    config.include('.fanstatic_lib')
    #Include widget search path (for deform)
    configure_zpt_renderer(['voteit.schulze:templates/widgets'])
