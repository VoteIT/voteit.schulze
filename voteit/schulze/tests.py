import unittest

import colander
from pyramid import testing
from zope.interface.verify import verifyObject
from zope.interface.verify import verifyClass

from voteit.core.models.agenda_item import AgendaItem
from voteit.core.models.meeting import Meeting
from voteit.core.models.poll import Poll
from voteit.core.models.poll_plugin import PollPlugin
from voteit.core.models.proposal import Proposal
from voteit.core.models.interfaces import IPollPlugin
from voteit.core.models.interfaces import IVote
from voteit.core.security import unrestricted_wf_transition_to
from voteit.core.testing_helpers import bootstrap_and_fixture


class SchulzeBaseTests(unittest.TestCase):
    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)

    def tearDown(self):
        testing.tearDown()
    
    @property
    def _cut(self):
        from voteit.schulze.models import SchulzeBase
        return SchulzeBase            

    @property
    def _dummy_plugin(self):
        class DummyPlugin(self._cut, PollPlugin):
            pass
        return DummyPlugin

    def test_get_vote_schema(self):
        poll = _setup_poll_fixture(self.config)
        obj = self._dummy_plugin(poll)
        
        request = testing.DummyRequest()
        from voteit.core.views.api import APIView
        api = APIView(poll, request)
        
        self.assertIsInstance(obj.get_vote_schema(request, api), colander.SchemaNode)

    def test_render_raw_data(self):
        poll = _setup_poll_fixture(self.config)
        #We need a proper poll plugin for this test
        poll.set_field_value('poll_plugin', 'schulze_stv')
        _add_votes(poll)
        poll.close_poll()
        plugin = poll.get_poll_plugin()
        #Same as poll.ballots, but as a string
        self.assertEqual(plugin.render_raw_data().body, "(({u'p1uid': 1, u'p2uid': 2, u'p3uid': 3}, 3),)")

    def test_schulze_format_ballots(self):
        poll = _setup_poll_fixture(self.config)
        #We need a proper poll plugin for this test
        poll.set_field_value('poll_plugin', 'schulze_stv')
        _add_votes(poll)
        poll.close_poll()
        plugin = poll.get_poll_plugin()
        self.assertEqual(plugin.schulze_format_ballots(poll.ballots),
                         [{'count': 3, 'ballot': {u'p1uid': 1, u'p2uid': 2, u'p3uid': 3}}])

    def test_get_vote_class(self):
        #From poll plugin base, but still good to test
        obj = self._dummy_plugin(Poll())
        self.failUnless(verifyClass(IVote, obj.get_vote_class()))


class SchulzeSTVTests(unittest.TestCase):
    def setUp(self):
        #Request needed for wf transitions
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)

    def tearDown(self):
        testing.tearDown()
    
    @property
    def _cut(self):
        from voteit.schulze.models import SchulzeSTVPollPlugin
        return SchulzeSTVPollPlugin
    
    def test_verify_obj_implementation(self):
        obj = self._cut(Poll())
        self.failUnless(verifyObject(IPollPlugin, obj))

    def test_verify_class_implementation(self):
        self.failUnless(verifyClass(IPollPlugin, self._cut))

    def test_get_settings_schema(self):
        obj = self._cut(Poll())
        schema = obj.get_settings_schema()
        self.assertIsInstance(schema, colander.SchemaNode)

    def test_ballots(self):
        poll = _setup_poll_fixture(self.config)
        poll.set_field_value('poll_plugin', 'schulze_stv')
        _add_votes(poll)
        poll.close_poll()
        self.assertEqual(poll.ballots, (({u'p1uid': 1, u'p2uid': 2, u'p3uid': 3}, 3),))

    def test_close_with_no_votes(self):
        poll = _setup_poll_fixture(self.config)
        poll.set_field_value('poll_plugin', 'schulze_stv')
        self.assertRaises(ValueError, poll.close_poll)

    def test_poll_result(self):
        poll = _setup_poll_fixture(self.config)
        poll.set_field_value('poll_plugin', 'schulze_stv')
        _add_votes(poll)
        poll.close_poll()
        self.assertEqual({'winners': set([u'p1uid']), 'candidates': set([u'p1uid', u'p2uid', u'p3uid'])}, poll.poll_result)

    def test_render_result(self):
        poll = _setup_poll_fixture(self.config)
        poll.set_field_value('poll_plugin', 'schulze_stv')
        _add_votes(poll)
        poll.close_poll()
        plugin = poll.get_poll_plugin()
        request = testing.DummyRequest()
        from voteit.core.views.api import APIView
        api = APIView(poll, request)
        self.assertTrue('Poll result' in plugin.render_result(request, api))


class SchulzePRTests(unittest.TestCase):
    def setUp(self):
        #Request needed for wf transitions
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from voteit.schulze.models import SchulzePRPollPlugin
        return SchulzePRPollPlugin
    
    def test_verify_obj_implementation(self):
        obj = self._cut(Poll())
        self.failUnless(verifyObject(IPollPlugin, obj))

    def test_verify_class_implementation(self):
        self.failUnless(verifyClass(IPollPlugin, self._cut))

    def test_get_settings_schema(self):
        obj = self._cut(Poll())
        schema = obj.get_settings_schema()
        self.assertIsInstance(schema, colander.SchemaNode)
        self.assertNotIn('winners', schema)

    def test_ballots(self):
        poll = _setup_poll_fixture(self.config)
        poll.set_field_value('poll_plugin', 'schulze_pr')
        _add_votes(poll)
        poll.close_poll()
        self.assertEqual(poll.ballots, (({u'p1uid': 1, u'p2uid': 2, u'p3uid': 3}, 3),))

    def test_close_with_no_votes(self):
        poll = _setup_poll_fixture(self.config)
        poll.set_field_value('poll_plugin', 'schulze_pr')
        self.assertRaises(ValueError, poll.close_poll)

    def test_poll_result(self):
        poll = _setup_poll_fixture(self.config)
        poll.set_field_value('poll_plugin', 'schulze_pr')
        _add_votes(poll)
        poll.close_poll()
        self.assertEqual(poll.poll_result['candidates'],
                         set([u'p1uid', u'p2uid', u'p3uid']))
        self.assertEqual(poll.poll_result['order'],
                         [u'p1uid', u'p2uid', u'p3uid'])
        self.assertEqual(poll.poll_result['rounds'],
                         [{'winner': u'p1uid'}, {'winner': u'p2uid'}, {'winner': u'p3uid'}])

    def test_render_result(self):
        poll = _setup_poll_fixture(self.config)
        poll.set_field_value('poll_plugin', 'schulze_pr')
        _add_votes(poll)
        poll.close_poll()
        plugin = poll.get_poll_plugin()
        request = testing.DummyRequest()
        from voteit.core.views.api import APIView
        api = APIView(poll, request)
        self.assertTrue('Poll result' in plugin.render_result(request, api))


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_stv_included(self):
        self.config.include('voteit.schulze')
        poll = Poll()
        self.failUnless(self.config.registry.queryAdapter(poll, IPollPlugin, name = 'schulze_stv'))

    def test_pr_included(self):
        self.config.include('voteit.schulze')
        poll = Poll()
        self.failUnless(self.config.registry.queryAdapter(poll, IPollPlugin, name = 'schulze_pr'))


def _setup_poll_fixture(config):

    #Register plugin
    config.include('voteit.schulze')
    
    config.include('voteit.core.testing_helpers.register_catalog')
    config.include('voteit.core.testing_helpers.register_security_policies')
    config.scan('voteit.core.subscribers.catalog')    
    config.scan('voteit.core.views.components.proposals')
    config.scan('voteit.core.views.components.creators_info')
    config.scan('voteit.core.views.components.metadata_listing')
    root = bootstrap_and_fixture(config)
    
    root['m'] = Meeting()
    unrestricted_wf_transition_to(root['m'], 'ongoing')
    root['m']['ai'] = ai = AgendaItem()
    unrestricted_wf_transition_to(ai, 'upcoming')
    unrestricted_wf_transition_to(ai, 'ongoing')
    
    #Setup poll
    ai['poll'] = Poll()
    poll = ai['poll']
    
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
    unrestricted_wf_transition_to(poll, 'upcoming')
    unrestricted_wf_transition_to(poll, 'ongoing')

    return poll

def _add_votes(poll):
    plugin = poll.get_poll_plugin()
    ai = poll.__parent__

    #Add 3 votes
    v1 = plugin.get_vote_class()(creators = ['one'])
    v1.set_vote_data({ai['p1'].uid:1, ai['p2'].uid:2, ai['p3'].uid:3}, notify = False)
    poll['v1'] = v1
    
    v2 = plugin.get_vote_class()(creators = ['two'])
    v2.set_vote_data({ai['p1'].uid:1, ai['p2'].uid:2, ai['p3'].uid:3}, notify = False)
    poll['v2'] = v2
    
    v3 = plugin.get_vote_class()(creators = ['three'])
    v3.set_vote_data({ai['p1'].uid:1, ai['p2'].uid:2, ai['p3'].uid:3}, notify = False)
    poll['v3'] = v3
