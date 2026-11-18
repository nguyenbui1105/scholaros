"""Offline demonstration entrypoint."""
import argparse
from datetime import date, timedelta

from .eligibility import assess_eligibility
from .models import AIUsePolicy, Opportunity, Student
from .ranking import rank_eligible


def demo() -> None:
    today = date.today()
    student = Student("undergraduate", "F-1", frozenset({"computer_science"}), 3.8, "Demo College")
    opportunities = [
        Opportunity(
            id="demo-stem", title="Fictional STEM Opportunity — NOT REAL",
            official_url="https://example.org/stem", eligible_levels=frozenset({"undergraduate"}),
            eligible_visas=frozenset({"F-1"}), eligible_majors=frozenset({"computer_science"}),
            min_gpa=3.5, deadline=today + timedelta(days=45), verified_on=today,
            international_eligibility_confirmed=True, ai_use_policy=AIUsePolicy.EDITING_ONLY,
            award_usd=2500, effort_hours=3.0,
        ),
        Opportunity(
            id="demo-unknown", title="Fictional Unverified Opportunity — NOT REAL",
            official_url="https://example.org/unknown", eligible_levels=frozenset({"undergraduate"}),
            deadline=today + timedelta(days=30), award_usd=5000,
        ),
        Opportunity(
            id="demo-ineligible", title="Fictional Graduate Award — NOT REAL",
            official_url="https://example.org/graduate",
            eligible_levels=frozenset({"graduate"}), deadline=today + timedelta(days=60),
            verified_on=today, international_eligibility_confirmed=True,
        ),
    ]
    assessed = [(o, assess_eligibility(student, o, today=today)) for o in opportunities]
    print("ScholarOS offline demo — ALL OPPORTUNITIES ARE FICTIONAL")
    for o, result in assessed:
        print(f"- {o.id}: {result.decision.value} | {'; '.join(result.reasons)}")
    print("Verified eligible ranking:")
    for item in rank_eligible(student, assessed):
        print(f"- {item.opportunity.id}: {item.score:.2f} (priority score, not probability)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="scholaros")
    parser.add_argument("command", choices=["demo"], help="Run the offline fictional-data demo")
    args = parser.parse_args()
    if args.command == "demo":
        demo()


if __name__ == "__main__":
    main()
