from copy import deepcopy
from decimal import Decimal

from pyramid.httpexceptions import HTTPForbidden
from pyramid.renderers import render
from pyramid.response import Response
from pyvotecore.schulze_method import SchulzeMethod
from pyvotecore.schulze_pr import SchulzePR
from pyvotecore.schulze_stv import SchulzeSTV
from voteit.core.models import poll_plugin
import colander
import deform

from voteit.schulze.schemas import SettingsSchema
from voteit.schulze import _
from voteit.schulze.schemas import SchulzePollSchema


def format_ranking(pairs):
    """
    Input looks something like this:
    {(u'bd2c71ca-0444-4d96-8a00-d1bf896e3051', u'0b43972f-0be8-49c6-a1ef-6de2fd5b6fca'): 0,
     (u'bd2c71ca-0444-4d96-8a00-d1bf896e3051', u'fdb177a9-c7e0-4958-8e0d-8e89d0e311b2'): 1,
     (u'fdb177a9-c7e0-4958-8e0d-8e89d0e311b2', u'bd2c71ca-0444-4d96-8a00-d1bf896e3051'): 1,
     (u'0b43972f-0be8-49c6-a1ef-6de2fd5b6fca', u'fdb177a9-c7e0-4958-8e0d-8e89d0e311b2'): 1,
     (u'fdb177a9-c7e0-4958-8e0d-8e89d0e311b2', u'0b43972f-0be8-49c6-a1ef-6de2fd5b6fca'): 1,
     (u'0b43972f-0be8-49c6-a1ef-6de2fd5b6fca', u'bd2c71ca-0444-4d96-8a00-d1bf896e3051'): 2}
    """
    results = {}
    for (pair, rank) in pairs.items():
        preferred = results.setdefault(pair[0], {})
        preferred[pair[1]] = rank
    return results


class SchulzeBase(poll_plugin.PollPlugin):
    """ Common methods for Schulze ballots. This is ment to be a mixin
        for an adapter. It won't work by itself.
    """
    description = _("schulze_base_description",
                    default="Rank proposals with stars - more is better. "
                            "When the result is calculated, each proposal will "
                            "be compared to every other based on preference.")
    proposals_min = 3

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
            title = "#%s" % proposal.aid
            schema.add(colander.SchemaNode(
                colander.String(),
                name = proposal.uid,
                #To make missing even less desired than the regular stars
                #Schulze can't handle null value or empty dicts.
                #This does however produce the same result
                missing = stars+1,
                title = title,
                # FIXME: This is an ugly hack so we can render proposals properly within the widget
                # description-fields won't render html.
                proposal=proposal,
                #description = proposal.text,
                validator = colander.OneOf(valid_entries),
                widget = deform.widget.RadioChoiceWidget(
                    values = schulze_choice,
                    template = 'star_choice',
                    readonly_template = 'readonly/star_choice')))
        schema.description = self.description
        return schema

    def schulze_format_ballots(self, ballots):
        formatted = []
        for (ballot, count) in ballots:
            formatted.append({'count':count, 'ballot':ballot})
        return formatted

    def render_raw_data(self):
        return Response(unicode(self.context.ballots))

    def handle_start(self, request):
        if len(self.context.proposals) < 2:
            raise HTTPForbidden(_("Only one proposal selected, can't start poll."))


class SchulzePollPlugin(SchulzeBase):
    """ Regular Schulze poll - one winner.
    """
    name = 'schulze'
    title = _("Schulze (Single winner with detailed results)")
    description = _("moderator_description_schulze",
                    default = "Ranked poll suitable for most occations where "
                              "you want a single winner. Voters rank proposals with stars.")
    priority = 1
    multiple_winners = False
    criteria = (
        poll_plugin.MajorityWinner(True),
        poll_plugin.MajorityLooser(True),
        poll_plugin.MutialMajority(True),
        poll_plugin.CondorcetWinner(True),
        poll_plugin.CondorcetLooser(True),
        poll_plugin.CloneProof(True),
    )

    def get_settings_schema(self):
        """ Get an instance of the schema used to render a form for editing settings.
        """
        schema = SettingsSchema()
        schema.title = _(u"Poll settings")
        schema.description = _(u"Settings for Schulze STV")
        del schema['winners']
        return schema

    def handle_close(self):
        # IMPORTANT! Use deepcopy, we don't want the SchulzePollPlugin to modify our ballots,
        # just calculate a result
        ballots = deepcopy(self.context.ballots)
        if ballots:
            schulze_ballots = self.schulze_format_ballots(ballots)
            self.context.poll_result = SchulzeMethod(schulze_ballots,
                                                     ballot_notation = "ranking").as_dict()
        else:
            raise HTTPForbidden(_("No votes, cancel the poll instead."))

    def change_states_of(self):
        """ This gets called when a poll has finished.
            It returns a dictionary with proposal uid as key and new state as value.
            Like: {'<uid>':'approved', '<uid>', 'denied'}
        """
        result = {}
        winner = self.context.poll_result.get('winner', '')
        losers = self.context.poll_result['candidates'] - set([winner])
        if winner:
            result[winner] = 'approved'
            for loser in losers:
                result[loser] = 'denied'
        return result

    def render_result(self, view):
        winner_uid = self.context.poll_result.get('winner', set())
        winner = view.resolve_uid(winner_uid)
        tied_winners = []
        for uid in self.context.poll_result.get('tied_winners', ()):
            tied_winners.append(view.resolve_uid(uid))
        looser_uids = set(self.context.poll_result['candidates']) - set([winner_uid])
        loosers = []
        for uid in looser_uids:
            loosers.append(view.resolve_uid(uid))
        response = {}
        response['context'] = self.context
        response['pairs'] = pairs = format_ranking(self.context.poll_result['pairs'])
        response['total_votes'] = total_votes = len(self.context) #Should be ok...
        response['proposals_dict'] = dict([(x.uid, x) for x in self.context.get_proposal_objects()])
        response['winners'] = [winner]
        response['tied_winners'] = tied_winners
        response['loosers'] = loosers
        response['proposals'] = [winner] + loosers
        def _perc(primary_uid, vs_uid):
            primary = Decimal(pairs[primary_uid][vs_uid])
            vs = Decimal(pairs[vs_uid][primary_uid])
            result = {}
            try:
                result[primary_uid] = int(round(primary / total_votes * 100))
            except ZeroDivisionError:
                result[primary_uid] = 0
            try:
                result[vs_uid] = int(round(vs / total_votes * 100))
            except ZeroDivisionError:
                result[vs_uid] = 0
            result['equal'] = 100 - result[primary_uid] - result[vs_uid]
            return result
        response['perc'] = _perc
        return render('templates/result_schulze.pt', response, request = view.request)


class SortedSchulzePollPlugin(SchulzeBase):
    """ A regular Schulze poll that's repeated until everything is sorted.
        This is a non-proportionally ranked method
    """
    name = 'sorted_schulze'
    title = _("Sorted Schulze")
    description = _(
        "moderator_description_sorted_non_proportional",
        default = "A regular Schulze poll is repeated until all "
        "candidates have a ranking. The result is non-proportional, "
        "and each stage produces the condorcet winner "
        "within the remaining candidates. "
        "Voters rank proposals with stars."
    )
    multiple_winners = True
    recommended_for = _("Board elections or sorting proposals according to preference.")
    priority = 3
    criteria = (
        poll_plugin.MajorityWinner(True, comment=_("In each round")),
        poll_plugin.MajorityLooser(True, comment=_("In each round")),
        poll_plugin.MutialMajority(True, comment=_("In each round")),
        poll_plugin.CondorcetWinner(True),
        poll_plugin.CondorcetLooser(True),
        poll_plugin.CloneProof(True),
        poll_plugin.Proportional(False, comment=_("Incompatible with condorcet.")),
    )

    def get_settings_schema(self):
        """ Get an instance of the schema used to render a form for editing settings.
        """
        schema = SettingsSchema()
        schema.title = _(u"Poll settings")
        schema.description = _(u"Settings for Sorted Schulze")
        del schema['winners']
        schema.add(
            colander.SchemaNode(
                colander.Int(),
                title=_("Restrict number of winners"),
                description=_("Use 0 to sort all"),
                default=0,
                missing=0,
            )
        )
        return schema

    def handle_close(self):
        """
        Calculate results per round instead. Each round has exactly 1 winner.
        (It could be a randomized tie though)
        """
        # IMPORTANT! Use deepcopy, we don't want the SortedSchulzePollPlugin to modify our ballots,
        # just calculate a result
        ballots = deepcopy(self.context.ballots)
        wcount = self.context.poll_settings.get('winners', 0)

        if ballots:
            candidates_left = set(self.context.proposals)
            if wcount and len(self.context.proposals) > wcount:
                rounds = wcount
            else:
                rounds = len(self.context.proposals)
            schulze_ballots = self.schulze_format_ballots(ballots)
            round_data = []
            for i in range(rounds):
                if len(candidates_left) > 1:
                    # SchulzeMethod changed the ballots, so we need another copy here!
                    res = SchulzeMethod(deepcopy(schulze_ballots), ballot_notation = "ranking").as_dict()
                    round_data.append(res)
                    schulze_ballots = self.eliminate_candidate(res['winner'], schulze_ballots)
                    candidates_left.remove(res['winner'])
                else:
                    # Only 1 candidate left
                    round_data.append({'winner': list(candidates_left)[0]})
            self.context.poll_result = {
                'rounds': round_data,
                'candidates': set(self.context.proposals),
                'winners': [x['winner'] for x in round_data]
            }
        else:
            raise HTTPForbidden(_("No votes, cancel the poll instead."))

    def eliminate_candidate(self, uid, ballots):
        """ Eliminate a candidate from formatted ballots. """
        for ballot in ballots:
            ballot['ballot'].pop(uid, None)
        return ballots

    def render_result(self, view):
        response = {}
        response['context'] = self.context
        response['total_votes'] = len(self.context) #Should be ok...
        response['proposals_dict'] = dict([(x.uid, x) for x in self.context.get_proposal_objects()])
        response['winners'] = self.context.poll_result.get('winners', ())
        return render('templates/result_sorted_schulze.pt', response, request = view.request)


class SchulzeSTVPollPlugin(SchulzeBase):
    """ Poll plugin for the Schulze STV Polls. """
    name = u'schulze_stv'
    title = _(u"schulze_stv_title", 
              default="Schulze STV (Multiple winner, proportional")
    description = _("moderator_description_schulze_stv",
                    default = "This poll can handle multiple winners too, "
                              "but may suffer from performance problems. "
                              "Each new possible winner increases complexity expontentially. "
                              "Computations may take a very long time with more than 6 winners!")
    selectable = False  # Legacy plugin

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
            raise HTTPForbidden(_("No votes, cancel the poll instead."))

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


class SchulzePRPollPlugin(SchulzeBase):
    """ Poll plugin for the Schulze PR ranking polls. It will sort a list
        of proposals according to the voters preference.
    """
    name = u'schulze_pr'
    title = _(u"schulze_pr_title", 
              default="Schulze PR (Sorted result, proportional)")
    description = _("moderator_description_schulze_pr",
                    default = "This poll sorts all the proposals according "
                              "to the preference of all voters. "
                              "The result will be proportional. "
                              "Note: Computational complexity grows expontentially "
                              "with each added proposal. Over 5 proposals may be tricky. "
                              "Use with caution!")
    selectable = False  # Legacy plugin

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
            raise HTTPForbidden(_("No votes, cancel the poll instead."))

    def render_result(self, view):
        response = {}
        proposals = []
        for uid in self.context.poll_result.get('order', ()):
            proposals.append(view.resolve_uid(uid))
        response['proposals'] = proposals
        response['context'] = self.context
        return render('templates/result_pr.pt', response, request = view.request)


def includeme(config):
    config.registry.registerAdapter(SchulzePollPlugin, name = SchulzePollPlugin.name)
    config.registry.registerAdapter(SortedSchulzePollPlugin, name = SortedSchulzePollPlugin.name)
    config.registry.registerAdapter(SchulzeSTVPollPlugin, name = SchulzeSTVPollPlugin.name)
    config.registry.registerAdapter(SchulzePRPollPlugin, name = SchulzePRPollPlugin.name)
