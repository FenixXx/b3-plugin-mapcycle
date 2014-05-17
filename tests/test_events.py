#
# Mapcycle Plugin for BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2013 Daniele Pantaleone <fenix@bigbrotherbot.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA


from b3.events import Event
from mock import Mock
from mock import call
from tests import logging_disabled
from tests import MapcycleTestCase

class Test_events(MapcycleTestCase):

    def setUp(self):

        MapcycleTestCase.setUp(self)

        with logging_disabled():
            from b3.fake import FakeClient

        # create some clients
        #self.mike = FakeClient(console=self.console, name="Mike", guid="mikeguid", team=TEAM_FREE, groupBits=1)
        #self.bill = FakeClient(console=self.console, name="Bill", guid="billguid", team=TEAM_FREE, groupBits=1)
        #self.mike.connects("1")
        #self.bill.connects("2")

    def tearDown(self):
        #self.mike.disconnects()
        #self.bill.disconnects()
        MapcycleTestCase.tearDown(self)

    ####################################################################################################################
    ##                                                                                                                ##
    ##   TEST EVENT GAME EXIT                                                                                         ##
    ##                                                                                                                ##
    ####################################################################################################################

    def test_event_game_exit(self):
        # GIVEN
        self.p.nextmap = 'ut4_sanc'
        self.p.setLevelCvars = Mock()
        # WHEN
        self.console.queueEvent(Event(self.console.getEventID('EVT_GAME_EXIT'), None))
        # THEN
        self.p.setLevelCvars.assert_has_calls(call('ut4_sanc', True))

    def test_event_game_exit_with_set_cvar_calls(self):
        # GIVEN
        self.p.nextmap = 'ut4_algiers'
        self.console.setCvar = Mock()
        # WHEN
        self.console.queueEvent(Event(self.console.getEventID('EVT_GAME_EXIT'), None))
        # THEN
        self.console.setCvar.assert_has_calls([call(u'g_gametype', '4'), call(u'g_matchmode', '0')], any_order=True)

    ####################################################################################################################
    ##                                                                                                                ##
    ##   TEST EVENT VOTE PASSED                                                                                       ##
    ##                                                                                                                ##
    ####################################################################################################################

    def test_event_vote_nextmap_passed(self):
        # GIVEN
        self.p.nextmap = 'ut4_casa'
        # WHEN
        self.console.queueEvent(Event(self.console.getEventID('EVT_VOTE_PASSED'), data={'yes': '3', 'no': '2', 'what': 'g_nextmap ut4_uptown'}))
        # THEN
        self.assertEqual(self.p.nextmap, 'ut4_uptown')

    def test_event_vote_map_passed(self):
        # GIVEN
        self.p.nextmap = 'ut4_casa'
        self.p.setLevelCvars = Mock()
        # WHEN
        self.console.queueEvent(Event(self.console.getEventID('EVT_VOTE_PASSED'), data={'yes': '3', 'no': '2', 'what': 'map ut4_uptown'}))
        # THEN
        self.p.setLevelCvars.assert_has_calls(call('ut4_uptown', True))

    def test_event_vote_map_passed_with_set_cvar_calls(self):
        # GIVEN
        self.p.nextmap = 'ut4_casa'
        self.console.setCvar = Mock()
        # WHEN
        self.console.queueEvent(Event(self.console.getEventID('EVT_VOTE_PASSED'), data={'yes': '3', 'no': '2', 'what': 'map ut4_uptown'}))
        # THEN
        self.console.setCvar.assert_has_calls([call(u'g_gametype', '8'), call(u'g_matchmode', '0')], any_order=True)

    def test_event_vote_cyclemap_passed(self):
        # GIVEN
        self.p.nextmap = 'ut4_casa'
        self.p.setLevelCvars = Mock()
        # WHEN
        self.console.queueEvent(Event(self.console.getEventID('EVT_VOTE_PASSED'), data={'yes': '3', 'no': '2', 'what': 'cyclemap'}))
        # THEN
        self.p.setLevelCvars.assert_has_calls(call('ut4_casa', True))

    def test_event_vote_cyclemap_passed_with_set_cvar_calls(self):
        # GIVEN
        self.p.nextmap = 'ut4_casa'
        self.console.setCvar = Mock()
        # WHEN
        self.console.queueEvent(Event(self.console.getEventID('EVT_VOTE_PASSED'), data={'yes': '3', 'no': '2', 'what': 'cyclemap'}))
        # THEN
        self.console.setCvar.assert_has_calls([call(u'g_gametype', '7'), call(u'g_matchmode', '1')], any_order=True)

    ####################################################################################################################
    ##                                                                                                                ##
    ##   TEST EVENT GAME MAP CHANGE                                                                                   ##
    ##                                                                                                                ##
    ####################################################################################################################

    def test_event_game_map_change_complete(self):
        # GIVEN
        self.console.storage.query("INSERT INTO maphistory(mapname, time_add, time_edit) VALUES ('ut4_casa', '1400328813', '1400328813')")
        self.console.storage.query("INSERT INTO maphistory(mapname, time_add, time_edit) VALUES ('ut4_uptown', '1400328814', '1400328814')")
        self.console.storage.query("INSERT INTO maphistory(mapname, time_add, time_edit) VALUES ('ut4_abbey', '1400328815', '1400328815')")
        self.console.storage.query("INSERT INTO maphistory(mapname, time_add, time_edit) VALUES ('ut4_jupiter', '1400328816', '1400328816')")
        self.p.nextmap = 'ut4_sanc'
        self.p.setLevelCvars = Mock()
        self.console.setCvar = Mock()
        # WHEN
        self.console.queueEvent(Event(self.console.getEventID('EVT_GAME_MAP_CHANGE'), {'old': 'ut4_casa', 'new': 'ut4_sanc'}))
        # THEN
        self.p.setLevelCvars.assert_has_calls(call('ut4_sanc', False))
        self.assertListEqual(self.p.getLastMaps(0, len(self.p.mapcycle) - 1), ['ut4_sanc', 'ut4_jupiter', 'ut4_abbey', 'ut4_uptown', 'ut4_casa'])
        self.assertIn(self.p.nextmap, ['ut4_algiers', 'ut4_toxic'])
        self.console.setCvar.assert_has_calls(call('g_nextmap', self.p.nextmap))