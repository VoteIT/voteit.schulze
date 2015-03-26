from arche.interfaces import IViewInitializedEvent
from arche.interfaces import IBaseView
from fanstatic import Library
from fanstatic import Resource
from fanstatic import Group
from js.jquery import jquery


library = Library('voteit_schulze', 'static')

_star_rating_css = Resource(library, 'rating.css')
_star_rating_js = Resource(library, 'jquery.rating.js', depends = (jquery,))

star_rating = Group((_star_rating_css, _star_rating_js))

#The old jquery rating cruft is in deed need of an overhaul.

def need_star_rating(view, event):
    """ Always load star rating within meetings
        since poll forms can be opened anywhere now.
    """
    if view.request.meeting:
        star_rating.need()

def includeme(config):
    config.add_subscriber(need_star_rating, [IBaseView, IViewInitializedEvent])
     