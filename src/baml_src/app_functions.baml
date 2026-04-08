enum Overall{
    Out_Of_Scope
    In_Scope_Question
    //User_Requests_Repeat  // handle later
    // User_Clarification   // handle later
    //User_Respond_Clarification
    Transfer_To_Human
    End_Call
}


// ─── Group enum ───
enum Group {
    CoOp
    Dining_food
    Housing
    Student_Amenities_Activities
    Safety
    Athletics
    Admission_Application
    Ranking_GeneralStats
    Student_Support
    Experiential_Learning

    No_Matching_Group

    // For Out Of Scope General Classification
    NotApplicable
}

// ─── Subgroup enum (flat; Group field disambiguates shared values like Contact_Info) ───
enum Subgroup {
    // CoOp
    CoOp_Process
    CoOp_Salary
    CoOp_Overview

    // Dining_food
    Dining_Halls
    Retail_Dining
    Allergy_Info
    Plan_Options_And_Cost

    // Housing
    Housing_Cost
    Layout_Info
    Off_Campus
    Moving_Information

    // Student_Amenities_Activities
    Gym
    Student_Activities_Fees
    Clubs
    Game_Rooms
    Volunteering
    Transportation
    Greek_Life
    Study_Space

    // Safety
    RedEye_Night_Shuttle
    Security_App
    Campus_Escort
    Card_Entry
    Crime_Statistics

    // Athletics
    Varsity_Sports
    Intramural
    Signature_Events

    // Admission_Application
    Decision_Types_Outcomes
    Dates_Deadlines
    Portal_Info
    Application_Materials
    Financial_Aid
    Estimated_Cost
    Tours
    Acceptance_Criteria_Stats
    AP_Credit_Lookup
    Enrollment
    Transfer_Applicants
    Orientation
    Honors_Program
    

    // Ranking_GeneralStats
    Overall_School_Ranking
    Extracurriculars
    Majors
    Demographics
    Career_Outcomes

    // Student_Support
    Resources_Overview
    Confidential_Resources
    National_Resources
    Policies

    //Experiential Learning
    Coop_Process
    Coop_Salary
    Coop_Overview
    Research
    NU_View
    Experiential_Projects

    // Shared across multiple groups
    Contact_Info

    // For UnAnswerable group
    NoSubgroup
    // For Out Of Scope General Classification
    NotApplicable

}

// ─── Output class ───
class ClassifiedQuestion {
    group Group
    subgroup Subgroup
    confidence float? @description(#"
        Range is 0.0 to 1.0 based on the confidence of classifying the input into Group and Subgroup.
        0.0 Confidence if Group is 'UnAnswerable'. 
    "#)
    clarification string?  @description(#"
        Only populated when group is UnAnswerable or confidence is less or equal to 0.5. 
        Field should be a follow up question that would raise confidence. An example is to narrow down
        possible the group and subgroup the user is potentially asking about.  
    "#)
}

class ClassifiedInput {
    overall_classification Overall
    group Group
    subgroup Subgroup
    confidence float? @description(#"
        Range is 0.0 to 1.0 based on the confidence of classifying an In-Scope question into Group and Subgroup.
        0.0 Confidence if Group is 'No_Matching_Group'. 
    "#)
    clarification string?  @description(#"
        Only populated when group is No_Matching_Group or confidence is less or equal to 0.5. 
        Field should be a follow up question that would raise confidence. An example is to narrow down
        possible the group and subgroup the user is potentially asking about.  
    "#)
}



function ClassifyInput(current_input: string, transcript: string) -> ClassifiedInput{
    client CustomGPT
    prompt #"
        You are a classification component in a voice agent for prospective Northeastern University students.

        ## Task 1: Overall Classification
        Classify the user's input into one of these categories:

        - Out_Of_Scope: Questions not related to Northeastern University admissions or student life
        - In_Scope_Question: A question about Northeastern that can be answered.
        - End_Call: The user is ending the conversation (e.g., "goodbye", "thanks, that's all", "I'm done")
        - Transfer_To_Human: The user is requesting to speak to a human representative or indicates frustration (e.g., "I want to talk to a person", "This isn't helpful")

        ## Task 2: Group/Subgroup Classification (only if In_Scope_Question)
        If overall_classification is In_Scope_Question, classify into exactly one Group and one Subgroup.

        Valid (Group -> Subgroup) mappings:
        - Dining_food -> Dining_Halls, Retail_Dining, Allergy_Info, Plan_Options_And_Cost, Contact_Info
        - Housing -> Housing_Cost, Layout_Info, Off_Campus, Moving_Information, Contact_Info
        - Student_Amenities_Activities -> Gym, Student_Activities_Fees, Clubs, Game_Rooms, Volunteering, Transportation, Greek_Life, Study_Space, Contact_Info
        - Safety -> RedEye_Night_Shuttle, Security_App, Campus_Escort, Card_Entry, Crime_Statistics, Contact_Info
        - Athletics -> Varsity_Sports, Intramural, Signature_Events, Contact_Info
        - Admission_Application -> Decision_Types_Outcomes, Dates_Deadlines, Portal_Info, Application_Materials, Financial_Aid, Estimated_Cost, Tours, Acceptance_Criteria_Stats, Contact_Info, AP_Credit_Lookup, Enrollment, Transfer_Applicants, Orientation, Honors_Program
        - Ranking_GeneralStats -> Overall_School_Ranking, Extracurriculars, Majors, Demographics, Career_Outcomes
        - Student_Support -> Contact_Info, Resources_Overview, Confidential_Resources, National_Resources, Policies
        - Experiential_Learning -> Coop_Process, Coop_Salary, Coop_Overview, Research, NU_View, Experiential_Projects
        - No_Matching_Group -> NoSubgroup (use when in-scope but no group fits)
        - NotApplicable -> NotApplicable (use when Out_Of_Scope, End_Call Overall, Transfer_To_Human classified )

        ## Confidence and Clarification Rules
        - confidence: 0.0 to 1.0 indicating certainty of Group/Subgroup classification
        - Set confidence to 0.0 if Group is No_Matching_Group
        - clarification: Only populate if confidence <= 0.5 OR Group is No_Matching_Group
          - This should be a follow-up question to narrow down the user's intent

        ## Input
        
        Conversation History: {{transcript}}
        Current User Input: {{current_input}}

        {{ ctx.output_format }}
    "#
}
function LanguageDetection(response: string) -> string {
    client CustomGPT
    prompt #"
        Extract the language name from user's response. If no language is mentioned, default to English.

        User response: {{response}}
    "#
}

function EmailRetrieval(spoken: string) -> string {
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


function AnswerQuery(question: string, context: string, transcript: string, language: string) -> string {
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

function ClassifyInput_GPT4oMini(current_input: string, transcript: string) -> ClassifiedInput{
    client CustomGPT
    prompt #"
        You are a classification component in a voice agent for prospective Northeastern University students.

        ## Task 1: Overall Classification
        Classify the user's input into one of these categories:

        - Out_Of_Scope: Questions not related to Northeastern University admissions or student life
        - In_Scope_Question: A question about Northeastern that can be answered.
        - End_Call: The user is ending the conversation (e.g., "goodbye", "thanks, that's all", "I'm done")

        ## Task 2: Group/Subgroup Classification (only if In_Scope_Question)
        If overall_classification is In_Scope_Question, classify into exactly one Group and one Subgroup.

        Valid (Group -> Subgroup) mappings:
        - Dining_food -> Dining_Halls, Retail_Dining, Allergy_Info, Plan_Options_And_Cost, Contact_Info
        - Housing -> Housing_Cost, Layout_Info, Off_Campus, Moving_Information, Contact_Info
        - Student_Amenities_Activities -> Gym, Student_Activities_Fees, Clubs, Game_Rooms, Volunteering, Transportation, Greek_Life, Study_Space, Contact_Info
        - Safety -> RedEye_Night_Shuttle, Security_App, Campus_Escort, Card_Entry, Crime_Statistics, Contact_Info
        - Athletics -> Varsity_Sports, Intramural, Signature_Events, Contact_Info
        - Admission_Application -> Decision_Types_Outcomes, Dates_Deadlines, Portal_Info, Application_Materials, Financial_Aid, Estimated_Cost, Tours, Acceptance_Criteria_Stats, Contact_Info, AP_Credit_Lookup, Enrollment, Transfer_Applicants, Orientation, Honors_Program
        - Ranking_GeneralStats -> Overall_School_Ranking, Extracurriculars, Majors, Demographics, Career_Outcomes
        - Student_Support -> Contact_Info, Resources_Overview, Confidential_Resources, National_Resources, Policies
        - Experiential_Learning -> Coop_Process, Coop_Salary, Coop_Overview, Research, NU_View, Experiential_Projects
        - No_Matching_Group -> NoSubgroup (use when in-scope but no group fits)
        - NotApplicable -> NotApplicable (use when Out_Of_Scope or End_Call Overall classified )   

        ## Confidence and Clarification Rules
        - confidence: 0.0 to 1.0 indicating certainty of Group/Subgroup classification
        - Set confidence to 0.0 if Group is No_Matching_Group
        - clarification: Only populate if confidence <= 0.5 OR Group is No_Matching_Group
          - This should be a follow-up question to narrow down the user's intent

        ## Input
        
        Conversation History: {{transcript}}
        Current User Input: {{current_input}}

        {{ ctx.output_format }}
    "#
}

function ClassifyInput_Haiku(current_input: string, transcript: string) -> ClassifiedInput{
    client OpenRouterClaudeHaiku
    prompt #"
        You are a classification component in a voice agent for prospective Northeastern University students.

        ## Task 1: Overall Classification
        Classify the user's input into one of these categories:

        - Out_Of_Scope: Questions not related to Northeastern University admissions or student life
        - In_Scope_Question: A question about Northeastern that can be answered.
        - End_Call: The user is ending the conversation (e.g., "goodbye", "thanks, that's all", "I'm done")

        ## Task 2: Group/Subgroup Classification (only if In_Scope_Question)
        If overall_classification is In_Scope_Question, classify into exactly one Group and one Subgroup.

        Valid (Group -> Subgroup) mappings:
        - Dining_food -> Dining_Halls, Retail_Dining, Allergy_Info, Plan_Options_And_Cost, Contact_Info
        - Housing -> Housing_Cost, Layout_Info, Off_Campus, Moving_Information, Contact_Info
        - Student_Amenities_Activities -> Gym, Student_Activities_Fees, Clubs, Game_Rooms, Volunteering, Transportation, Greek_Life, Study_Space, Contact_Info
        - Safety -> RedEye_Night_Shuttle, Security_App, Campus_Escort, Card_Entry, Crime_Statistics, Contact_Info
        - Athletics -> Varsity_Sports, Intramural, Signature_Events, Contact_Info
        - Admission_Application -> Decision_Types_Outcomes, Dates_Deadlines, Portal_Info, Application_Materials, Financial_Aid, Estimated_Cost, Tours, Acceptance_Criteria_Stats, Contact_Info, AP_Credit_Lookup, Enrollment, Transfer_Applicants, Orientation, Honors_Program
        - Ranking_GeneralStats -> Overall_School_Ranking, Extracurriculars, Majors, Demographics, Career_Outcomes
        - Student_Support -> Contact_Info, Resources_Overview, Confidential_Resources, National_Resources, Policies
        - Experiential_Learning -> Coop_Process, Coop_Salary, Coop_Overview, Research, NU_View, Experiential_Projects
        - No_Matching_Group -> NoSubgroup (use when in-scope but no group fits)
        - NotApplicable -> NotApplicable (use when Out_Of_Scope or End_Call Overall classified )   

        ## Confidence and Clarification Rules
        - confidence: 0.0 to 1.0 indicating certainty of Group/Subgroup classification
        - Set confidence to 0.0 if Group is No_Matching_Group
        - clarification: Only populate if confidence <= 0.5 OR Group is No_Matching_Group
          - This should be a follow-up question to narrow down the user's intent

        ## Input
        
        Conversation History: {{transcript}}
        Current User Input: {{current_input}}

        {{ ctx.output_format }}
    "#
}
function ClassifyInput_GeminiFlash(current_input: string, transcript: string) -> ClassifiedInput{
    client OpenRouterGeminiFlash
    prompt #"
        You are a classification component in a voice agent for prospective Northeastern University students.

        ## Task 1: Overall Classification
        Classify the user's input into one of these categories:

        - Out_Of_Scope: Questions not related to Northeastern University admissions or student life
        - In_Scope_Question: A question about Northeastern that can be answered.
        - End_Call: The user is ending the conversation (e.g., "goodbye", "thanks, that's all", "I'm done")

        ## Task 2: Group/Subgroup Classification (only if In_Scope_Question)
        If overall_classification is In_Scope_Question, classify into exactly one Group and one Subgroup.

        Valid (Group -> Subgroup) mappings:
        - Dining_food -> Dining_Halls, Retail_Dining, Allergy_Info, Plan_Options_And_Cost, Contact_Info
        - Housing -> Housing_Cost, Layout_Info, Off_Campus, Moving_Information, Contact_Info
        - Student_Amenities_Activities -> Gym, Student_Activities_Fees, Clubs, Game_Rooms, Volunteering, Transportation, Greek_Life, Study_Space, Contact_Info
        - Safety -> RedEye_Night_Shuttle, Security_App, Campus_Escort, Card_Entry, Crime_Statistics, Contact_Info
        - Athletics -> Varsity_Sports, Intramural, Signature_Events, Contact_Info
        - Admission_Application -> Decision_Types_Outcomes, Dates_Deadlines, Portal_Info, Application_Materials, Financial_Aid, Estimated_Cost, Tours, Acceptance_Criteria_Stats, Contact_Info, AP_Credit_Lookup, Enrollment, Transfer_Applicants, Orientation, Honors_Program
        - Ranking_GeneralStats -> Overall_School_Ranking, Extracurriculars, Majors, Demographics, Career_Outcomes
        - Student_Support -> Contact_Info, Resources_Overview, Confidential_Resources, National_Resources, Policies
        - Experiential_Learning -> Coop_Process, Coop_Salary, Coop_Overview, Research, NU_View, Experiential_Projects
        - No_Matching_Group -> NoSubgroup (use when in-scope but no group fits)
        - NotApplicable -> NotApplicable (use when Out_Of_Scope or End_Call Overall classified )   

        ## Confidence and Clarification Rules
        - confidence: 0.0 to 1.0 indicating certainty of Group/Subgroup classification
        - Set confidence to 0.0 if Group is No_Matching_Group
        - clarification: Only populate if confidence <= 0.5 OR Group is No_Matching_Group
          - This should be a follow-up question to narrow down the user's intent

        ## Input
        
        Conversation History: {{transcript}}
        Current User Input: {{current_input}}

        {{ ctx.output_format }}
    "#
}

function ClassifyInput_Llama8B(current_input: string, transcript: string) -> ClassifiedInput{
    client OpenRouterLlama8B
    prompt #"
        You are a classification component in a voice agent for prospective Northeastern University students.

        ## Task 1: Overall Classification
        Classify the user's input into one of these categories:

        - Out_Of_Scope: Questions not related to Northeastern University admissions or student life
        - In_Scope_Question: A question about Northeastern that can be answered.
        - End_Call: The user is ending the conversation (e.g., "goodbye", "thanks, that's all", "I'm done")

        ## Task 2: Group/Subgroup Classification (only if In_Scope_Question)
        If overall_classification is In_Scope_Question, classify into exactly one Group and one Subgroup.

        Valid (Group -> Subgroup) mappings:
        - Dining_food -> Dining_Halls, Retail_Dining, Allergy_Info, Plan_Options_And_Cost, Contact_Info
        - Housing -> Housing_Cost, Layout_Info, Off_Campus, Moving_Information, Contact_Info
        - Student_Amenities_Activities -> Gym, Student_Activities_Fees, Clubs, Game_Rooms, Volunteering, Transportation, Greek_Life, Study_Space, Contact_Info
        - Safety -> RedEye_Night_Shuttle, Security_App, Campus_Escort, Card_Entry, Crime_Statistics, Contact_Info
        - Athletics -> Varsity_Sports, Intramural, Signature_Events, Contact_Info
        - Admission_Application -> Decision_Types_Outcomes, Dates_Deadlines, Portal_Info, Application_Materials, Financial_Aid, Estimated_Cost, Tours, Acceptance_Criteria_Stats, Contact_Info, AP_Credit_Lookup, Enrollment, Transfer_Applicants, Orientation, Honors_Program
        - Ranking_GeneralStats -> Overall_School_Ranking, Extracurriculars, Majors, Demographics, Career_Outcomes
        - Student_Support -> Contact_Info, Resources_Overview, Confidential_Resources, National_Resources, Policies
        - Experiential_Learning -> Coop_Process, Coop_Salary, Coop_Overview, Research, NU_View, Experiential_Projects
        - No_Matching_Group -> NoSubgroup (use when in-scope but no group fits)
        - NotApplicable -> NotApplicable (use when Out_Of_Scope or End_Call Overall classified )   

        ## Confidence and Clarification Rules
        - confidence: 0.0 to 1.0 indicating certainty of Group/Subgroup classification
        - Set confidence to 0.0 if Group is No_Matching_Group
        - clarification: Only populate if confidence <= 0.5 OR Group is No_Matching_Group
          - This should be a follow-up question to narrow down the user's intent

        ## Input
        
        Conversation History: {{transcript}}
        Current User Input: {{current_input}}

        {{ ctx.output_format }}
    "#
}





// test Test1Parse {
//     functions [ParseQuery]
//     args {
//         question #"
//           What GPA does Northeastern require for admissions?
//         "#
//     }
// }

test Test2Parse {
    functions [ClassifyInput]
    args {
        current_input #"
          What GPA does Northeastern require for admissions?
        "#
        transcript #"
            Agent: What can I help you with today?
        "#
    }
}



// enum Group {
//     Dining
//     Admissions
//     // For Out Of Scope General Classification
//     NotApplicable
// }

// enum Subgroup {
//     // Dining_food
//     Dining_Halls
//     Plan_Options_And_Cost

//     // Admission_Application
//     Decision_Types_Outcomes
//     Dates_Deadlines
//     Application_Materials
    
//     // For Out Of Scope General Classification
//     NotApplicable
// }


// class ClassifiedInput {
//     overall_classification Overall
//     group Group
//     subgroup Subgroup
//     confidence float? 
//     clarification string?  
// }

// function ClassifyInput_demo(current_input: string, transcript: string) -> ClassifiedInput{
//     client CustomGPT
//     prompt #"
//         <Our Prompt Here to Help the LLM Classify the input>

//         ## Input:
//         Conversation History: {{transcript}}
//         Current User Input: {{current_input}}

//         {{ ctx.output_format }}
//     "#
// }
