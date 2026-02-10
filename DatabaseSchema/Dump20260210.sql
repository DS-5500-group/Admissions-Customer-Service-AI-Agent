CREATE DATABASE  IF NOT EXISTS `capstonedb` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `capstonedb`;
-- MySQL dump 10.13  Distrib 8.0.41, for Win64 (x86_64)
--
-- Host: localhost    Database: capstonedb
-- ------------------------------------------------------
-- Server version	9.2.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `answerconfidence`
--

DROP TABLE IF EXISTS `answerconfidence`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `answerconfidence` (
  `Question` varchar(255) DEFAULT NULL,
  `Answer` varchar(1028) DEFAULT NULL,
  `confidenceLevel` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `answerconfidence`
--

LOCK TABLES `answerconfidence` WRITE;
/*!40000 ALTER TABLE `answerconfidence` DISABLE KEYS */;
INSERT INTO `answerconfidence` VALUES ('What GPA does Northeastern require for admissions?','Middle 50% GPA range of admitted students: 4.2â€“4.5.',95),('How much is tuition at Northeastern?','Undergraduate tuition is approximately $67,990 per year.',90),('What is the housing cost at Northeastern?','On-campus housing costs about $13,148 per year.',88),('What are the Early Decision/Action dates?','Early Decision/Action: Nov 1, Regular Decision: Jan 1.',92),('Is the SAT required at Northeastern?','Test-optional; SAT/ACT accepted but not required.',90);
/*!40000 ALTER TABLE `answerconfidence` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `informationdatabase`
--

DROP TABLE IF EXISTS `informationdatabase`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `informationdatabase` (
  `id` int NOT NULL AUTO_INCREMENT,
  `Category` varchar(255) DEFAULT NULL,
  `Sub_Category` varchar(255) DEFAULT NULL,
  `Information_Text` text,
  `Source_Name` varchar(1028) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `informationdatabase`
--

LOCK TABLES `informationdatabase` WRITE;
/*!40000 ALTER TABLE `informationdatabase` DISABLE KEYS */;
INSERT INTO `informationdatabase` VALUES (1,'Ranking','Overall','Ranked among top national universities in multiple rankings.','https://www.northeastern.edu/about/fast-facts/'),(2,'Ranking','CS','Northeastern\'s CS program is highly ranked nationally.','https://www.northeastern.edu/academics/programs/computer-science/'),(3,'Financial','Tuition','Undergraduate tuition is approximately $67,990 per year.','https://www.northeastern.edu/tuition/undergraduate/'),(4,'Financial','Housing','On-campus housing costs about $13,148 per year.','https://www.northeastern.edu/housing/residential-life/'),(5,'Location Information','Boston','Main campus located in Fenway Cultural District, Boston, MA.','https://www.northeastern.edu/about/'),(6,'Career Outcomes','Employment','93% of undergraduates employed or in graduate school within 6 months.','https://www.northeastern.edu/careers/outcomes/'),(7,'Application Questions','Dates','Early Decision/Action: Nov 1, Regular Decision: Jan 1.','https://www.northeastern.edu/admissions/undergraduate/'),(8,'Application Questions','Fees','Application fee is $75.','https://www.northeastern.edu/admissions/undergraduate/'),(9,'Admission Requirements Domestic','GPA','Middle 50% GPA range of admitted students: 4.2â€“4.5.','https://www.northeastern.edu/admissions/undergraduate/'),(10,'Admission Requirements Domestic','SAT/ACT','Test-optional; SAT/ACT accepted but not required.','https://www.northeastern.edu/admissions/undergraduate/'),(11,'Admission Requirements International','GPA','Similar GPA expectations to domestic students, varies by program.','https://www.northeastern.edu/admissions/international/'),(12,'Admission Requirements International','SAT/ACT','Testing optional; English proficiency required.','https://www.northeastern.edu/admissions/international/'),(13,'Contact and External Resources','Admissions','Contact email: [emailÂ protected], Phone: 617-373-2200.','https://www.northeastern.edu/admissions/undergraduate/'),(14,'Contact and External Resources','Student Services','Counseling, disability support, student engagement programs available.','https://www.northeastern.edu/student-services/'),(15,'Other/Unanswerable','General Overview','Private research university in Boston; famous for co-op and experiential learning.','https://www.northeastern.edu/about/');
/*!40000 ALTER TABLE `informationdatabase` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `interactionhistory`
--

DROP TABLE IF EXISTS `interactionhistory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `interactionhistory` (
  `userID` text,
  `Question` varchar(255) DEFAULT NULL,
  `Answer` varchar(1028) DEFAULT NULL,
  `Time_Stamp` time DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `interactionhistory`
--

LOCK TABLES `interactionhistory` WRITE;
/*!40000 ALTER TABLE `interactionhistory` DISABLE KEYS */;
/*!40000 ALTER TABLE `interactionhistory` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-02-10 17:02:53
