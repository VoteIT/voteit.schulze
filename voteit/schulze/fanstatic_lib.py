from arche.interfaces import IViewInitializedEvent
from fanstatic import Library
from fanstatic import Resource
from fanstatic import Group
from js.jquery import jquery
from voteit.core.views.agenda_item import AgendaItemView


library = Library('voteit_schulze', 'static')

_star_rating_css = Resource(library, 'rating.css')
_star_rating_js = Resource(library, 'jquery.rating.js', depends = (jquery,))

star_rating = Group((_star_rating_css, _star_rating_js))

#The old jquery rating cruft is in deed need of an overhaul.

def need_star_rating(*args):
    star_rating.need()

def includeme(config):
    """ Create a subscriber that fires on agenda items. This isn't a perfect way
        of including this script, but there's no other good way right now.
        FIXME: Change this :)
    """
    config.add_subscriber(need_star_rating, [AgendaItemView, IViewInitializedEvent])
     