

CREATE DATABASE CapstoneDB;

Use CapstoneDB;

#This Table will hold information for the University
Create Table InformationDatabase(
id INT AUTO_INCREMENT PRIMARY KEY,
Category Varchar(255),
Sub_Category Varchar(255),
Information_Text Text,
Source_Name Varchar(1028)
);

#This table will hold the User Question, Agent Answer, and Agent confidence on answer.
Create Table AnswerConfidence(
Question Varchar(255),
Answer Varchar(1028),
confidenceLevel INT
);

#Interaction History
Create Table InteractionHistory(
userID Text,
Question Varchar(255),
Answer Varchar(1028),
Time_Stamp Time
);

#Import Data from the CSV using SQL Data Import Wizard in SQL WorkBench





