-- MySQL dump 10.13  Distrib 5.1.69, for redhat-linux-gnu (x86_64)
--
-- Host: localhost    Database: slurmtest_acct_db
-- ------------------------------------------------------
-- Server version	5.1.69

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `slurmtest_assoc_table`
--

DROP TABLE IF EXISTS `slurmtest_assoc_table`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `slurmtest_assoc_table` (
  `creation_time` int(10) unsigned NOT NULL,
  `mod_time` int(10) unsigned NOT NULL DEFAULT '0',
  `deleted` tinyint(4) NOT NULL DEFAULT '0',
  `is_def` tinyint(4) NOT NULL DEFAULT '0',
  `id_assoc` int(11) NOT NULL DEFAULT '0',
  `user` tinytext NOT NULL,
  `acct` tinytext NOT NULL,
  `partition` tinytext NOT NULL,
  `parent_acct` tinytext NOT NULL,
  `lft` int(11) NOT NULL,
  `rgt` int(11) NOT NULL,
  `shares` int(11) NOT NULL DEFAULT '1',
  `max_jobs` int(11) DEFAULT NULL,
  `max_submit_jobs` int(11) DEFAULT NULL,
  `max_cpus_pj` int(11) DEFAULT NULL,
  `max_nodes_pj` int(11) DEFAULT NULL,
  `max_wall_pj` int(11) DEFAULT NULL,
  `max_cpu_mins_pj` bigint(20) DEFAULT NULL,
  `max_cpu_run_mins` bigint(20) DEFAULT NULL,
  `grp_jobs` int(11) DEFAULT NULL,
  `grp_submit_jobs` int(11) DEFAULT NULL,
  `grp_cpus` int(11) DEFAULT NULL,
  `grp_mem` int(11) DEFAULT NULL,
  `grp_nodes` int(11) DEFAULT NULL,
  `grp_wall` int(11) DEFAULT NULL,
  `grp_cpu_mins` bigint(20) DEFAULT NULL,
  `grp_cpu_run_mins` bigint(20) DEFAULT NULL,
  `def_qos_id` int(11) DEFAULT NULL,
  `qos` blob NOT NULL,
  `delta_qos` blob NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `slurmtest_assoc_table`
--

LOCK TABLES `slurmtest_assoc_table` WRITE;
/*!40000 ALTER TABLE `slurmtest_assoc_table` DISABLE KEYS */;
INSERT INTO `slurmtest_assoc_table` VALUES (1369423802,1369423802,0,1,1363,'user1','group1','','',505,506,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'','');
INSERT INTO `slurmtest_assoc_table` VALUES (1369423802,1369423802,0,1,1387,'user2','group2','','',2337,2338,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'','');
INSERT INTO `slurmtest_assoc_table` VALUES (1369423802,1369423802,0,1,2724,'user3','group3','','',1519,1520,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'','');
/*!40000 ALTER TABLE `slurmtest_assoc_table` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `slurmtest_job_table`
--

DROP TABLE IF EXISTS `slurmtest_job_table`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `slurmtest_job_table` (
  `job_db_inx` int(11) NOT NULL DEFAULT '0',
  `mod_time` int(10) unsigned NOT NULL DEFAULT '0',
  `deleted` tinyint(4) NOT NULL DEFAULT '0',
  `account` tinytext,
  `cpus_req` int(10) unsigned NOT NULL,
  `cpus_alloc` int(10) unsigned NOT NULL,
  `derived_ec` int(10) unsigned NOT NULL DEFAULT '0',
  `derived_es` text,
  `exit_code` int(10) unsigned NOT NULL DEFAULT '0',
  `job_name` tinytext NOT NULL,
  `id_assoc` int(10) unsigned NOT NULL,
  `id_block` tinytext,
  `id_job` int(10) unsigned NOT NULL,
  `id_qos` int(10) unsigned NOT NULL DEFAULT '0',
  `id_resv` int(10) unsigned NOT NULL,
  `id_wckey` int(10) unsigned NOT NULL,
  `id_user` int(10) unsigned NOT NULL,
  `id_group` int(10) unsigned NOT NULL,
  `kill_requid` int(11) NOT NULL DEFAULT '-1',
  `nodelist` text,
  `nodes_alloc` int(10) unsigned NOT NULL,
  `node_inx` text,
  `partition` tinytext NOT NULL,
  `priority` int(10) unsigned NOT NULL,
  `state` smallint(5) unsigned NOT NULL,
  `timelimit` int(10) unsigned NOT NULL DEFAULT '0',
  `time_submit` int(10) unsigned NOT NULL DEFAULT '0',
  `time_eligible` int(10) unsigned NOT NULL DEFAULT '0',
  `time_start` int(10) unsigned NOT NULL DEFAULT '0',
  `time_end` int(10) unsigned NOT NULL DEFAULT '0',
  `time_suspended` int(10) unsigned NOT NULL DEFAULT '0',
  `gres_req` text NOT NULL,
  `gres_alloc` text NOT NULL,
  `gres_used` text NOT NULL,
  `wckey` tinytext NOT NULL,
  `track_steps` tinyint(4) NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `slurmtest_job_table`
--

LOCK TABLES `slurmtest_job_table` WRITE;
/*!40000 ALTER TABLE `slurmtest_job_table` DISABLE KEYS */;
INSERT INTO `slurmtest_job_table` VALUES (255158,0,0,'group2',1,8,0,NULL,0,'hfco_r',1387,NULL,200561,1,0,0,1837,10038,-1,'c2715',1,'54','batch',22657,3,2880,1373042184,1373042184,1373042192,1373042687,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255163,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200562,1,0,0,31996,4001,-1,'c2919',1,'80','group1',100,4,1440,1373042189,1373042189,1373063166,1373063197,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (258104,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200562,1,0,0,31996,4001,-1,'c2909',1,'75','group1',444,4,1440,1373063197,1373063278,1373084032,1373100737,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (271714,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200562,1,0,0,31996,4001,-1,'c2603',1,'36','group1',443,4,1440,1373100737,1373100753,1373110269,1373143109,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (276586,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200562,1,0,0,31996,4001,-1,'c2519',1,'32','group1',254,4,1440,1373143109,1373143151,1373143235,1373152647,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (278347,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200562,1,0,0,31996,4001,-1,'c2305',1,'1','group1',800,3,1440,1373152647,1373152663,1373152708,1373176300,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255164,0,0,'group2',1,8,0,NULL,0,'irco_r',1387,NULL,200563,1,0,0,1837,10038,-1,'c2625',1,'47','batch',22657,3,2880,1373042200,1373042200,1373042252,1373043195,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255165,0,0,'group2',1,8,0,NULL,0,'taco_r',1387,NULL,200564,1,0,0,1837,10038,-1,'c2519',1,'32','batch',22657,3,2880,1373042210,1373042210,1373042282,1373042906,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255166,0,0,'group2',1,8,0,NULL,0,'wco_r',1387,NULL,200565,1,0,0,1837,10038,-1,'c2625',1,'47','batch',22657,3,2880,1373042218,1373042218,1373042312,1373042944,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255173,0,0,'group2',1,8,0,NULL,0,'reco_r',1387,NULL,200566,1,0,0,1837,10038,-1,'c2607',1,'38','batch',22657,3,2880,1373042227,1373042227,1373042342,1373043904,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255174,0,0,'group2',1,8,0,NULL,0,'osco_r',1387,NULL,200567,1,0,0,1837,10038,-1,'c2615',1,'42','batch',22657,3,2880,1373042240,1373042240,1373042372,1373043109,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255185,0,0,'group2',1,8,0,NULL,0,'ptco_r',1387,NULL,200568,1,0,0,1837,10038,1837,'c2911',1,'76','batch',22657,4,2880,1373042249,1373042249,1373042402,1373043815,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255186,0,0,'group3',1,32,0,NULL,0,'VASP',2724,NULL,200569,1,0,0,3564,11135,-1,'c3015',1,'90','batch',20000,3,4320,1373042251,1373042251,1373045149,1373204999,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255196,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200570,1,0,0,31996,4001,-1,'c2419',1,'20','group1',100,3,1440,1373042296,1373042296,1373065118,1373137321,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255197,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200571,1,0,0,31996,4001,-1,'c2909',1,'75','group1',100,4,1440,1373042297,1373042297,1373065118,1373100737,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (271715,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200571,1,0,0,31996,4001,-1,'c2603',1,'36','group1',472,4,1440,1373100737,1373100749,1373110269,1373143109,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (276587,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200571,1,0,0,31996,4001,-1,'c2607',1,'38','group1',254,3,1440,1373143109,1373143151,1373143236,1373167537,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255198,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200572,1,0,0,31996,4001,-1,'c2917',1,'79','group1',100,4,1440,1373042300,1373042300,1373065118,1373102924,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (271785,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200572,1,0,0,31996,4001,-1,'c2615',1,'42','group1',472,3,1440,1373102924,1373102937,1373102954,1373143731,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255199,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200573,1,0,0,31996,4001,-1,'c2903',1,'72','group1',100,3,1440,1373042301,1373042301,1373065118,1373144022,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255200,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200574,1,0,0,31996,4001,-1,'c2903',1,'72','group1',100,3,1440,1373042302,1373042302,1373065118,1373143967,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255201,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200575,1,0,0,31996,4001,-1,'c2903',1,'72','group1',100,3,1440,1373042304,1373042304,1373065118,1373141686,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255202,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200576,1,0,0,31996,4001,-1,'c2911',1,'76','group1',100,3,1440,1373042306,1373042306,1373065118,1373136082,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255231,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200577,1,0,0,31996,4001,-1,'c2915',1,'78','group1',100,4,1440,1373042487,1373042487,1373065118,1373065843,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (258933,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200577,1,0,0,31996,4001,-1,'c2305',1,'1','group1',469,4,1440,1373065843,1373065856,1373065897,1373143047,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (276571,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200577,1,0,0,31996,4001,-1,'c3109',1,'99','group1',469,3,1440,1373143047,1373143079,1373153225,1373234809,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255232,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200578,1,0,0,31996,4001,-1,'c2905',1,'73','group1',100,3,1440,1373042488,1373042488,1373065119,1373136357,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255233,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200579,1,0,0,31996,4001,-1,'c2609',1,'39','group1',100,3,1440,1373042489,1373042489,1373065120,1373137059,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (255236,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200580,1,0,0,31996,4001,-1,'c2809',1,'63','group1',100,4,1440,1373042493,1373042493,1373065120,1373085072,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (265852,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200580,1,0,0,31996,4001,-1,'c3025',1,'95','group1',469,4,1440,1373085072,1373085140,1373087785,1373100767,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (271719,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200580,1,0,0,31996,4001,-1,'c2603',1,'36','group1',141,4,1440,1373100767,1373100780,1373110269,1373143109,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (276588,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200580,1,0,0,31996,4001,-1,'c2613',1,'41','group1',254,4,1440,1373143109,1373143152,1373143237,1373151518,0,'','','','',0);
INSERT INTO `slurmtest_job_table` VALUES (278150,0,0,'group1',1,1,0,NULL,0,'scheduler_pbs_job_script',1363,NULL,200580,1,0,0,31996,4001,-1,'c2819',1,'68','group1',800,3,1440,1373151518,1373151531,1373158782,1373177239,0,'','','','',0);
/*!40000 ALTER TABLE `slurmtest_job_table` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `slurmtest_step_table`
--

DROP TABLE IF EXISTS `slurmtest_step_table`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `slurmtest_step_table` (
  `job_db_inx` int(11) NOT NULL,
  `deleted` tinyint(4) NOT NULL DEFAULT '0',
  `cpus_alloc` int(10) unsigned NOT NULL,
  `exit_code` int(11) NOT NULL DEFAULT '0',
  `id_step` int(11) NOT NULL,
  `kill_requid` int(11) NOT NULL DEFAULT '-1',
  `nodelist` text NOT NULL,
  `nodes_alloc` int(10) unsigned NOT NULL,
  `node_inx` text,
  `state` smallint(5) unsigned NOT NULL,
  `step_name` text NOT NULL,
  `task_cnt` int(10) unsigned NOT NULL,
  `task_dist` smallint(6) NOT NULL DEFAULT '0',
  `time_start` int(10) unsigned NOT NULL DEFAULT '0',
  `time_end` int(10) unsigned NOT NULL DEFAULT '0',
  `time_suspended` int(10) unsigned NOT NULL DEFAULT '0',
  `user_sec` int(10) unsigned NOT NULL DEFAULT '0',
  `user_usec` int(10) unsigned NOT NULL DEFAULT '0',
  `sys_sec` int(10) unsigned NOT NULL DEFAULT '0',
  `sys_usec` int(10) unsigned NOT NULL DEFAULT '0',
  `max_pages` int(10) unsigned NOT NULL DEFAULT '0',
  `max_pages_task` int(10) unsigned NOT NULL DEFAULT '0',
  `max_pages_node` int(10) unsigned NOT NULL DEFAULT '0',
  `ave_pages` double unsigned NOT NULL DEFAULT '0',
  `max_rss` bigint(20) unsigned NOT NULL DEFAULT '0',
  `max_rss_task` int(10) unsigned NOT NULL DEFAULT '0',
  `max_rss_node` int(10) unsigned NOT NULL DEFAULT '0',
  `ave_rss` double unsigned NOT NULL DEFAULT '0',
  `max_vsize` bigint(20) unsigned NOT NULL DEFAULT '0',
  `max_vsize_task` int(10) unsigned NOT NULL DEFAULT '0',
  `max_vsize_node` int(10) unsigned NOT NULL DEFAULT '0',
  `ave_vsize` double unsigned NOT NULL DEFAULT '0',
  `min_cpu` int(10) unsigned NOT NULL DEFAULT '0',
  `min_cpu_task` int(10) unsigned NOT NULL DEFAULT '0',
  `min_cpu_node` int(10) unsigned NOT NULL DEFAULT '0',
  `ave_cpu` double unsigned NOT NULL DEFAULT '0',
  `act_cpufreq` double unsigned NOT NULL DEFAULT '0',
  `consumed_energy` double unsigned NOT NULL DEFAULT '0',
  `max_disk_read` double unsigned NOT NULL DEFAULT '0',
  `max_disk_read_task` int(10) unsigned NOT NULL DEFAULT '0',
  `max_disk_read_node` int(10) unsigned NOT NULL DEFAULT '0',
  `ave_disk_read` double unsigned NOT NULL DEFAULT '0',
  `max_disk_write` double unsigned NOT NULL DEFAULT '0',
  `max_disk_write_task` int(10) unsigned NOT NULL DEFAULT '0',
  `max_disk_write_node` int(10) unsigned NOT NULL DEFAULT '0',
  `ave_disk_write` double unsigned NOT NULL DEFAULT '0'
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `slurmtest_step_table`
--

LOCK TABLES `slurmtest_step_table` WRITE;
/*!40000 ALTER TABLE `slurmtest_step_table` DISABLE KEYS */;
INSERT INTO `slurmtest_step_table` VALUES (255158,0,1,0,-2,-1,'c2715',1,'54',3,'batch',1,0,1373042192,1373042687,0,3919,445153,6,324038,40,0,0,40,455312,0,0,451972,2803056,0,0,2799208,0,0,0,0,2100000,0,82.096447,0,0,82.096447,3.416608,0,0,3.416608);
INSERT INTO `slurmtest_step_table` VALUES (255164,0,1,0,-2,-1,'c2625',1,'47',3,'batch',1,0,1373042252,1373043195,0,7464,356245,8,196753,50,0,0,50,467636,0,0,462604,2813252,0,0,2807652,0,0,0,0,2100000,0,96.059849,0,0,96.059849,3.417789,0,0,3.417789);
INSERT INTO `slurmtest_step_table` VALUES (255165,0,1,0,-2,-1,'c2519',1,'32',3,'batch',1,0,1373042282,1373042906,0,4921,929752,7,602844,41,0,0,41,456428,0,0,456088,2803764,0,0,2803764,0,0,0,0,2100000,0,86.796613,0,0,86.796613,3.244969,0,0,3.244969);
INSERT INTO `slurmtest_step_table` VALUES (255166,0,1,0,-2,-1,'c2625',1,'47',3,'batch',1,0,1373042312,1373042944,0,4963,314461,7,759820,48,0,0,48,448216,0,0,445388,2796124,0,0,2792532,0,0,0,0,2100000,0,89.12845,0,0,89.12845,79.219021,0,0,79.219021);
INSERT INTO `slurmtest_step_table` VALUES (255173,0,1,0,-2,-1,'c2607',1,'38',3,'batch',1,0,1373042342,1373043904,0,12385,393134,9,801509,45,0,0,45,453372,0,0,446588,2799876,0,0,2792636,0,0,0,0,2100000,0,91.467368,0,0,91.467368,77.834174,0,0,77.834174);
INSERT INTO `slurmtest_step_table` VALUES (255174,0,1,0,-2,-1,'c2615',1,'42',3,'batch',1,0,1373042372,1373043109,0,5819,43370,6,445020,48,0,0,48,450744,0,0,447216,2798460,0,0,2794380,0,0,0,0,2100000,0,93.815774,0,0,93.815774,2.960266,0,0,2.960266);
INSERT INTO `slurmtest_step_table` VALUES (255185,0,1,15,-2,-1,'c2911',1,'76',4,'batch',1,0,1373042402,1373043816,0,0,61990,0,27995,45,0,0,45,484488,0,0,484488,2835000,0,0,2835000,0,0,0,0,2100000,0,100.831144,0,0,100.831144,0.352856,0,0,0.352856);
INSERT INTO `slurmtest_step_table` VALUES (255186,0,1,0,-2,-1,'c3015',1,'90',3,'batch',1,0,1373045149,1373204999,0,4986296,633690,116145,699169,1287,0,0,204,18778084,0,0,3686164,25858180,0,0,5296572,0,0,0,0,2100000,0,44.234023,0,0,10.411278,9.827832,0,0,2.05897);
INSERT INTO `slurmtest_step_table` VALUES (255196,0,1,0,-2,-1,'c2419',1,'20',3,'batch',1,0,1373065118,1373137321,0,70600,395108,444,431436,0,0,0,0,300668,0,0,25488,768040,0,0,210448,0,0,0,0,2100000,0,4546.737899,0,0,4546.737899,1118.452336,0,0,1118.452336);
INSERT INTO `slurmtest_step_table` VALUES (255199,0,1,0,-2,-1,'c2903',1,'72',3,'batch',1,0,1373065118,1373144022,0,76007,235143,493,859921,0,0,0,0,280972,0,0,26828,759272,0,0,211912,0,0,0,0,2100000,0,7136.614912,0,0,7136.614912,1009.579643,0,0,1009.579643);
INSERT INTO `slurmtest_step_table` VALUES (255200,0,1,0,-2,-1,'c2903',1,'72',3,'batch',1,0,1373065118,1373143967,0,75895,852076,491,219323,0,0,0,0,281772,0,0,6152,759336,0,0,103584,0,0,0,0,1400000,0,7125.042548,0,0,1489.304774,1008.428627,0,0,1001.976442);
INSERT INTO `slurmtest_step_table` VALUES (255201,0,1,0,-2,-1,'c2903',1,'72',3,'batch',1,0,1373065118,1373141686,0,73547,867024,487,277922,0,0,0,0,286220,0,0,6776,864600,0,0,99952,0,0,0,0,2100000,0,6912.700717,0,0,1496.022424,1015.892091,0,0,1009.663585);
INSERT INTO `slurmtest_step_table` VALUES (255202,0,1,0,-2,-1,'c2911',1,'76',3,'batch',1,0,1373065118,1373136082,0,68912,713675,469,527620,0,0,0,0,281916,0,0,26856,762388,0,0,212152,0,0,0,0,2100000,0,5872.73068,0,0,5872.73068,1008.086425,0,0,1008.086425);
INSERT INTO `slurmtest_step_table` VALUES (255232,0,1,0,-2,-1,'c2905',1,'73',3,'batch',1,0,1373065119,1373136357,0,69066,313324,493,56044,17,0,0,0,276272,0,0,4808,757876,0,0,68212,0,0,0,0,2100000,0,4541.237699,0,0,47.809687,745.121394,0,0,27.28334);
INSERT INTO `slurmtest_step_table` VALUES (255233,0,1,0,-2,-1,'c2609',1,'39',3,'batch',1,0,1373065120,1373137059,0,70446,19577,510,362413,0,0,0,0,282832,0,0,23792,756456,0,0,209560,0,0,0,0,2100000,0,2862.853929,0,0,1741.094645,751.146852,0,0,31.19075);
INSERT INTO `slurmtest_step_table` VALUES (258104,0,1,9,-2,-1,'c2919',1,'80',4,'batch',1,0,1373063166,1373063259,0,0,5999,0,10998,0,0,0,0,1936,0,0,1936,221888,0,0,44440,0,0,0,0,1400000,0,0.037008,0,0,0.037008,5.2e-05,0,0,5.2e-05);
INSERT INTO `slurmtest_step_table` VALUES (258933,0,1,15,-2,-1,'c2915',1,'78',4,'batch',1,0,1373065118,1373065845,0,0,6998,0,2999,0,0,0,0,253936,0,0,253936,735888,0,0,735888,0,0,0,0,2100000,0,218.750704,0,0,218.750704,254.179801,0,0,254.179801);
INSERT INTO `slurmtest_step_table` VALUES (265852,0,1,15,-2,-1,'c2809',1,'63',4,'batch',1,0,1373065120,1373085130,0,0,2999,0,9998,0,0,0,0,269980,0,0,107032,752948,0,0,581624,0,0,0,0,2100000,0,2170.735701,0,0,2170.735701,379.682835,0,0,379.682835);
INSERT INTO `slurmtest_step_table` VALUES (271714,0,1,15,-2,-1,'c2909',1,'75',4,'batch',1,0,1373084032,1373100742,0,0,5999,0,10998,0,0,0,0,277208,0,0,265920,748584,0,0,748584,0,0,0,0,2100000,0,1176.233036,0,0,1176.233036,349.515496,0,0,349.515496);
INSERT INTO `slurmtest_step_table` VALUES (271715,0,1,15,-2,-1,'c2909',1,'75',4,'batch',1,0,1373065118,1373100739,0,0,4999,0,7998,18,0,0,1,289828,0,0,271032,757396,0,0,755076,0,0,0,0,2100000,0,2669.930323,0,0,2669.930323,512.294904,0,0,512.294904);
INSERT INTO `slurmtest_step_table` VALUES (271719,0,1,15,-2,-1,'c3025',1,'95',4,'batch',1,0,1373087785,1373100769,0,0,5999,0,5999,0,0,0,0,1772068,0,0,1772068,2762036,0,0,2762032,0,0,0,0,2100000,0,1142.716335,0,0,1142.716335,487.287826,0,0,487.287826);
INSERT INTO `slurmtest_step_table` VALUES (271785,0,1,0,-2,-1,'c2615',1,'42',3,'batch',1,0,1373065118,1373143731,0,40131,528080,5,288196,0,0,0,0,1897220,0,0,26152,2763844,0,0,211492,0,0,0,0,2100000,0,4406.478991,0,0,4406.478991,505.609762,0,0,505.609762);
INSERT INTO `slurmtest_step_table` VALUES (276571,0,1,0,-2,-1,'c3109',1,'99',3,'batch',1,0,1373065897,1373234809,0,79894,627170,451,747323,0,0,0,0,305244,0,0,25496,792164,0,0,210488,0,0,0,0,2100000,0,4717.038625,0,0,4717.038625,1226.168622,0,0,1226.168622);
INSERT INTO `slurmtest_step_table` VALUES (276586,0,1,15,-2,-1,'c2603',1,'36',4,'batch',1,0,1373110269,1373143134,0,0,5999,0,8998,0,0,0,0,232356,0,0,220844,711008,0,0,698144,0,0,0,0,2100000,0,3619.745543,0,0,3619.745543,474.102014,0,0,474.102014);
INSERT INTO `slurmtest_step_table` VALUES (276587,0,1,0,-2,-1,'c2607',1,'38',3,'batch',1,0,1373110269,1373167537,0,23759,412020,4,500315,0,0,0,0,1860540,0,0,26884,2763908,0,0,211928,0,0,0,0,2100000,0,2108.69206,0,0,2108.69206,488.771967,0,0,488.771967);
INSERT INTO `slurmtest_step_table` VALUES (276588,0,1,15,-2,-1,'c2603',1,'36',4,'batch',1,0,1373110269,1373143133,0,0,5999,0,9998,0,0,0,0,234192,0,0,105568,713056,0,0,582224,0,0,0,0,2100000,0,3651.427007,0,0,3651.427007,488.541189,0,0,488.541189);
INSERT INTO `slurmtest_step_table` VALUES (278150,0,1,0,-2,-1,'c2819',1,'68',3,'batch',1,0,1373143237,1373177239,0,18155,653921,5,42233,0,0,0,0,1832944,0,0,27988,2764924,0,0,212936,0,0,0,0,2100000,0,3265.993665,0,0,3265.993665,488.19168,0,0,488.19168);
INSERT INTO `slurmtest_step_table` VALUES (278347,0,1,0,-2,-1,'c2305',1,'1',3,'batch',1,0,1373143235,1373176300,0,23138,416426,5,53231,0,0,0,0,1836996,0,0,25864,2762808,0,0,210824,0,0,0,0,1400000,0,1739.920688,0,0,1739.920688,488.628329,0,0,488.628329);
/*!40000 ALTER TABLE `slurmtest_step_table` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2013-07-17 10:47:54
