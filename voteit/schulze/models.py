from copy import deepcopy

from pyramid.renderers import render
from pyramid.response import Response
from pyvotecore.schulze_pr import SchulzePR
from pyvotecore.schulze_stv import SchulzeSTV
from voteit.core.models.poll_plugin import PollPlugin
import colander
import deform

from voteit.schulze.schemas import SettingsSchema
from voteit.schulze import _
from voteit.schulze.schemas import SchulzePollSchema


class SchulzeBase(object):
    """ Common methods for Schulze ballots. This is ment to be a mixin
        for an adapter. It won't work by itself.
    """

    def get_vote_schema(self):
        """ Get an instance of the schema that this poll uses.

            Maximum and minimum number of stars is a setting for the widget
            about the number of stars to display. It has nothing to do with validation or similar.

            About the rating and how Schulze STV and PR calculates them:
            Note that higher is less preferred. Missing should be highest
            "normal" value +1 to avoid mixing it with an active stance on something.
            That makes it possible to just rate some of the proposals.
        """
        proposals = self.context.get_proposal_objects()
        #Schulze works with ranking, so we add as many numbers as there are alternatives
        stars = len(proposals)
        max_stars = self.context.poll_settings.get('max_stars', 5)
        min_stars = self.context.poll_settings.get('min_stars', 5)
        if max_stars < stars:
            stars = max_stars
        if min_stars > stars:
            stars = min_stars
        #SelectWidget expects a list where each item has a value and a readable title  (value, title)
        #the title should be the value reversed so 5 stars doesn't say "1" although it really is that value.
        schulze_choice = [(str(x), str(stars-x+1)) for x in range(1, stars+1)]
        #Ie 5 stars = 1 point, 1 star 5 points
        schulze_choice.reverse()
        valid_entries = [str(x) for x in range(1, stars+2)] #To include the missing value
        #This schema creation method is due to legacy code.
        schema = SchulzePollSchema()
        for proposal in proposals:
            title = "#%s: %s" % (proposal.aid, proposal.text)
            schema.add(colander.SchemaNode(colander.String(),
                                           name = proposal.uid,
                                           #To make missing even less desired than the regular stars
                                           #Schulze can't handle null value or empty dicts.
                                           #This does however produce the same result
                                           missing = stars+1,
                                           title = title,
                                           validator = colander.OneOf(valid_entries),
                                           widget = deform.widget.RadioChoiceWidget(values = schulze_choice,
                                                                                    template = 'star_choice',
                                                                                    readonly_template = 'readonly/star_choice')))
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
        if ballots:
            winners = self.context.poll_settings.get('winners', 1)
            schulze_ballots = self.schulze_format_ballots(ballots)
            self.context.poll_result = SchulzeSTV(schulze_ballots,
                                                  ballot_notation = "ranking",
                                                  required_winners = winners).as_dict()
        else:
            #No votes!
            self.context.poll_result = {'candidates': set(self.context.proposal_uids)}

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

    def render_result(self, view):
        winner_uids = self.context.poll_result.get('winners', set())
        winners = []
        for uid in winner_uids:
            winners.append(view.resolve_uid(uid))
        looser_uids = set(self.context.poll_result['candidates']) - winner_uids
        loosers = []
        for uid in looser_uids:
            loosers.append(view.resolve_uid(uid))
        response = {}
        response['context'] = self.context
        response['winners'] = winners
        response['loosers'] = loosers
        return render('templates/result_stv.pt', response, request = view.request)


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
        if ballots:
            schulze_ballots = self.schulze_format_ballots(ballots)
            self.context.poll_result = SchulzePR(schulze_ballots,
                                                 ballot_notation = "ranking").as_dict()
        else:
            self.context.poll_result = {'candidates': set(self.context.proposal_uids)}

    def render_result(self, view):
        response = {}
        proposals = []
        for uid in self.context.poll_result.get('order', ()):
            proposals.append(view.resolve_uid(uid))
        response['proposals'] = proposals
        response['context'] = self.context
        return render('templates/result_pr.pt', response, request = view.request)


def includeme(config):
    config.registry.registerAdapter(SchulzeSTVPollPlugin, name = SchulzeSTVPollPlugin.name)
    config.registry.registerAdapter(SchulzePRPollPlugin, name = SchulzePRPollPlugin.name)
