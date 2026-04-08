// ─── State management (independent of Group/Subgroup classification) ───

enum Overall_U {
    Out_Of_Scope
    In_Scope_Question
    //User_Requests_Repeat  // handle later
    //User_Clarification    // handle later
    //User_Respond_Clarification
    End_Call
}


// ─── Subgroup enums (one per group, enforces valid pairs at the type level) ───

enum DiningFoodSubgroup {
    Dining_Halls
    Retail_Dining
    Allergy_Info
    Plan_Options_And_Cost
    Contact_Info
}

enum HousingSubgroup {
    Housing_Cost
    Layout_Info
    Off_Campus
    Moving_Information
    Contact_Info
}

enum StudentAmenitiesActivitiesSubgroup {
    Gym
    Student_Activities_Fees
    Clubs
    Game_Rooms
    Volunteering
    Transportation
    Greek_Life
    Study_Space
    Contact_Info
}

enum SafetySubgroup {
    RedEye_Night_Shuttle
    Security_App
    Campus_Escort
    Card_Entry
    Crime_Statistics
    Contact_Info
}

enum AthleticsSubgroup {
    Varsity_Sports
    Intramural
    Signature_Events
    Contact_Info
}

enum AdmissionApplicationSubgroup {
    Decision_Types_Outcomes
    Dates_Deadlines
    Portal_Info
    Application_Materials
    Financial_Aid
    Estimated_Cost
    Tours
    Acceptance_Criteria_Stats
    Contact_Info
    AP_Credit_Lookup
    Enrollment
    Transfer_Applicants
    Orientation
    Honors_Program
}

enum RankingGeneralStatsSubgroup {
    Overall_School_Ranking
    Extracurriculars
    Majors
    Demographics
    Career_Outcomes
}

enum StudentSupportSubgroup {
    Contact_Info
    Resources_Overview
    Confidential_Resources
    National_Resources
    Policies
}

enum ExperientialLearningSubgroup {
    Coop_Process
    Coop_Salary
    Coop_Overview
    Research
    NU_View
    Experiential_Projects
}


// ─── One class per group (field name = lookup key prefix) ───

class DiningFoodQuestion {
    Dining_food DiningFoodSubgroup
}

class HousingQuestion {
    Housing HousingSubgroup
}

class StudentAmenitiesActivitiesQuestion {
    Student_Amenities_Activities StudentAmenitiesActivitiesSubgroup
}

class SafetyQuestion {
    Safety SafetySubgroup
}

class AthleticsQuestion {
    Athletics AthleticsSubgroup
}

class AdmissionApplicationQuestion {
    Admission_Application AdmissionApplicationSubgroup
}

class RankingGeneralStatsQuestion {
    Ranking_GeneralStats RankingGeneralStatsSubgroup
}

class StudentSupportQuestion {
    Student_Support StudentSupportSubgroup
}

class ExperientialLearningQuestion {
    Experiential_Learning ExperientialLearningSubgroup
}

class NoMatchingGroupQuestion {
    No_Matching_Group "NoSubgroup"
}

class NotApplicableQuestion {
    NotApplicable "NotApplicable"
}


// ─── Output class ───

class ClassifiedInput_U {
    overall_classification Overall_U
    category DiningFoodQuestion | HousingQuestion | StudentAmenitiesActivitiesQuestion | SafetyQuestion | AthleticsQuestion | AdmissionApplicationQuestion | RankingGeneralStatsQuestion | StudentSupportQuestion | ExperientialLearningQuestion | NoMatchingGroupQuestion | NotApplicableQuestion
    confidence float? @description(#"
        Range is 0.0 to 1.0 based on the confidence of classifying an In-Scope question into Group and Subgroup.
        0.0 Confidence if Group is 'No_Matching_Group'.
    "#)
    clarification string? @description(#"
        Only populated when group is No_Matching_Group or confidence is less or equal to 0.5.
        Field should be a follow up question that would raise confidence. An example is to narrow down
        possible the group and subgroup the user is potentially asking about.
    "#)
}


// ─── Functions ───

function ClassifyInput_Union(current_input: string, transcript: string) -> ClassifiedInput_U {
    client CustomGPT
    prompt #"
        You are a classification component in a voice agent for prospective Northeastern University students.

        ## Task 1: Overall Classification
        Classify the user's input into one of these categories:

        - Out_Of_Scope: Questions not related to Northeastern University admissions or student life
        - In_Scope_Question: A question about Northeastern that can be answered
        - End_Call: The user is ending the conversation (e.g., "goodbye", "thanks, that's all", "I'm done")

        ## Task 2: Group/Subgroup Classification
        If In_Scope_Question: classify into exactly one Group and one Subgroup.
        If Out_Of_Scope or End_Call: use NotApplicable.
        If in-scope but no group fits: use No_Matching_Group.

        ## Confidence and Clarification Rules
        - confidence: 0.0 to 1.0 indicating certainty of Group/Subgroup classification
        - Set confidence to 0.0 if No_Matching_Group
        - clarification: Only populate if confidence <= 0.5 OR No_Matching_Group
          - This should be a follow-up question to narrow down the user's intent

        ## Input

        Conversation History: {{transcript}}
        Current User Input: {{current_input}}

        {{ ctx.output_format }}
    "#
}

function LanguageDetection_Union(response: string) -> string {
    client CustomGPT
    prompt #"
        Extract the language name from user's response. If no language is mentioned, default to English.

        User response: {{response}}
    "#
}

function EmailRetrieval_Union(spoken: string) -> string {
    client CustomGPT
    prompt #"
        Please extract the email address from the user's spoken input.
        You must follow these steps to parse the email accuractely:
        1. Convert all number words to digits for example "two" -> "2".
        2. Everything is a string remove all whitespace between characters for example "a b 1 2" -> "ab12".
        3. Conversion of certain phrases:
            - "dot" -> "."
            - "at" -> "@"
            - "underscore" -> "_"
            - "dash" or "hyphen" -> "-"
        4. Look for domain of the email.
        The domains are:
            - "gmail dot com" -> "gmail.com"
            - "yahoo dot com" -> "yahoo.com"
        If no domain is found and username only is provided append "@gmail.com" to the end of the response.

        Example of conversion is: "tom dot brady at gmail dot com" -> "tom.brady@gmail.com"

        However, if no email can be obtained please respond with "Unable to parse email".
        The final output is the email address with no additional text and punctuation.

        Spoken email: {{spoken}}
    "#
}

function AnswerQuery_Union(question: string, context: string, transcript: string, language: string) -> string {
    client CustomGPT
    prompt #"
        You are a friendly admissions assistant for Northeastern University, speaking with a prospective student over the phone.
        ## Rules
        - Answer in 1-4 short sentences (this will be spoken aloud)
        - Use only information from the "University Info Context" below
        - Never use bullet points, numbered lists, "*" characters, or URLs
        - Avoid abbreviations; spell out words fully
        - Respond in {{language}}

        Call Transcript: {{transcript}}
        Current User question: {{question}}

        University info context: {{context}}
    "#
}


test Test2Parse {
    functions [ClassifyInput_Union]
    args {
        current_input #"
          What GPA does Northeastern require for admissions?
        "#
        transcript #"
            Agent: What can I help you with today?
        "#
    }
}
