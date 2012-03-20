import unittest

from pyramid import testing
from zope.interface.verify import verifyObject
from zope.interface.verify import verifyClass

from voteit.core.models.agenda_item import AgendaItem
from voteit.core.models.poll import Poll
from voteit.core.models.proposal import Proposal
from voteit.core.models.interfaces import IPollPlugin
from voteit.core.models.interfaces import IVote


class SchulzeSpecificTests(unittest.TestCase):
    def setUp(self):
        #Request needed for wf transitions
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)

    def tearDown(self):
        testing.tearDown()
    
    @property
    def _cut(self):
        from voteit.schulze.models import SchulzePollPlugin
        return SchulzePollPlugin
    
    def test_verify_implementation(self):
        obj = self._cut(Poll())
        self.failUnless(verifyObject(IPollPlugin, obj))

    def test_get_vote_class(self):
        obj = self._cut(Poll())
        self.failUnless(verifyClass(IVote, obj.get_vote_class()))

    def _setup_poll_fixture(self):
        #Enable workflows
        self.config.include('pyramid_zcml')
        self.config.load_zcml('voteit.core:configure.zcml')

        #Register plugin
        self.config.include('voteit.schulze')
        
        request = testing.DummyRequest()
        ai = AgendaItem()
        ai.set_workflow_state(request, 'upcoming')
        ai.set_workflow_state(request, 'ongoing')
        
        #Setup poll
        ai['poll'] = Poll()
        poll = ai['poll']
        
        #Set that we want to use this plugin
        poll.set_field_value('poll_plugin', 'schulze_stv')
        
        #Add proposals
        p1 = Proposal(creators = ['dummy'])
        p1.uid = 'p1uid' #To make it simpler to test against
        ai['p1'] = p1
        p2 = Proposal(creators = ['dummy'])
        p2.uid = 'p2uid'
        ai['p2'] = p2
        p3 = Proposal(creators = ['dummy'])
        p3.uid = 'p3uid'
        ai['p3'] = p3
        
        #Select proposals for this poll
        poll.proposal_uids = (p1.uid, p2.uid, p3.uid)

        #Set poll as ongoing
        poll.set_workflow_state(request, 'upcoming')
        poll.set_workflow_state(request, 'ongoing')

        return poll

    def _add_votes(self, poll):
        plugin = poll.get_poll_plugin()
        ai = poll.__parent__

        #Add 3 votes
        v1 = plugin.get_vote_class()(creators = ['one'])
        v1.set_vote_data({ai['p1'].uid:1, ai['p2'].uid:2, ai['p3'].uid:3})
        poll['v1'] = v1
        
        v2 = plugin.get_vote_class()(creators = ['two'])
        v2.set_vote_data({ai['p1'].uid:1, ai['p2'].uid:2, ai['p3'].uid:3})
        poll['v2'] = v2
        
        v3 = plugin.get_vote_class()(creators = ['three'])
        v3.set_vote_data({ai['p1'].uid:1, ai['p2'].uid:2, ai['p3'].uid:3})
        poll['v3'] = v3

    def test_ballots(self):
        poll = self._setup_poll_fixture()
        self._add_votes(poll)
        poll.close_poll()
        self.assertEqual(poll.ballots, (({u'p1uid': 1, u'p2uid': 2, u'p3uid': 3}, 3),))
    
    def test_close_with_no_votes(self):
        poll = self._setup_poll_fixture()
        self.assertRaises(ValueError, poll.close_poll)
        
    def test_poll_result(self):
        poll = self._setup_poll_fixture()
        self._add_votes(poll)
        poll.close_poll()
        self.assertEqual({'winners': set([u'p1uid']), 'candidates': set([u'p1uid', u'p2uid', u'p3uid'])}, poll.poll_result)

    def test_render_raw_data(self):
        poll = self._setup_poll_fixture()
        self._add_votes(poll)
        poll.close_poll()
        plugin = poll.get_poll_plugin()
        #Same as poll.ballots, but as a string
        self.assertEqual(plugin.render_raw_data().body, "(({u'p1uid': 1, u'p2uid': 2, u'p3uid': 3}, 3),)")
            
    def test_render_result(self):
        poll = self._setup_poll_fixture()
        self._add_votes(poll)
        poll.close_poll()
        plugin = poll.get_poll_plugin()
        request = testing.DummyRequest()
        self.assertTrue('Poll result' in plugin.render_result(request))
