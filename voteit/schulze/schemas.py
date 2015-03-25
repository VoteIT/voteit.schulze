import colander

from voteit.schulze import _


class SettingsSchema(colander.Schema):
    """ Settings for a Schulze poll
    """
    winners = colander.SchemaNode(colander.Int(),
                                  title = _(u"Winners"),
                                  description = _(u"schulze_config_winners_description",
                                                  default=u"Numbers of possible winners in the poll"),
                                  default=1,)
    max_stars = colander.SchemaNode(colander.Int(),
                                    title = _(u"Maximum stars"),
                                    description = _(u"schulze_config_max_stars_description",
                                                    default=u"The maximum numbers of stars regarless of number of proposals"),
                                    default=5,)
    min_stars = colander.SchemaNode(colander.Int(),
                                    title = _(u"Minumum stars"),
                                    description = _(u"schulze_config_min_stars_description",
                                                    default=u"The minimum numbers of stars regarless of number of proposals"),
                                    default=5,)
