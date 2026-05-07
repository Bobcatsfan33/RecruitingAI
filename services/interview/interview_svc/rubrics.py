"""Role-specific interview rubrics.

Three baseline rubrics:
- ``sales``: deal narrative, strategic thinking, objection handling,
  communication clarity, quota validation.
- ``sales_engineering``: technical depth, demo presentation, customer
  empathy, communication clarity.
- ``cleared``: program experience, clearance timeline confirmation,
  availability + location, security culture.

Each dimension has a question prompt + scoring guidance. The interview
agent uses these to drive both the structured interview and the LLM
evaluation of the transcript.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Dimension:
    name: str
    question: str
    scoring_guide: str
    weight: float = 1.0


@dataclass
class Rubric:
    role_type: str
    intro: str
    dimensions: list[Dimension] = field(default_factory=list)
    pass_threshold: float = 3.5


SALES_RUBRIC = Rubric(
    role_type="sales",
    intro="Sales rubric — focus on deal narrative + strategic thinking.",
    dimensions=[
        Dimension(
            name="deal_narrative",
            question="Walk me through your largest deal in the last 12 months — how it started, what stalled it, how you closed it.",
            scoring_guide="5 = vivid story, named buyer roles, specific objections, quantified outcomes. 1 = vague, no numbers, no specific buyer dynamics.",
            weight=1.5,
        ),
        Dimension(
            name="strategic_thinking",
            question="When you walk into a new account, what's the first three things you do in the first two weeks?",
            scoring_guide="5 = territory plan, buyer mapping, partner intel. 1 = generic 'reach out and discover'.",
            weight=1.2,
        ),
        Dimension(
            name="objection_handling",
            question="Tell me about an objection you couldn't overcome. What would you do differently now?",
            scoring_guide="5 = specific objection, named root cause, learned framework. 1 = blames procurement.",
        ),
        Dimension(
            name="communication_clarity",
            question="Explain your current product to me as if I were a CFO with no technical background.",
            scoring_guide="5 = quantified ROI, no jargon, narrative arc. 1 = feature dump.",
        ),
        Dimension(
            name="quota_validation",
            question="What was your quota and attainment for the last two years?",
            scoring_guide="5 = exact numbers + W-2 trajectory. 1 = ranges + 'always over quota'.",
            weight=1.3,
        ),
    ],
)


SE_RUBRIC = Rubric(
    role_type="sales_engineering",
    intro="Sales engineering rubric — technical depth + demo skill.",
    dimensions=[
        Dimension(
            name="technical_depth",
            question="Pick a topic in your stack you'd say you have deepest expertise in. I'll ask three increasingly specific questions about it.",
            scoring_guide="5 = first-principles answers + edge cases + counter-examples. 1 = surface-level marketing language.",
            weight=1.5,
        ),
        Dimension(
            name="demo_presentation",
            question="Walk me through the demo you give to a Director of Engineering at a 1000-person SaaS company. Where do you start?",
            scoring_guide="5 = audience-specific, value-first, handles likely objections. 1 = product-tour from the homepage.",
            weight=1.5,
        ),
        Dimension(
            name="customer_empathy",
            question="A customer says 'this won't work for us'. How do you handle that mid-demo?",
            scoring_guide="5 = pause + diagnostic question. 1 = defend the product.",
        ),
        Dimension(
            name="communication_clarity",
            question="Explain a technical concept you find others struggle with — in 90 seconds, no diagrams.",
            scoring_guide="5 = analogy + concrete example + one technical anchor. 1 = jargon spiral.",
        ),
    ],
)


CLEARED_RUBRIC = Rubric(
    role_type="cleared",
    intro="Cleared rubric — program experience + availability.",
    dimensions=[
        Dimension(
            name="program_experience",
            question="Describe two programs you supported in the last 24 months. Sponsor, mission, your role, what you delivered.",
            scoring_guide="5 = named programs, sponsors, mission specifics, measurable outcomes. 1 = 'various government work'.",
            weight=1.5,
        ),
        Dimension(
            name="clearance_timeline",
            question="Confirm clearance type, polygraph, last adjudication date, and any read-on history.",
            scoring_guide="5 = active, current, broad read-on history, ITAR/EAR eligible. 1 = expired or in-process w/ no clear eta.",
            weight=1.3,
        ),
        Dimension(
            name="availability_location",
            question="What's your start window, location flexibility, and any commute / relocation constraints?",
            scoring_guide="5 = immediate + on-site flexible. 1 = 60+ days + remote-only.",
        ),
        Dimension(
            name="security_culture",
            question="Walk me through how you handle a SCIF-day-to-WFH transition — phones, transport of materials, etc.",
            scoring_guide="5 = first-principles + named protocols. 1 = vague.",
        ),
    ],
)


RUBRICS: dict[str, Rubric] = {
    r.role_type: r for r in (SALES_RUBRIC, SE_RUBRIC, CLEARED_RUBRIC)
}


def for_role(role_type: str) -> Rubric:
    return RUBRICS.get(role_type, SALES_RUBRIC)
