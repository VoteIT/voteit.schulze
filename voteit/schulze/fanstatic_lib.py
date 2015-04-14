from arche.interfaces import IViewInitializedEvent
from arche.interfaces import IBaseView
from fanstatic import Library
from fanstatic import Resource


library = Library('voteit_schulze', 'static')
star_rating = Resource(library, 'rating.css')


def need_star_rating(view, event):
    """ Always load star rating within meetings
        since poll forms can be opened anywhere now.
    """
    if view.request.meeting:
        star_rating.need()

def includeme(config):
    config.add_subscriber(need_star_rating, [IBaseView, IViewInitializedEvent])
     