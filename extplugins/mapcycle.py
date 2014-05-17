#
# Mapcycle Plugin for BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2013 Daniele Pantaleone <fenix@bigbrotherbot.net)
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
#
# CHANGELOG
#
#   16/05/2014 - 1.6 - Fenix
#   * code cleanup
#   * added SQLite compatibility
#   * added automated tests
#   * JumperPlugin integration
#   * make use of the built-in event EVT_GAME_MAP_CHANGE
#   * removed doMapcycleRoutine execution from B3 startup
#   17/05/2014 - 1.6.1 - Fenix
#   * removed B3 1.9.x compatibility: iourt42 parser needed is shipped withj B3 1.10dev

__author__ = 'Fenix'
__version__ = '1.6.1'

import b3
import b3.plugin
import b3.events
import time
import re

from ConfigParser import NoOptionError
from ConfigParser import NoSectionError
from random import randrange
from xml.dom import minidom
from b3.plugins.admin import AdminPlugin
from b3.functions import getCmd


class MapcyclePlugin(b3.plugin.Plugin):
    
    adminPlugin = None
    jumperPlugin = None
    nextmap = None

    mapcycle = {}
    settings = {'last_map_limit': 3}

    # this will hold the reference to the correct
    # getMapsSoundingLike() function to be used
    getMapsSoundingLike = None

    sql = {
        ## DATA STORAGE/RETRIEVAL
        'q1': """INSERT INTO maphistory(mapname, time_add, time_edit) VALUES ('%s', '%d', '%d')""",
        'q2': """UPDATE maphistory SET num_played = '%d', time_edit = '%d' WHERE mapname = '%s'""",
        'q3': """SELECT * FROM maphistory WHERE mapname = '%s'""",
        'q4': """SELECT * FROM maphistory ORDER BY time_edit DESC LIMIT %d, %d""",

        ## DATABASE SETUP
        'mysql': """CREATE TABLE IF NOT EXISTS maphistory (
                    id int(10) unsigned NOT NULL AUTO_INCREMENT,
                    mapname varchar(60) DEFAULT NULL,
                    num_played int(10) unsigned NOT NULL DEFAULT '1',
                    time_add int(10) unsigned NOT NULL,
                    time_edit int(10) unsigned NOT NULL,
                    PRIMARY KEY (id)
                    ) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1;""",
        'sqlite': """CREATE TABLE IF NOT EXISTS maphistory (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     mapname VARCHAR(64) DEFAULT NULL,
                     num_played INTEGER NOT NULL DEFAULT '1',
                     time_add INTEGER NOT NULL,
                     time_edit INTEGER NOT NULL);"""
    }

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
        self.adminPlugin = self.console.getPlugin('admin')
        if not self.adminPlugin:
            self.critical('could not start without admin plugin')
            raise SystemExit(220)

        self.jumperPlugin = self.console.getPlugin('jumper')
        if not self.jumperPlugin:
            # use the built-in function
            self.getMapsSoundingLike = self.console.getMapsSoundingLike
        else:
            # use the custom version of the function which will skip std maps
            self.getMapsSoundingLike = self.jumperPlugin.getMapsSoundingLike

        # override map command in the admin plugin
        AdminPlugin.cmd_map = self.cmd_map

        try:
            # override command in the PowerAdminUrt Plugin if available
            import b3.extplugins.poweradminurt.Poweradminurtplugin as Poweradminurtplugin
            Poweradminurtplugin.cmd_pasetnextmap = self.cmd_pasetnextmap
            Poweradminurtplugin.cmd_pacyclemap = self.cmd_pacyclemap
        except ImportError:
            self.debug('not overriding PowerAdminUrt commands: PowerAdminUrt Plugin is not loaded')
            pass

    def onLoadConfig(self):
        """
        Load plugin configuration
        """
        try:
            self.settings['last_map_limit'] = self.config.getint('settings', 'lastmaplimit')
            self.debug('loaded settings/lastmaplimit setting: %s' % self.settings['last_map_limit'])
        except NoOptionError:
            self.warning('could not find settings/lastmaplimit in config file, '
                         'using default: %s' % self.settings['last_map_limit'])
        except ValueError, e:
            self.error('could not load settings/lastmaplimit config value: %s' % e)
            self.debug('using default value (%s) for settings/lastmaplimit' % self.settings['last_map_limit'])

        # parse the mapcycle
        self.getMapcycleFromConfig()

    def onStartup(self):
        """
        Initialize plugin settings
        """
        # create database tables (if needed)
        if not 'maphistory' in self.console.storage.getTables():
            protocol = self.console.storage.dsnDict['protocol']
            self.console.storage.query(self.sql[protocol])

        # register our commands
        if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2:
                    cmd, alias = sp

                func = getCmd(self, cmd)
                if func:
                    self.adminPlugin.registerCommand(self, cmd, level, func, alias)

        self.registerEvent(self.console.getEventID('EVT_GAME_MAP_CHANGE'), self.onLevelStart)
        self.registerEvent(self.console.getEventID('EVT_VOTE_PASSED'), self.onVotePassed)
        self.registerEvent(self.console.getEventID('EVT_GAME_EXIT'), self.onGameExit)

    ####################################################################################################################
    ##                                                                                                                ##
    ##   EVENTS                                                                                                       ##
    ##                                                                                                                ##
    ####################################################################################################################

    def onLevelStart(self, event):
        """
        Handle EVT_GAME_WARMUP and EVT_GAME_ROUND_START
        """
        mapname = event.data['new']
        self.setLevelCvars(mapname, False)
        self.getMapcycleFromConfig()
        self.doMapcycleRoutine(mapname)

    def onVotePassed(self, event):
        """
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
            self.setLevelCvars(m.group('args'), True)
        elif m.group('type') == 'cyclemap':
            self.setLevelCvars(self.nextmap, True)

    def onGameExit(self, event):
        """
        Handle EVT_GAME_EXIT
        """
        self.setLevelCvars(self.nextmap, True)
                
    ####################################################################################################################
    ##                                                                                                                ##
    ##   OTHER METHODS                                                                                                ##
    ##                                                                                                                ##
    ####################################################################################################################

    def getMapcycleFromConfig(self):
        """
        Retrieve the mapcycle from the configuration file
        """
        # empty the dict
        self.mapcycle = {}
        self.debug('retrieving mapcycle maps list from XML configuration file...')

        try:
            document = minidom.parse(self.config.fileName)
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

    def doMapcycleRoutine(self, mapname):
        """
        Execute the mapcycle routine
        """
        if not mapname:
            self.warning('could not execute mapcycle routine: unable to retrieve current mapname')
            return

        if not self.mapcycle:
            self.warning('could not execute mapcycle routine: mapcycle maps list is empty')
            return

        cursor = self.console.storage.query(self.sql['q3'] % mapname)
        if cursor.EOF:
            # if it's the first time we are playing this map, store a new record
            self.verbose("storing new data for map '%s'" % mapname)
            self.console.storage.query(self.sql['q1'] % (mapname, time.time(), time.time()))
        else:
            # if this map has been already played previously, update the old record
            num_played = int(cursor.getRow()['num_played']) + 1
            self.verbose("updating data for map '%s': num_played = %d" % (mapname, num_played))
            self.console.storage.query(self.sql['q2'] % (num_played, time.time(), mapname))

        cursor.close()

        list1 = self.getLastMaps(start=0, limit=len(self.mapcycle) - 1)
        list2 = []

        # print last played map list and num of elements in log file for debugging purpose
        self.verbose("[LIST] mapcycle contains %s elements: %s " % (len(self.mapcycle), ', '.join(self.mapcycle.keys())))
        self.verbose("[LIST] discarding %s maps in nextmap selection: %s" % (len(list1), ', '.join(list1)))

        # Looking for a map not being played
        # recently so we can use it as nextmap
        for m in self.mapcycle.keys():
            if m not in list1:
                list2.append(m)

        # if no map is left
        if not list2:
            self.warning('could not execute mapcycle routine: no suitable map left')
            return

        # print available map list and num of elements in log file for debugging purpose
        self.verbose("[LIST] there are %s available maps for nextmap selection: %s" % (len(list2), ', '.join(list2)))

        # selecting a random nextmap among the list
        randint = randrange(len(list2))
        self.nextmap = list2[randint]
        self.console.setCvar('g_nextmap', list2[randint])

    @staticmethod
    def isCvarLatch(name):
        """
        Tells if a cvar is latch or not
        """
        return name in [
            'bot_enable',
            'g_bombplanttime',
            'g_gametype',
            'g_matchmode',
            'g_maxgameclients',
            'sv_maxclients']

    def setLevelCvars(self, mapname, latch=False):
        """
        Set the given map cvars
        """
        if mapname is not None and mapname in self.mapcycle.keys():
            for key, value in self.mapcycle[mapname].iteritems():
                if self.isCvarLatch(key) == latch:
                    self.console.setCvar(key, value)

    def getLastMaps(self, start, limit):
        """
        Returns a list with the last maps played
        """
        cursor = self.console.storage.query(self.sql['q4'] % (start, limit))
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
        """
        <map> - switch current map
        """
        if not data:
            client.message('missing data, try ^3!^7help map')
            return

        match = self.getMapsSoundingLike(data)
        if isinstance(match, list):
            client.message('do you mean: ^3%s?' % '^7, ^3'.join(match[:5]))
            return

        if isinstance(match, basestring):
            cmd.sayLoudOrPM(client, '^7changing map to ^3%s' % match)
            time.sleep(1)
            self.console.write('map %s' % match)
            return

        # no map found
        client.message('^7could not find any map matching ^1%s' % data)

    def cmd_pasetnextmap(self, data, client=None, cmd=None):
        """
        [<mapname>] - set the nextmap (partial map name works)
        """
        if not data:
            # random choice from mapcycle
            list1 = self.mapcycle.keys()
            data = list1[randrange(len(list1))]

        match = self.getMapsSoundingLike(data)
        if isinstance(match, list):
            client.message('do you mean: ^3%s?' % '^7, ^3'.join(match[:5]))
            return

        if isinstance(match, basestring):
            self.nextmap = match
            self.console.setCvar('g_nextmap', match)
            if client:
                client.message('^7nextmap set to ^3%s' % match)
            return

        # no map found
        client.message('^7could not find any map matching ^1%s' % data)

    def cmd_pacyclemap(self, data, client, cmd=None):
        """
        Cycle to the next map
        """
        # set level cvars before switching
        nextmap = self.nextmap
        cvar = self.console.getCvar('g_nextmap')
        if cvar:
            # if we got a valid cvar, use this value
            self.nextmap = cvar.getString()
            nextmap = self.nextmap

        self.setLevelCvars(nextmap, latch=True)
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
        list1 = self.getLastMaps(1, self.settings['last_map_limit'])
        if not list1:
            client.message('^7could not retrieve last map(s)')
            return

        # print in-game the last map played
        cmd.sayLoudOrPM(client, '^7Last map%s: ^3%s' % ('s' if len(list1) > 1 else '', '^7, ^3'.join(list1)))