CREATE TABLE IF NOT EXISTS `maphistory` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `mapname` varchar(60) DEFAULT NULL,
  `num_played` int(10) unsigned NOT NULL DEFAULT '1',
  `time_add` int(10) unsigned NOT NULL,
  `time_edit` int(10) unsigned NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;