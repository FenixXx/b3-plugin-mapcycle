Mapcycle Plugin for BigBrotherBot [![BigBrotherBot](http://i.imgur.com/7sljo4G.png)][B3]
===============================

Description
-----------

A [BigBrotherBot][B3] plugin which enhances the mapcycle system of Urban Terror.
At the beginning of every level, it computes the `g_nextmap` according to the maps listed in the plugin configuration
file and the last map played on the server. The algorithm which computes the nextmap ensure to have always a different
level set as `g_nextmap`. It's meant to promote maps that are barely played on the server to make the gameplay more
interesting. The plugin is also capable of setting server cvars according to the level being played: such cvars needs
to be specified in the plugin configuration file.

Download
--------

Latest version available [here](https://github.com/FenixXx/b3-plugin-mapcycle/archive/master.zip).

Installation
------------

* copy the `mapcycle.py` file into `b3/extplugins`
* copy the `plugin_mapcycle.xml` file in `b3/extplugins/conf`
* add to the `plugins` section of your `b3.xml` config file:

  ```xml
  <plugin name="mapcycle" config="@b3/extplugins/conf/plugin_mapcycle.xml" />
  ```

Requirements
------------

* Urban Terror 4.2 server [g_modversion >= 4.2.015]

The plugin relies on the Admin Plugin only (as every other B3 plugin). Although the plugin overrides some commands
declared in other plugins (`!map` from **Admin Plugin** and `!setnextmap`, `!cyclemap` from **PowerAdminUrt Plugin**)
and some functions provided by the **Jumper Plugin**. So, if you have those plugins loaded, make sure that in your `b3.xml`
the mapcycle plugin is loaded after them.

In-game user guide
------------------

* **!lastmap** - `display the last map(s) played on the server`

Support
-------

If you have found a bug or have a suggestion for this plugin, please report it on the [B3 forums][Support].

[B3]: http://www.bigbrotherbot.net/ "BigBrotherBot (B3)"
[Support]: http://forum.bigbrotherbot.net/plugins-by-fenix/mapcycle-plugin/ "Support topic on the B3 forums"

[![Build Status](https://travis-ci.org/FenixXx/b3-plugin-mapcycle.svg?branch=master)](https://travis-ci.org/FenixXx/b3-plugin-mapcycle)