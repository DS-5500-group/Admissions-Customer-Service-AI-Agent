// initial trial classification schema for university questions
class UniQuery {
    group "Admission Requirements Domestic" | "Application Questions"
    subgroup "GPA" | "Dates" //@description("sub group related to primary group)" // description is decorator: will help LLM
        
}

// enum RankingSubgroup {OVERALL
// CS 
// HEALTH_SCIENCE 
// MATHS 
// ENGINEERING 
// BUSINESS 
// ARTS_HUMANITIES 
// SOCIAL_SCIENCE 
// LAW 
// MEDICINE 
// NURSING 
// PHARMACY}
enum FinancialSubgroup {
HOUSING
TUITION
OTHER
}
enum LocationSubgroup {
BOSTON
OAKLAND
NEW_YORK
}
enum CareerSubgroup {
COOP_INTERNSHIPS
OUTCOMES
LONG_TERM
}
enum ApplicationSubgroup {
DATES
FEES
ED
EA
}
enum AdmissionDomesticSubgroup {
GPA
SAT
ACT
}
enum AdmissionInternationalSubgroup {
GPA
SAT
ACT
LANGUAGE
}
enum ContactSubgroup {
ADMISSIONS
HEALTH_COUNSELING
DISABILITY
}

class RankingQuestion {
    Ranking_Subgroup "Overall" | "CS" | "HealthScience" | "Math" | "Engineering" | "Business"
}

// class RankingQuestion {
//     Ranking_Subgroup RankingSubgroup
// }

class FinancialQuestion {
    Financial_Subgroup FinancialSubgroup
}

class LocationQuestion {
    Location_Subgroup LocationSubgroup
}

class CareerQuestion {
    Career_Subgroup CareerSubgroup
}

class ApplicationQuestion {
    Application_Subgroup ApplicationSubgroup
}

class AdmissionDomesticQuestion {
    AdmissionDomestic_Subgroup AdmissionDomesticSubgroup
}

class AdmissionInternationalQuestion {
    AdmissionInternational_Subgroup AdmissionInternationalSubgroup
}

class ContactQuestion {
    Contact_Subgroup ContactSubgroup
}

class OtherQuestion {
    UnAnswerable string  // Why it's unanswerable
}

class ClassifiedQuestion {
    category RankingQuestion | FinancialQuestion | LocationQuestion | CareerQuestion | ApplicationQuestion | AdmissionDomesticQuestion | AdmissionInternationalQuestion | ContactQuestion | OtherQuestion
    //universityMentioned string?
    //confidence float
}


// function 1: parse user question
// "{{ ctx.output_format }}" causes JSON formatting request to be added to the prompt based on BAML class
//   Can view this extra prompt in the BAML Playground (requires VScode extension)
function ParseQuery(question:string) -> ClassifiedQuestion {
    client CustomGPT
    prompt #"
        Classify the input user question into the question Group and its SubGroup. 

        Question: {{question}}

        {{ ctx.output_format }}
    "#
}

function AnswerQuery(question:string, context:string) -> string {
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
