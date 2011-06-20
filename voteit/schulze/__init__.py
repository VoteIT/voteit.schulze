

def includeme(config):
    from voteit.core.app import register_poll_plugin
    from voteit.schulze.models import SchulzePollPlugin
    register_poll_plugin(SchulzePollPlugin, registry=config.registry)
    