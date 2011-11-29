""" Fanstatic lib"""
from fanstatic import Group
from fanstatic import Library
from fanstatic import Resource

from voteit.core.fanstaticlib import voteit_common_js
from voteit.core.fanstaticlib import voteit_main_css


voteit_schulze_lib = Library('voteit_schulze', '')

voteit_schulze_js = Resource(voteit_schulze_lib, 'voteit_schulze.js', depends=(voteit_common_js,))
voteit_schulze_css = Resource(voteit_schulze_lib, 'voteit_schulze.css', depends=(voteit_main_css,))

voteit_schulze = Group((voteit_schulze_js, voteit_schulze_css))
