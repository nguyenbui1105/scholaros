"""Offline demonstration entrypoint; all opportunities are explicitly synthetic."""
import argparse
from datetime import date, timedelta

from .eligibility import assess_eligibility
from .models import AIUsePolicy, ClaimRecord, Opportunity, Student
from .ranking import rank_eligible


def demo() -> None:
    today = date.today()
    student = Student("undergraduate", "F-1", {"computer_science"}, 3.8, "Demo College")
    url = "https://demo.edu/scholarship"
    opportunities = [
        Opportunity(
            id="demo-stem", title="Fictional STEM Opportunity — NOT REAL",
            official_url=url, eligible_levels={"undergraduate"},
            eligible_visas={"F-1"}, eligible_majors={"computer_science"},
            min_gpa=3.5, allowed_schools={"Demo College"},
            deadline=today + timedelta(days=45), verified_on=today,
            international_claim=ClaimRecord(
                "F-1 eligible", url, today,
                "F-1 students are eligible (fictional fixture).", "fixture-hash", "fixture",
            ),
            ai_use_policy=AIUsePolicy.EDITING_ONLY,
            award_usd=2500, effort_hours=3.0,
        ),
        Opportunity(
            id="demo-unknown", title="Fictional Unverified Opportunity — NOT REAL",
            official_url="https://demo.edu/unknown",
            eligible_levels={"undergraduate"}, deadline=today + timedelta(days=30),
            award_usd=5000,
        ),
        Opportunity(
            id="demo-ineligible", title="Fictional Graduate Award — NOT REAL",
            official_url=url, eligible_levels={"graduate"},
            eligible_visas={"F-1"}, eligible_majors={"computer_science"},
            allowed_schools={"Demo College"}, min_gpa=3.0,
            deadline=today + timedelta(days=60), verified_on=today,
        ),
    ]
    assessed = [(o, assess_eligibility(student, o, today=today)) for o in opportunities]
    print("ScholarOS offline demo — ALL OPPORTUNITIES ARE FICTIONAL")
    for opportunity, result in assessed:
        print(f"- {opportunity.id}: {result.decision.value} | "
              + "; ".join(reason.code for reason in result.reasons))
    print("Verified eligible ranking:")
    for item in rank_eligible(student, assessed):
        print(f"- {item.opportunity.id}: {item.score:.2f} (priority, not probability)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="scholaros")
    parser.add_argument("command", choices=["demo"])
    args = parser.parse_args()
    if args.command == "demo":
        demo()


if __name__ == "__main__":
    main()
