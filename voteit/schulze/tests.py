import unittest

from pyramid import testing
from zope.interface.verify import verifyObject
from zope.interface.verify import verifyClass

from voteit.core import register_poll_plugin
from voteit.core.models.poll import Poll
from voteit.core.models.proposal import Proposal
from voteit.core.models.interfaces import IPollPlugin
from voteit.core.models.interfaces import IVote


class SchulzeSpecificTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()
    
    @property
    def _class(self):
        from voteit.schulze.models import SchulzePollPlugin
        return SchulzePollPlugin
    
    def test_verify_implementation(self):
        obj = self._class(Poll())
        self.failUnless(verifyObject(IPollPlugin, obj))

    def test_get_vote_class(self):
        obj = self._class(Poll())
        self.failUnless(verifyClass(IVote, obj.get_vote_class()))

    def _setup_poll_fixture(self):
        #Enable workflows
        self.config.include('pyramid_zcml')
        self.config.load_zcml('voteit.core:configure.zcml')
        
        #Register plugin
        register_poll_plugin(self._class, verify=0, registry=self.config.registry)
        
        #Setup poll
        poll = Poll()
        #Set that we want to use this plugin
        poll.set_field_value('poll_plugin', 'schulze_stv')
        
        #Add proposals
        p1 = Proposal()
        p1.uid = 'p1uid' #To make it simpler to test against
        poll['p1'] = p1
        p2 = Proposal()
        p2.uid = 'p2uid'
        poll['p2'] = p2
        p3 = Proposal()
        p3.uid = 'p3uid'
        poll['p3'] = p3
        
        #Select proposals for this poll
        poll.proposal_uids = (p1.uid, p2.uid, p3.uid)
        
        return poll

    def test_integration(self):
        poll = self._setup_poll_fixture()
        
        plugin = poll.get_poll_plugin()

        #Add 3 votes
        v1 = plugin.get_vote_class()()
        v1.set_vote_data({poll['p1'].uid:1, poll['p2'].uid:2, poll['p3'].uid:3})
        poll['v1'] = v1
        
        v2 = plugin.get_vote_class()()
        v2.set_vote_data({poll['p1'].uid:1, poll['p2'].uid:2, poll['p3'].uid:3})
        poll['v2'] = v2
        
        v3 = plugin.get_vote_class()()
        v3.set_vote_data({poll['p1'].uid:1, poll['p2'].uid:2, poll['p3'].uid:3})
        poll['v3'] = v3
        
        request = testing.DummyRequest()
        poll.set_workflow_state(request, 'planned')
        poll.set_workflow_state(request, 'ongoing')
        poll.set_workflow_state(request, 'closed')

        self.assertEqual({'winners': set([u'p1uid']), 'candidates': set([u'p1uid', u'p2uid', u'p3uid'])}, poll.poll_result)
        