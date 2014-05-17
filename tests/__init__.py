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

import logging
import unittest2

from textwrap import dedent
from mockito import when
from mapcycle import MapcyclePlugin
from xml.dom import minidom
from ConfigParser import NoSectionError
from b3.cvar import Cvar
from b3.config import XmlConfigParser
from b3.plugins.admin import AdminPlugin
from b3 import __version__ as b3_version

try:
    from b3.parsers.iourt42 import Iourt42Parser
except ImportError:
    HAS_IOURT42_PARSER = False
else:
    HAS_IOURT42_PARSER = True

MAPCYCLE_PLUGIN_CONFIG = r"""
<configuration plugin="mapcycle">
    <settings name="settings">
        <set name='lastmaplimit'>3</set>
    </settings>
    <settings name="commands">
        <set name='lastmap'>2</set>
    </settings>
    <mapcycle>
        <map g_gametype="4" timelimit="10" g_matchmode="1">ut4_abbey</map>
        <map g_gametype="7" timelimit="20" g_matchmode="1">ut4_casa</map>
        <map g_gametype="9" timelimit="90" g_matchmode="0">ut4_jupiter</map>
        <map g_gametype="1" timelimit="10" g_matchmode="0">ut4_toxic</map>
        <map g_gametype="3" timelimit="10" g_matchmode="0">ut4_sanc</map>
        <map g_gametype="4" timelimit="20" g_matchmode="0">ut4_algiers</map>
        <map g_gametype="8" timelimit="30" g_matchmode="0">ut4_uptown</map>
    </mapcycle>
</configuration>
"""


class logging_disabled(object):
    """
    Context manager that temporarily disable logging.

    USAGE:
        with logging_disabled():
            # do stuff
    """
    DISABLED = False

    def __init__(self):
        self.nested = logging_disabled.DISABLED

    def __enter__(self):
        if not self.nested:
            logging.getLogger('output').propagate = False
            logging_disabled.DISABLED = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.nested:
            logging.getLogger('output').propagate = True
            logging_disabled.DISABLED = False


def patch_mapcycle_plugin():

    def getMapcycleFromConfig(self):
        """
        Retrieve the mapcycle from the configuration file
        """
        # empty the dict
        self.mapcycle = {}
        self.console.debug('retrieving mapcycle maps list from XML configuration file...')

        try:
            document = minidom.parseString(dedent(MAPCYCLE_PLUGIN_CONFIG))
            maps = document.getElementsByTagName('map')
            for node in maps:
                mapname = None
                for v in node.childNodes:
                    if v.nodeType == v.TEXT_NODE:
                        mapname = v.data
                        break

                if not mapname:
                    self.warning('could not parse line from configuration file: empty node found')
                    continue

                cvars = {}
                for name, value in node.attributes.items():
                    cvars[name.lower()] = value

                self.mapcycle[mapname] = cvars
                self.debug('map : %s | cvars : %s' % (mapname, str(self.mapcycle[mapname])))

        except NoSectionError, e:
            self.error('could not load mapcycle maps list from XML configuration file: %s' % e)

    MapcyclePlugin.getMapcycleFromConfig = getMapcycleFromConfig


@unittest2.skipUnless(HAS_IOURT42_PARSER, "B3 %s does not have the iourt42 parser" % b3_version)
class MapcycleTestCase(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        with logging_disabled():
            from b3.parsers.q3a.abstractParser import AbstractParser
            from b3.fake import FakeConsole
            AbstractParser.__bases__ = (FakeConsole,)
            # Now parser inheritance hierarchy is :
            # Iourt41Parser -> abstractParser -> FakeConsole -> Parser

    def setUp(self):
        # create a Iourt42 parser
        self.parser_conf = XmlConfigParser()
        self.parser_conf.loadFromString(dedent(r"""
            <configuration>
                <settings name="server">
                    <set name="game_log"></set>
                </settings>
            </configuration>
            """))

        self.console = Iourt42Parser(self.parser_conf)

        # initialize some fixed cvars which will be used by both the plugin and the iourt42 parser
        when(self.console).getCvar('auth').thenReturn(Cvar('auth', value='0'))
        when(self.console).getCvar('fs_basepath').thenReturn(Cvar('g_maxGameClients', value='/fake/basepath'))
        when(self.console).getCvar('fs_homepath').thenReturn(Cvar('sv_maxclients', value='/fake/homepath'))
        when(self.console).getCvar('fs_game').thenReturn(Cvar('fs_game', value='q3ut4'))
        when(self.console).getCvar('gamename').thenReturn(Cvar('gamename', value='q3urt42'))

        # start the parser
        self.console.startup()

        with logging_disabled():
            self.adminPlugin = AdminPlugin(self.console, '@b3/conf/plugin_admin.ini')
            self.adminPlugin.onLoadConfig()
            self.adminPlugin.onStartup()

        # make sure the admin plugin obtained by other plugins is our admin plugin
        when(self.console).getPlugin('admin').thenReturn(self.adminPlugin)

        # force fake mapname here so Mapcycle Plugin will
        # not catch useless EVT_GAME_MAP_CHANGE
        self.console.game.mapName = 'ut4_casa'

        self.conf = XmlConfigParser()
        self.conf.loadFromString(dedent(MAPCYCLE_PLUGIN_CONFIG))

        # patch the mapcycle plugin for testing purpose
        patch_mapcycle_plugin()

        self.p = MapcyclePlugin(self.console, self.conf)
        self.p.onLoadConfig()
        self.p.onStartup()

    def tearDown(self):
        self.console.working = False