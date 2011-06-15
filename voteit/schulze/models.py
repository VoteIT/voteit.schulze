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

    def __init__(self, context):
        self.context = context
        settings = {'winners':1}
        context.poll_settings = settings

    def get_settings_schema(self):
        """ Get an instance of the schema used to render a form for editing settings.
        """
        return SettingsSchema()
    
    def get_vote_schema(self):
        """ Get an instance of the schema that this poll uses.
        """
        proposals = self.context.get_proposal_objects()

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

    def handle_close(self):
        ballots = self.context.ballots
        winners = self.context.poll_settings.get('winners', 1)
        
        schulze_ballots = self.schulze_format_ballots(ballots)
        
        self.context.poll_result = SchulzeSTV(schulze_ballots, ballot_notation = "ranking", required_winners=winners).as_dict()

    def schulze_format_ballots(self, ballots):
        formatted = []
        for (ballot, count) in ballots:
            formatted.append({'count':count, 'ballot':ballot})
        return formatted

    def render_result(self):
        response = {}
        response['result'] = self.context.poll_result
        response['no_users'] = len(self.context.get_voted_userids())
        response['no_winners'] = self.context.poll_settings.get('winners', 1)
        response['get_proposal_by_uid'] = self.context.get_proposal_by_uid
        return render('templates/result.pt', response)

    def change_states_of(self):
        """ This gets called when a poll has finished.
            It returns a dictionary with proposal uid as key and new state as value.
            Like: {'<uid>':'approved', '<uid>', 'denied'}
        """
        #Not implemented yet
        return {}

        
class SettingsSchema(colander.Schema):
    """ Settings for a Schulze poll
    """
    winners = colander.SchemaNode(colander.Int(),
                                  default=1)
