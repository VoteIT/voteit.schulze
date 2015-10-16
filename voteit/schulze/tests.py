import unittest

from arche.views.base import BaseView
from pyramid import testing
from pyramid.traversal import find_root
from voteit.core.models.agenda_item import AgendaItem
from voteit.core.models.interfaces import IPollPlugin
from voteit.core.models.interfaces import IVote
from voteit.core.models.meeting import Meeting
from voteit.core.models.poll import Poll
from voteit.core.models.poll_plugin import PollPlugin
from voteit.core.models.proposal import Proposal
from voteit.core.security import unrestricted_wf_transition_to
from voteit.core.testing_helpers import bootstrap_and_fixture
from voteit.core.testing_helpers import attach_request_method
from voteit.core.helpers import creators_info
from voteit.core.helpers import get_userinfo_url
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject
import colander


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
        self.assertIsInstance(obj.get_vote_schema(), colander.Schema)

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
        poll.close_poll()
        marker = object()
        self.assertEqual(poll.poll_result.get('winners', marker), marker)
        self.assertIn('candidates', poll.poll_result)

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
        request.root = find_root(poll)
        request.meeting = request.root['m']
        attach_request_method(request, creators_info, 'creators_info')
        attach_request_method(request, get_userinfo_url, 'get_userinfo_url')
        view = BaseView(poll, request)
        result = plugin.render_result(view)
        self.assertTrue('first proposal' in result)
        self.assertTrue('third proposal' in result)


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
        poll.close_poll()
        marker = object()
        self.assertEqual(poll.poll_result.get('order', marker), marker)
        self.assertIn('candidates', poll.poll_result)

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
        request.root = find_root(poll)
        request.meeting = request.root['m']
        attach_request_method(request, creators_info, 'creators_info')
        attach_request_method(request, get_userinfo_url, 'get_userinfo_url')
        view = BaseView(poll, request)
        result = plugin.render_result(view)
        self.assertTrue('first proposal' in result)
        self.assertTrue('third proposal' in result)


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
    config.testing_securitypolicy('admin', permissive = True)
    config.include('pyramid_chameleon')
    #Register plugin
    config.include('voteit.schulze')
    config.include('arche.models.catalog')
    config.include('voteit.core.models.catalog')
    config.include('voteit.core.models.unread')
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
    p1 = Proposal(creators = ['dummy'], text = 'first proposal')
    p1.uid = 'p1uid' #To make it simpler to test against
    ai['p1'] = p1
    p2 = Proposal(creators = ['dummy'], text = 'second proposal')
    p2.uid = 'p2uid'
    ai['p2'] = p2
    p3 = Proposal(creators = ['dummy'], text = 'third proposal')
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
