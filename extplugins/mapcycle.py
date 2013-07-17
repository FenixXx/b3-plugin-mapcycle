#
# Mapcycle Plugin for BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2013 Fenix <fenix@urbanterror.info)
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

__author__ = 'Fenix - http://www.urbanterror.info'
__version__ = '1.1'

import b3
import b3.plugin
import b3.events
import re
import os
import random
    
class MapcyclePlugin(b3.plugin.Plugin):
    
    _adminPlugin = None
    
    _lastmaplimit = 3
    _mapcycleFile = None
    _mapcycle = []
    
    _team_gametype = ('tdm', 'ts', 'ftl', 'cah', 'ctf', 'bm')
    
    _sql = { 'q1' : "INSERT INTO `maplist`(`mapname`, `time_add`, `time_edit`) VALUES ('%s', '%d', '%d')", 
             'q2' : "UPDATE `maplist` SET `num_played` = '%d', `time_edit` = '%d' WHERE `mapname` = '%s'",
             'q3' : "SELECT * FROM `maplist` WHERE `mapname` = '%s'", 
             'q4' : "SELECT * FROM `maplist` ORDER BY `time_edit` DESC LIMIT 1, %d", }
                
    
    def onLoadConfig(self):
        """
        Load plugin configuration
        """
        self.verbose('Loading configuration file...')
        
        try:
            self._lastmaplimit = self.config.getint('settings', 'lastmaplimit')
            self.debug('Loaded last map command limit: %d' % self._lastmaplimit)
        except Exception, e:
            self.error('Unable to load last map command limit: %s' % e)
            self.debug('Using default value last map command limit: %d' % self._lastmaplimit)
            
             
    def onStartup(self):
        """
        Initialize plugin settings
        """
        # Get the admin plugin
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:    
            self.error('Could not find admin plugin')
            return False
        
        # Register our commands
        if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2: 
                    cmd, alias = sp

                func = self.getCmd(cmd)
                if func: 
                    self._adminPlugin.registerCommand(self, cmd, level, func, alias)
                    
        # Register the events needed
        self.registerEvent(b3.events.EVT_GAME_WARMUP)
        self.registerEvent(b3.events.EVT_GAME_ROUND_START)
            
            
    # ######################################################################################### #
    # ##################################### HANDLE EVENTS ##################################### #        
    # ######################################################################################### #       
        
     
    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if event.type == b3.events.EVT_GAME_WARMUP:
            if self.console.game.gameType in self._team_gametype:
                self.onMapStart()
        
        elif event.type == b3.events.EVT_GAME_ROUND_START:
            if self.console.game.gameType not in self._team_gametype:
                self.onMapStart()     
            
        
    # ######################################################################################### #
    # ####################################### FUNCTIONS ####################################### #        
    # ######################################################################################### #
        
        
    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
        return None     
    
    
    def getLastMap(self):
        """
        Returns a list with the last map played
        """
        cursor = self.console.storage.query(self._sql['q4'] % self._lastmaplimit)
        
        if cursor.EOF:
            cursor.close()
            return []
        
        maplist = []
        while not cursor.EOF:
            r = cursor.getRow()
            maplist.append(r['mapname'])
            cursor.moveNext()
        
        cursor.close()
        
        return maplist
    
    
    def getMapList(self):
        """
        Return a list with all the maps listed in the mapcycle.txt file
        """
        if self._mapcycleFile is None:
            
            try:
                self._mapcycleFile = self.console.getCvar('g_mapcycle').getString().rstrip('/')
                self.debug('Retrieved CVAR[g_mapcycle]: %s' % self._mapcycleFile)
            except Exception, e:
                self.warning('Could not retrieve CVAR[g_mapcycle]: %s' % e)
                self._mapcycleFile = None
                return []
            
        if self.console.game.fs_game is None:
            
            try:
                self.console.game.fs_game = self.console.getCvar('fs_game').getString().rstrip('/')
                self.debug('Retrieved CVAR[fs_game]: %s' % self.console.game.fs_game)
            except Exception, e:
                self.warning('Could not retrieve CVAR[fs_game]: %s' % e)
                self.console.game.fs_game = None
                return []
        
        if self.console.game.fs_basepath is None:
        
            try:
                self.console.game.fs_basepath = self.console.getCvar('fs_basepath').getString().rstrip('/')
                self.debug('Retrieved CVAR[fs_basepath]: %s' % self.console.game.fs_game)
            except Exception, e:
                self.warning('Could not retrieve CVAR[fs_basepath]: %s' % e)
                self.console.game.fs_basepath = None
    
        # Construct a possible mapcycle filepath
        mpath = self.console.game.fs_basepath + '/' + self.console.game.fs_game + '/' + self._mapcycleFile
        
        if not os.path.isfile(mpath):
            self.debug('Could not find mapcycle file at %s' % mpath)
            if self.console.game.fs_homepath is None:
            
                try:
                    self.console.game.fs_homepath = self.console.getCvar('fs_homepath').getString().rstrip('/')
                    self.debug('Retrieved CVAR[fs_homepath]: %s' % self.console.game.fs_game)
                except Exception, e:
                    self.warning('Could not retrieve CVAR[fs_homepath]: %s' % e)
                    self.console.game.fs_homepath = None
                
            # Construct a possible mapcycle filepath
            mpath = self.console.game.fs_homepath + '/' + self.console.game.fs_game + '/' + self._mapcycleFile
    
        if not os.path.isfile(mpath):
            self.debug('Could not find mapcycle file at %s' % mpath)
            self.error('Could not read mapcycle file. File not found!')
            return []
        
        mfile = open(mpath, 'r')
        re_comment_line = re.compile(r"""^\s*(//.*)?$""")
        lines = filter(lambda x: not re_comment_line.match(x), mfile.readlines())

        if not len(lines):
            return []

        maplist = []
        try:
            while True:
                tmp = lines.pop(0).strip()
                if tmp[0] == '{':
                    while tmp[0] != '}':
                        tmp = lines.pop(0).strip()
                    tmp = lines.pop(0).strip()
                maplist.append(tmp)
        except IndexError:
            pass
        
        return maplist
    

    def onMapStart(self):
        """\
        Perform operations on map start
        """
        mapname = self.console.game.mapName
        cursor = self.console.storage.query(self._sql['q3'] % mapname)
        
        if cursor.EOF:
            self.console.storage.query(self._sql['q1'] % (mapname, self.console.time(), self.console.time()))
            cursor.close()
        else:
            r = cursor.getRow()
            num_played = int(r['num_played']) + 1
            self.console.storage.query(self._sql['q2'] % (num_played, self.console.time(), mapname))
            cursor.close()
            
        maplist = self.getMapList()
        if len(maplist) == 0:
            # Mapcycle file couldn't be read so
            # exit here to prevent further failures
            return
        
        # Print some debug in the log file so the user can check the correct behavior of the plugin
        self.debug("Mapcycle file has %d maps: %s" % (len(maplist), ' | '.join(maplist)))
        
        av_maps = []
        lp_maps = []
        
        # Retrieving last played maps in order to compute a proper g_nextmap
        cursor = self.console.storage.query(self._sql['q4'] % (len(maplist) - 1))
        
        while not cursor.EOF:
            r = cursor.getRow()
            lp_maps.append(r['mapname'])
            cursor.moveNext()
            
        cursor.close()
        
        # Print some debug in the log file so the user can check the correct behavior of the plugin
        self.debug("Last %d played maps: %s" % (len(lp_maps), ' | '.join(lp_maps)))
        
        # Looking for a map not being played
        # recently so we can use it as nextmap
        for m in maplist:
            if m not in lp_maps:
                av_maps.append(m)
        
        if len(av_maps) == 0:
            self.warning("No available maps from which to get the nextmap")
            return
        
        # Print some debug in the log file so the user can check the correct behavior of the plugin
        self.debug("List of %d maps available for next cycle: %s" % (len(av_maps), ' | '.join(av_maps)))    
        
        # Setting next map and printing result in-game
        randint = random.randint(0, len(av_maps) - 1)
        self.console.setCvar('g_nextmap', av_maps[randint])
        self.console.say('^7Next Map: ^2%s' % av_maps[randint])
 
 
    # ######################################################################################### #
    # ######################################## COMMANDS ####################################### #        
    # ######################################################################################### #
    
    
    def cmd_lastmap(self, data, client, cmd=None):
        """\
        Display the last map(s) played
        """
        maplist = self.getLastMap()
        
        if len(maplist) == 0:
            cmd.sayLoudOrPM(client, '^7Could not retrieve last map')
            return;
        
        cmd.sayLoudOrPM(client, '^7Last map%s: ^3%s' % ('s' if len(maplist) > 1 else '', '^7,^3 '.join(maplist)))
        
