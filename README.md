Mapcycle Plugin for BigBrotherBot
=================================

## Description

This plugin enhance the mapcycle system of Urban Terror.<br />
At the beginning of every map, it computes the g_NextMap according to the maps listed in the mapcycle file and to the last map played.<br />
The algorithm which computes the nextmap ensure to have always a different level set as g_NextMap; it's meant to promote maps that are barely played on the server to make the gameplay more interesting.<br/>

## How to install

### Installing the plugin

* Copy **mapcycle.py** into **b3/extplugins**
* Copy **mapcycle.xml** into **b3/extplugins/conf**
* Import **mapcycle.sql** into your b3 database
* Load the plugin in your **b3.xml** configuration file

## In-game user guide

* **!lastmap** *Display the last map(s) played on the server*
* **!setnextmap [<mapname>]** *Set the nextmap on the server*

## Support

For support regarding this very plugin you can find me on IRC on **#urbanterror / #goreclan** @ **Quakenet**<br>
For support regarding Big Brother Bot you may ask for help on the official website: http://www.bigbrotherbot.net