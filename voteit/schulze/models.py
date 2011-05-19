import colander
import deform
from pyvotecore.schulze_stv import SchulzeSTV

from voteit.core.models.poll_plugin import PollPlugin
from voteit.core.models.vote import Vote
from pyramid.renderers import render


class SchulzePollPlugin(PollPlugin):
    """ Poll plugin for the Schulze STV Vote """

    name = u'schulze_stv'
    title = u'Schulze STV'
    
    def get_settings_schema(self, poll):
        """ Get an instance of the schema used to render a form for editing settings.
        """
        return SettingsSchema()
    
    def get_vote_schema(self, poll):
        """ Get an instance of the schema that this poll uses.
        """
        proposals = poll.get_proposal_objects()

        #Schulze works with ranking, so we add as many numbers as there are alternatives
        num_proposals = len(proposals)
        #SelectWidget expects a list where each item has a readable title and a value (title, value)
        schulze_choice = [(str(x), str(x)) for x in range(1, num_proposals+1)]
        
        schema = colander.Schema()
        for proposal in proposals:
            schema.add(colander.SchemaNode(colander.String(),
                                           name=proposal.uid,
                                           title=proposal.title,
                                           widget=deform.widget.SelectWidget(values=schulze_choice)),)
        return schema

    def get_vote_class(self):
        return Vote

    def get_result(self, ballots, **settings):
        if ballots:
            self._transform_preference(ballots)
            winners = settings.get('winners', 1)
            return SchulzeSTV(ballots, ballot_notation = "ranking", required_winners=winners).as_dict()

    def _transform_preference(self, ballots):
        for entries in ballots:
            for k, v in entries['ballot'].items():
                entries['ballot'][k] = int(v)

    @staticmethod
    def _get_proposal_by_uid(proposals, uid):
        """ Return a proposal by it's uid"""
        for prop in proposals:
            if prop.uid == uid:
                return prop
        raise KeyError("No proposal found with UID '%s'" % uid)
        
    def render_result(self, poll):
        response = {}
        response['result'] = poll.get_poll_result()
        response['get_proposal_by_uid'] = poll.get_proposal_by_uid
        return render('templates/result.pt', response)

        
class SettingsSchema(colander.Schema):
    """ Settings for a Schulze poll
    """
    winners = colander.SchemaNode(colander.Int())
