from copy import deepcopy

import colander
import deform
from pyvotecore.schulze_stv import SchulzeSTV
from pyramid.renderers import render
from pyramid.response import Response
from voteit.core.models.poll_plugin import PollPlugin
from voteit.core.models.vote import Vote
from voteit.core.widget import StarWidget


class SchulzePollPlugin(PollPlugin):
    """ Poll plugin for the Schulze STV Vote """

    name = u'schulze_stv'
    title = u'Schulze STV'

    def __init__(self, context):
        """ Remember that init is run every time the adapter adapts something,
            so don't put configuration defaults or similar here.
        """
        self.context = context

    def get_settings_schema(self):
        """ Get an instance of the schema used to render a form for editing settings.
        """
        return SettingsSchema()
    
    def get_vote_schema(self):
        """ Get an instance of the schema that this poll uses.
        """
        proposals = self.context.get_proposal_objects()

        #Schulze works with ranking, so we add as many numbers as there are alternatives
        stars = len(proposals)
        max_stars = self.context.poll_settings.get('max_stars', 5)
        if max_stars < stars:
            stars = max_stars
        #SelectWidget expects a list where each item has a readable title and a value (title, value)
        schulze_choice = [(str(x), str(x)) for x in range(1, stars+1)]
        #Ie 5 stars = 1 point, 1 star 5 points
        schulze_choice.reverse()
        
        valid_entries = [str(x) for x in range(1, stars+2)] #To include the missing value
        
        schema = colander.Schema()
        for proposal in proposals:
            schema.add(colander.SchemaNode(colander.String(),
                                           name=proposal.uid,
                                           #To make missing even less desired than the regular stars
                                           #Schulze can't handle null value or empty dicts.
                                           #This does however produce the same result
                                           missing=stars+1,
                                           title=proposal.title,
                                           validator=colander.OneOf(valid_entries),
                                           widget=StarWidget(values=schulze_choice)),)
        return schema

    def get_vote_class(self):
        return Vote

    def handle_close(self):
        #IMPORTANT! Use deepcopy, we don't want the SchulzeSTV to modify our ballots, just calculate a result
        ballots = deepcopy(self.context.ballots)
        if not ballots:
            self.context.poll_result = {'candidates': set(self.context.proposal_uids)}
            return
            #aise ValueError("It's not possible to use this version of Schulze STV without any votes. At least one is needed.")
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
        result = {}
        
        winners = self.context.poll_result.get('winners', ())
        losers = self.context.poll_result['candidates'] - set(winners)

        if winners:
            for winner in winners:
                result[winner] = 'approved'

            for loser in losers:
                result[loser] = 'denied'
        
        return result

    def render_raw_data(self):
        return Response(unicode(self.context.ballots))
        
class SettingsSchema(colander.Schema):
    """ Settings for a Schulze poll
    """
    winners = colander.SchemaNode(colander.Int(),
                                  default=1,)
    max_stars = colander.SchemaNode(colander.Int(),
                                    default=5,)
