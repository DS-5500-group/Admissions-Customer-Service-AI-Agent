enum FinancialSubgroup {
Housing
Tuition
Other
}
enum LocationSubgroup {
Boston
Oakland
NewYork
}
enum CareerSubgroup {
Employment
Coop
}
enum ApplicationSubgroup {
Dates
Fees
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
Admissions
StudentServices
Disability
}

class RankingQuestion {
    Ranking "Overall" | "CS" | "HealthScience" | "Math" | "Engineering" | "Business"
}

// class RankingQuestion {
//     Ranking_Subgroup RankingSubgroup
// }

class FinancialQuestion {
    Financial FinancialSubgroup
}

class LocationQuestion {
    LocationInformation LocationSubgroup
}

class CareerQuestion {
    CareerOutcomes CareerSubgroup
}

class ApplicationQuestion {
    ApplicationQuestions ApplicationSubgroup
}

class AdmissionDomesticQuestion {
    AdmissionRequirementsDomestic AdmissionDomesticSubgroup
}

class AdmissionInternationalQuestion {
    AdmissionRequirementsInternational AdmissionInternationalSubgroup
}

class ContactQuestion {
    ContactandExternalResources ContactSubgroup
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
