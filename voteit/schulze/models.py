from copy import deepcopy

import colander
from pyvotecore.schulze_stv import SchulzeSTV
from pyvotecore.schulze_pr import SchulzePR
from pyramid.renderers import render
from pyramid.response import Response
from pyramid.url import resource_url
from repoze.catalog.query import Any
from voteit.core.models.poll_plugin import PollPlugin
from voteit.core.widgets import StarWidget

from voteit.schulze import VoteITSchulzeMF as _
from voteit.core.models.proposal import Proposal


class SchulzeBase(object):
    """ Common methods for Schulze ballots. This is ment to be a mixin
        for an adapter. It won't work by itself.
    """
    
    def get_vote_schema(self, request, api):
        """ Get an instance of the schema that this poll uses.
        """
        
        query = api.root.catalog.query
        get_metadata = api.root.catalog.document_map.get_metadata
        num, results = query(Any('uid', self.context.proposal_uids), sort_index = 'created')
        proposals = [get_metadata(x) for x in results]
        
        #Schulze works with ranking, so we add as many numbers as there are alternatives
        stars = len(proposals)
        max_stars = self.context.poll_settings.get('max_stars', 5)
        min_stars = self.context.poll_settings.get('min_stars', 5)
        if max_stars < stars:
            stars = max_stars
        if min_stars > stars:
            stars = min_stars
        #SelectWidget expects a list where each item has a value and a readable title  (value, title)
        #the title should be the value reversed 
        schulze_choice = [(str(x), str(stars-x+1)) for x in range(1, stars+1)]
        #Ie 5 stars = 1 point, 1 star 5 points
        schulze_choice.reverse()
        
        valid_entries = [str(x) for x in range(1, stars+2)] #To include the missing value
        
        schema = colander.Schema()
        for proposal in proposals:
            schema.add(colander.SchemaNode(colander.String(),
                                           name=proposal['uid'],
                                           #To make missing even less desired than the regular stars
                                           #Schulze can't handle null value or empty dicts.
                                           #This does however produce the same result
                                           missing=stars+1,
                                           title=proposal['title'],
                                           validator=colander.OneOf(valid_entries),
                                           widget=StarWidget(values = schulze_choice,
                                                             proposal = proposal,
                                                             api = api,)))
        return schema


    def schulze_format_ballots(self, ballots):
        formatted = []
        for (ballot, count) in ballots:
            formatted.append({'count':count, 'ballot':ballot})
        return formatted

    def render_raw_data(self):
        return Response(unicode(self.context.ballots))


class SchulzeSTVPollPlugin(SchulzeBase, PollPlugin):
    """ Poll plugin for the Schulze STV Polls. """
    name = u'schulze_stv'
    title = _(u"schulze_stv_title", 
              default="Schulze STV")
    description = _(u"description_schulze_stv", 
                    default = "Order the proposals with stars. "
                              "The more stars the more you prefer the proposal. "
                              "VoteIT calculates the relation between the "
                              "proposals and finds a winner. "
                              "In case of a tie there is a random tie breaker.")

    def get_settings_schema(self):
        """ Get an instance of the schema used to render a form for editing settings.
        """
        schema = SettingsSchema()
        schema.title = _(u"Poll settings")
        schema.description = _(u"Settings for Schulze STV") 
        return schema

    def handle_close(self):
        #IMPORTANT! Use deepcopy, we don't want the SchulzeSTV to modify our ballots, just calculate a result
        ballots = deepcopy(self.context.ballots)
        if not ballots:
            self.context.poll_result = {'candidates': set(self.context.proposal_uids)}
            raise ValueError("It's not possible to use this version of Schulze STV without any votes. At least one is needed.")
        winners = self.context.poll_settings.get('winners', 1)
        schulze_ballots = self.schulze_format_ballots(ballots)
        self.context.poll_result = SchulzeSTV(schulze_ballots, ballot_notation = "ranking", required_winners=winners).as_dict()

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

    def render_result(self, request, api, complete=True):
        
        response = {}
        response['api'] = api
        response['result'] = self.context.poll_result
        response['no_users'] = len(self.context.get_voted_userids())
        response['no_winners'] = self.context.poll_settings.get('winners', 1)
        response['get_proposal_by_uid'] = self.context.get_proposal_by_uid
        response['raw_data_link'] = "%spoll_raw_data" % resource_url(self.context, request)
        response['complete'] = complete
        return render('templates/result_stv.pt', response, request=request)


class SchulzePRPollPlugin(SchulzeBase, PollPlugin):
    """ Poll plugin for the Schulze PR ranking polls. It will sort a list
        of proposals according to the voters preference.
    """
    name = u'schulze_pr'
    title = _(u"schulze_pr_title", 
              default="Schulze PR (ranking only)")
    description = _(u"description_schulze_pr",
                    default = "Order the proposals with stars. "
                              "The more stars the more you prefer the proposal. "
                              "VoteIT calculates the relation between the "
                              "proposals and sorts them according to all voters preference. "
                              "In case of a tie there's a random tie breaker.")

    def get_settings_schema(self):
        """ Get an instance of the schema used to render a form for editing settings.
        """
        schema = SettingsSchema()
        schema.title = _(u"Poll settings")
        schema.description = _(u"Settings for Schulze PR")
        del schema['winners']
        return schema

    def handle_close(self):
        #IMPORTANT! Use deepcopy, we don't want the SchulzePR to modify our ballots, just calculate a result
        ballots = deepcopy(self.context.ballots)
        if not ballots:
            self.context.poll_result = {'candidates': set(self.context.proposal_uids)}
            raise ValueError("It's not possible to use this version of Schulze PR without any votes. At least one is needed.")
        schulze_ballots = self.schulze_format_ballots(ballots)
        self.context.poll_result = SchulzePR(schulze_ballots, ballot_notation = "ranking").as_dict()

    def render_result(self, request, api, complete=True):
        response = {}
        response['api'] = api
        response['result'] = self.context.poll_result
        response['no_users'] = len(self.context.get_voted_userids())
        response['get_proposal_by_uid'] = self.context.get_proposal_by_uid
        response['raw_data_link'] = "%spoll_raw_data" % resource_url(self.context, request)
        response['complete'] = complete
        return render('templates/result_pr.pt', response, request=request)


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