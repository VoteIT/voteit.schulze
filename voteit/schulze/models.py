from pyramid.traversal import find_interface

import colander
import deform

from voteit.core.models.poll_plugin import PollPlugin
from voteit.core.models.agenda_item import AgendaItem


class SchulzePollPlugin(PollPlugin):
    """ Poll plugin for the Schulze STV Vote """

    name = u'schulze_stv'
    title = u'Schulze STV'

    @staticmethod
    def get_poll_schema(context):
        """ Get an instance of the schema that this poll uses.
        """
        #FIXME: Should this generate an exeption if a poll has been deleted?
        #IE it's uid isn't found
        proposal_uids = context.proposals
        agenda_item = find_interface(context, AgendaItem)
        proposals = set()
        for item in agenda_item.values():
            if item.uid in proposal_uids:
                proposals.add(item)

        #Schulze works with ranking, so we add as many numbers as there are alternatives
        num_proposals = len(proposals)
        #SelectWidget expects a list where each item has a readable title and a value (title, value)
        schulze_choice = [(str(x),str(x)) for x in range(1, num_proposals+1)]
        
        schema = colander.Schema()
        for proposal in proposals:
            schema.add(colander.SchemaNode(colander.String(),
                                           name=proposal.uid,
                                           title=proposal.title,
                                           widget=deform.widget.SelectWidget(values=schulze_choice)),)
        return schema
    
    @staticmethod
    def get_settings_schema(context):
        """ Get an instance of the schema used to render a form for editing settings.
        """
        return SettingsSchema()


class SettingsSchema(colander.Schema):
    """ Settings for a Schulze poll
    """
    winners = colander.SchemaNode(colander.Int())
