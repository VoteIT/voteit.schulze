import colander
import deform

from voteit.schulze import _


class SettingsSchema(colander.Schema):
    """ Settings for a Schulze poll
    """
    winners = colander.SchemaNode(
        colander.Int(),
        title=_(u"Winners (For 1, use regular Schulze)"),
        description=_(u"schulze_config_winners_description",
                      default="Note! With more than 5 winners, "
                              "the result may take an extremely long time to calculate. "
                              "Consult VoteIT development team before using this!"),
        default=2,
    )
    max_stars = colander.SchemaNode(
        colander.Int(),
        title=_(u"Maximum stars"),
        description=_(u"schulze_config_max_stars_description",
                      default=u"The maximum numbers of stars regarless of number of proposals"),
        default=5,
    )
    min_stars = colander.SchemaNode(
        colander.Int(),
        title=_(u"Minumum stars"),
        description=_(u"schulze_config_min_stars_description",
                      default=u"The minimum numbers of stars regarless of number of proposals"),
        default=5,
    )


# The schema will be populated in the schulze poll plugin
class SchulzePollSchema(colander.Schema):
    widget = deform.widget.FormWidget(template='form_modal',
                                      readonly_template='readonly/form_modal')
