// ─── Group enum ───
enum Group {
    Dining_food
    Housing
    Student_Amenities_Activities
    Safety
    Athletics
    Admission_Application
    Ranking_GeneralStats
    Student_Support
    UnAnswerable
}

// ─── Subgroup enum (flat; Group field disambiguates shared values like Contact_Info) ───
enum Subgroup {
    // Dining_food
    Dining_Halls
    Retail_Dining
    Allergy_Info
    Plan_Cost
    Food_Options

    // Housing
    Housing_Cost
    Layout_Info
    Off_Campus

    // Student_Amenities_Activities
    Gym
    Student_Activities_Fees
    Clubs
    Game_Rooms
    Volunteering

    // Safety
    Redeye
    Security_App
    Campus_Escort
    Card_Entry

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

    // Ranking_GeneralStats
    Overall_Ranking
    Extracurriculars
    Majors
    GeneralStats

    // Student_Support
    Resources_Overview
    Confidential_Resources
    National_Resources
    Policies

    // Shared across multiple groups
    Contact_Info

    // For UnAnswerable group
    NoSubgroup
}

// ─── Output class ───
class ClassifiedQuestion {
    group Group
    subgroup Subgroup
    reason string?  @description("Only populated when group is UnAnswerable")
}


// ─── Functions ───

function ParseQuery(question: string) -> ClassifiedQuestion {
    client CustomGPT
    prompt #"
        Classify the user's question into one Group and one Subgroup.

        Valid (Group -> Subgroup) mappings:
        - Dining_food -> Dining_Halls, Retail_Dining, Allergy_Info, Contact_Info, Plan_Cost, Food_Options
        - Housing -> Housing_Cost, Layout_Info, Off_Campus, Contact_Info
        - Student_Amenities_Activities -> Gym, Student_Activities_Fees, Clubs, Game_Rooms, Volunteering, Contact_Info
        - Safety -> Redeye, Security_App, Campus_Escort, Card_Entry, Contact_Info
        - Athletics -> Varsity_Sports, Intramural, Signature_Events, Contact_Info
        - Admission_Application -> Decision_Types_Outcomes, Dates_Deadlines, Portal_Info, Application_Materials, Financial_Aid, Estimated_Cost, Tours, Acceptance_Criteria_Stats, Contact_Info, AP_Credit_Lookup, Enrollment
        - Ranking_GeneralStats -> Overall_Ranking, Extracurriculars, Majors, GeneralStats
        - Student_Support -> Contact_Info, Resources_Overview, Confidential_Resources, National_Resources, Policies
        - UnAnswerable -> NoSubgroup  (set reason to explain why)

        Question: {{question}}

        {{ ctx.output_format }}
    "#
}

function AnswerQuery(question: string, context: string) -> string {
    client CustomGPT
    prompt #"
        Answer the user's question concisely and accurately using the context provided.

        User question: {{question}}

        University info context: {{context}}
    "#
}


test Test1Parse {
    functions [ParseQuery]
    args {
        question #"
          What GPA does Northeastern require for admissions?
        "#
    }
}
