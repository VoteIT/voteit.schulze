from voteit.core import register_poll_plugin

from voteit.schulze.models import SchulzePollPlugin


def includeme(config):
    register_poll_plugin(SchulzePollPlugin)
    