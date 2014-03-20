#
# Mapcycle Plugin for BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2013 Fenix <fenix@bigbrotherbot.net)
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

__author__ = 'Fenix'
__version__ = '1.4'

import b3
import b3.plugin
import b3.events
import time
import re

from ConfigParser import NoOptionError
from ConfigParser import NoSectionError
from random import randrange
from xml.dom import minidom


class MapcyclePlugin(b3.plugin.Plugin):
    
    _adminPlugin = None
    _poweradminurtPlugin = None

    _mapcycle = dict()
    _settings = dict(last_map_limit=3)

    _sql = dict(q1="""INSERT INTO `maphistory`(`mapname`, `time_add`, `time_edit`) VALUES ('%s', '%d', '%d')""",
                q2="""UPDATE `maphistory` SET `num_played` = '%d', `time_edit` = '%d' WHERE `mapname` = '%s'""",
                q3="""SELECT * FROM `maphistory` WHERE `mapname` = '%s'""",
                q4="""SELECT * FROM `maphistory` ORDER BY `time_edit` DESC LIMIT %d, %d""")

    nextmap = None

    ####################################################################################################################
    ##                                                                                                                ##
    ##   STARTUP                                                                                                      ##
    ##                                                                                                                ##
    ####################################################################################################################

    def __init__(self, console, config=None):
        """
        Build the plugin object
        """
        b3.plugin.Plugin.__init__(self, console, config)
        if self.console.gameName != 'iourt42':
            self.critical("unsupported game : %s" % self.console.gameName)
            raise SystemExit(220)

        # get the admin plugin
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.critical('could not start without admin plugin')
            raise SystemExit(220)

        # get the poweradminurt plugin
        self._poweradminurtPlugin = self.console.getPlugin('poweradminurt')

        # override other plugin commands
        self._adminPlugin.cmd_map = self.cmd_map

        if self._poweradminurtPlugin:
            self._poweradminurtPlugin.cmd_pacyclemap = self.cmd_pacyclemap
            self._poweradminurtPlugin.cmd_pasetnextmap = self.cmd_pasetnextmap

    def onLoadConfig(self):
        """\
        Load plugin configuration
        """
        try:
            self._settings['last_map_limit'] = self.config.getint('settings', 'lastmaplimit')
            self.debug('loaded settings/lastmaplimit setting: %s' % self._settings['last_map_limit'])
        except NoOptionError:
            self.warning('could not find settings/lastmaplimit in config file, '
                         'using default: %s' % self._settings['last_map_limit'])
        except ValueError, e:
            self.error('could not load settings/lastmaplimit config value: %s' % e)
            self.debug('using default value (%s) for settings/lastmaplimit' % self._settings['last_map_limit'])

    def onStartup(self):
        """\
        Initialize plugin settings
        """
        # create database table if needed
        tables = self.console.storage.getTables()
        if not 'maphistory' in tables:
            self.console.storage.query("""CREATE TABLE IF NOT EXISTS `maphistory` (
                                          `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
                                          `mapname` varchar(60) DEFAULT NULL,
                                          `num_played` int(10) unsigned NOT NULL DEFAULT '1',
                                          `time_add` int(10) unsigned NOT NULL,
                                          `time_edit` int(10) unsigned NOT NULL,
                                          PRIMARY KEY (`id`)
                                          ) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;""")

        # register our commands
        if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2:
                    cmd, alias = sp

                func = self.get_cmd(cmd)
                if func:
                    self._adminPlugin.registerCommand(self, cmd, level, func, alias)
                    
        # register the events needed
        self.registerEvent(self.console.getEventID('EVT_GAME_WARMUP'), self.onLevelStart)
        self.registerEvent(self.console.getEventID('EVT_GAME_ROUND_START'), self.onLevelStart)
        self.registerEvent(self.console.getEventID('EVT_VOTE_PASSED'), self.onVotePassed)
        self.registerEvent(self.console.getEventID('EVT_GAME_EXIT'), self.onGameExit)

        # parse the mapcycle
        self.parse_mapcycle()

        # execute the mapcycle routine
        self.do_mapcycle_routine()

    ####################################################################################################################
    ##                                                                                                                ##
    ##   EVENTS                                                                                                       ##
    ##                                                                                                                ##
    ####################################################################################################################

    def onLevelStart(self, event):
        """\
        Handle EVT_GAME_WARMUP and EVT_GAME_ROUND_START
        """
        # be sure to be at the very map beginning
        if not self.is_level_started(event):
            return

        # parse the mapcycle
        self.parse_mapcycle()

        # execute the mapcycle routine
        self.do_mapcycle_routine()

    def onVotePassed(self, event):
        """\
        Handle EVT_VOTE_PASSED
        """
        r = re.compile(r'''^(?P<type>\w+)\s?(?P<args>.*)$''')
        m = r.match(event.data['what'])
        if not m:
            self.warning('could not parse callvote data: %s' % event.data)
            return

        if m.group('type') == 'g_nextmap':
            self.nextmap = m.group('args')
        elif m.group('type') == 'map':
            self.set_level_cvars(m.group('args'), latch=True)
        elif m.group('type') == 'cyclemap':
            self.set_level_cvars(self.nextmap, latch=True)

    def onGameExit(self, event):
        """\
        Handle EVT_GAME_EXIT
        """
        self.set_level_cvars(self.nextmap, latch=True)
                
    ####################################################################################################################
    ##                                                                                                                ##
    ##   FUNCTIONS                                                                                                    ##
    ##                                                                                                                ##
    ####################################################################################################################
        
    def get_cmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
        return None

    def parse_mapcycle(self):
        """\
        Parse the mapcycle from the configuration file
        """
        try:

            # empty the dict
            self._mapcycle = dict()

            # load the mapcycle map list
            document = minidom.parse(self.config.fileName)
            maps = document.getElementsByTagName('map')
            for node in maps:
                # get the map name to be used as dict key:
                # if it's empty it will just be skipped
                mapname = None
                for v in node.childNodes:
                    if v.nodeType == v.TEXT_NODE:
                        mapname = v.data
                        break

                # if there is no text
                if not mapname:
                    self.warning('could not load mapname from mapcycle map list: empty node found')
                    continue

                cvars = dict()
                for name, value in node.attributes.items():
                    cvars[name.lower()] = value

                # store the map in the dict
                self._mapcycle[mapname] = cvars
                self.debug('loaded map [%s] : %s' % (mapname, self._mapcycle[mapname]))

        except NoSectionError, e:
            self.error('could not load mapcycle list form configuration file: %s' % e)

    def do_mapcycle_routine(self):
        """\
        Execute the mapcycle routine
        """
        # get the current map name
        mapname = self.console.game.mapName
        if not mapname:
            self.warning('could not execute mapcycle routine: mapname appears to be None')
            return

        # set the current level cvars
        self.set_level_cvars(mapname, latch=False)

        # check if this map has been already played previously
        cursor = self.console.storage.query(self._sql['q3'] % mapname)

        if cursor.EOF:
            # if it's the first time we are playing this map, store a new record
            self.console.storage.query(self._sql['q1'] % (mapname, self.console.time(), self.console.time()))
        else:
            # if this map has been already played previously, update the old record
            num_played = int(cursor.getRow()['num_played']) + 1
            self.console.storage.query(self._sql['q2'] % (num_played, self.console.time(), mapname))

        cursor.close()

        # print mapcycle list and num of elements in log file for debugging purpose
        self.verbose('mapcycle is composed of %s maps: %s' % (len(self._mapcycle), ', '.join(self._mapcycle.keys())))

        list1 = []  # holds last played map names
        list2 = []  # holds the maps which are available to be selected as nextmap

        # retrieving last played maps in order to compute a proper g_nextmap
        cursor = self.console.storage.query(self._sql['q4'] % (0, len(self._mapcycle) - 1))

        while not cursor.EOF:
            list1.append(cursor.getRow()['mapname'])
            cursor.moveNext()

        cursor.close()

        # print last played map list and num of elements in log file for debugging purpose
        self.verbose("last played map list is composed of %s maps: %s" % (len(list1), ', '.join(list1)))

        # discarding all the last played maps found
        # in mapcycle map list and building a list of
        # possible choices from where to pick the nextmap

        # Looking for a map not being played
        # recently so we can use it as nextmap
        for m in self._mapcycle.keys():
            if m not in list1:
                list2.append(m)

        # if no map is left
        if len(list2) == 0:
            self.warning('could not compute nextmap to be set on server: no available maps left')
            return

        # print available map list and num of elements in log file for debugging purpose
        self.verbose("available map list is composed of %s maps: %s" % (len(list2), ', '.join(list2)))

        # selecting a random nextmap among the list
        randint = randrange(len(list2))
        self.nextmap = list2[randint]
        self.console.setCvar('g_nextmap', list2[randint])

    def is_level_started(self, event):
        """\
        Tells if the current level just started
        """
        team_modes = ('tdm', 'ts', 'ftl', 'cah', 'ctf', 'bm')
        return (event.type == self.console.getEventID('EVT_GAME_WARMUP') and
                self.console.game.gameType in team_modes) or \
               (event.type == self.console.getEventID('EVT_GAME_ROUND_START') and
                not self.console.game.gameType in team_modes)

    def set_level_cvars(self, mapname, latch=False):
        """\
        Set the given map cvars
        """
        if mapname is not None and mapname in self._mapcycle.keys():
            for key, value in self._mapcycle[mapname].iteritems():
                if self.is_cvar_latch(key) == latch:
                    self.console.setCvar(key, value)

    @staticmethod
    def is_cvar_latch(name):
        """\
        Tells if a cvar is latch or not
        """
        cvarlist = ['bot_enable', 'g_bombplanttime', 'g_gametype', 'g_matchmode', 'g_maxgameclients', 'sv_maxclients']
        return name in cvarlist

    def get_last_maps(self):
        """\
        Returns a list with the last maps played
        """
        cursor = self.console.storage.query(self._sql['q4'] % (1, self._settings['last_map_limit']))
        if cursor.EOF:
            cursor.close()
            return []

        maplist = []
        while not cursor.EOF:
            maplist.append(cursor.getRow()['mapname'])
            cursor.moveNext()

        cursor.close()
        return maplist

    ####################################################################################################################
    ##                                                                                                                ##
    ##   COMMANDS OVERRIDE                                                                                            ##
    ##                                                                                                                ##
    ####################################################################################################################

    def cmd_map(self, data, client, cmd=None):
        """\
        <map> - switch current map
        """
        if not data:
            client.message('missing data, try ^3!^7help map')
            return

        match = self.console.getMapsSoundingLike(data)
        if isinstance(match, list):
            client.message('do you mean: ^3%s ?' % '^7, ^3'.join(match[:5]))
            return

        if isinstance(match, basestring):
            # set level cvars before switching
            self.set_level_cvars(match, latch=True)
            self.console.say('^7changing map to ^3%s' % match)
            time.sleep(1)
            self.console.write('map %s' % match)
            return

        # no map found
        client.message('^7could not find any map matching ^1%s' % data)

    def cmd_pasetnextmap(self, data, client=None, cmd=None):
        """\
        <mapname> - set the nextmap (partial map name works)
        """
        if not data:
            # select a random map from the mapcycle
            maplist = self._mapcycle.keys()
            data = maplist[randrange(len(maplist))]

        match = self.console.getMapsSoundingLike(data)
        if isinstance(match, list):
            client.message('do you mean: ^3%s?' % '^7, ^3'.join(match[:5]))
            return

        if isinstance(match, basestring):
            # mark the new nextmap
            self.nextmap = match
            self.console.setCvar('g_nextmap', match)
            if client:
                client.message('^7nextmap set to ^3%s' % match)

            return

        # no map found
        client.message('^7could not find any map matching ^1%s' % data)

    def cmd_pacyclemap(self, data, client, cmd=None):
        """\
        Cycle to the next map
        """
        # set level cvars before switching
        nextmap = self.nextmap
        cvar = self.console.getCvar('g_nextmap')
        if cvar:
            self.nextmap = cvar.getString()
            nextmap = self.nextmap

        self.set_level_cvars(nextmap, latch=True)
        self.console.say('^7cycling to nextmap ^3%s' % nextmap)
        time.sleep(1)
        self.console.write('cyclemap')
                
    ####################################################################################################################
    ##                                                                                                                ##
    ##   COMMANDS                                                                                                     ##
    ##                                                                                                                ##
    ####################################################################################################################

    def cmd_lastmap(self, data, client, cmd=None):
        """
        Display the last map(s) played
        """
        maplist = self.get_last_maps()
        
        if not maplist:
            client.message('^7could not retrieve last map(s)')
            return

        # print in-game the last map played
        cmd.sayLoudOrPM(client, '^7Last map%s: ^3%s' % ('s' if len(maplist) > 1 else '', '^7, ^3'.join(maplist)))