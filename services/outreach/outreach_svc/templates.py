"""Outreach + close-protection templates.

Each template is a function ``(ctx) -> dict`` returning {subject, body_text,
body_html?}. Template ids are referenced by `Step.template_id` in the
sequence engine. Variables get substituted at render time from the
candidate / requisition / variant context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class TemplateContext:
    candidate_first_name: str
    candidate_last_name: str
    candidate_company: str | None = None
    candidate_recent_role: str | None = None
    requisition_title: str | None = None
    client_name: str | None = None
    recruiter_first_name: str = "Alex"
    recruiter_email: str = "alex@workforce.local"
    counteroffer_inoculation: bool = False
    motion_type: str | None = None
    metro: str | None = None


def _intro_v1(ctx: TemplateContext) -> dict[str, str]:
    inoculation = (
        "\n\nHonest framing: most candidates we work with end up with a "
        "counteroffer from their current employer. The candidates who get "
        "the most out of the conversation are the ones who decide whether "
        "this is interesting on its own merits before that conversation "
        "happens — happy to chat from that frame."
        if ctx.counteroffer_inoculation else ""
    )
    return {
        "subject": f"{ctx.candidate_first_name}, quick question about {ctx.requisition_title}",
        "body_text": (
            f"Hi {ctx.candidate_first_name},\n\n"
            f"I noticed your background as {ctx.candidate_recent_role or 'a senior IC'} "
            f"at {ctx.candidate_company or 'your current company'}. "
            f"I'm working on a {ctx.requisition_title} role with {ctx.client_name or 'a client'} "
            "and your profile lined up unusually well — particularly the motion fit "
            f"({ctx.motion_type or 'enterprise'}).\n\n"
            "If you're open to a 15-minute conversation about the role + market "
            "comp data, I can come prepared with specifics. If not, "
            "no worries — totally fine to ignore."
            f"{inoculation}\n\n"
            f"— {ctx.recruiter_first_name}"
        ),
    }


def _li_intro_v1(ctx: TemplateContext) -> dict[str, str]:
    return {
        "subject": "",
        "body_text": (
            f"Hey {ctx.candidate_first_name} — I sent a note to your work email about "
            f"a {ctx.requisition_title}. If LinkedIn is easier, happy to share "
            "the comp band + scope here. — " + ctx.recruiter_first_name
        ),
    }


def _value_v1(ctx: TemplateContext) -> dict[str, str]:
    return {
        "subject": f"Re: {ctx.requisition_title} — comp + market context",
        "body_text": (
            f"{ctx.candidate_first_name},\n\n"
            f"Following up. Three things you'd probably want to know up-front:\n\n"
            f"1. Comp: real OTE band on this role + market comp for {ctx.metro or 'your metro'} "
            f"with your motion mix.\n"
            f"2. Why this client is hiring NOW (it's not a backfill).\n"
            f"3. The two questions every previous finalist asked — and how the hiring manager answered.\n\n"
            "Want me to send a one-pager with all three? — " + ctx.recruiter_first_name
        ),
    }


def _touch3_v1(ctx: TemplateContext) -> dict[str, str]:
    return {
        "subject": f"{ctx.candidate_first_name}, last note",
        "body_text": (
            f"Hi {ctx.candidate_first_name},\n\n"
            "Closing the loop on this one. If the timing isn't right, "
            "totally understand — I'll keep an eye out for roles that match "
            "your trajectory. Always happy to share market comp data on "
            "request, no strings.\n\n"
            f"— {ctx.recruiter_first_name}"
        ),
    }


def _breakup_v1(ctx: TemplateContext) -> dict[str, str]:
    return {
        "subject": "Closing the loop",
        "body_text": (
            f"{ctx.candidate_first_name} — moving you to passive in our system. "
            "If you'd ever like a market check on your comp / level, just reply "
            f"to this email. — {ctx.recruiter_first_name}"
        ),
    }


def _velocity_text_v1(ctx: TemplateContext) -> dict[str, str]:
    return {
        "subject": "",
        "body_text": (
            f"{ctx.candidate_first_name}, this is {ctx.recruiter_first_name}. "
            f"Quick fit on a {ctx.requisition_title} in {ctx.metro or 'your area'} — "
            "interested in 5 min to compare against your current setup?"
        ),
    }


def _velocity_call_v1(ctx: TemplateContext) -> dict[str, str]:
    # Used by the phone outreach worker as a script for the inside recruiter.
    return {
        "subject": "Voice script",
        "body_text": (
            f"Voicemail script: 'Hi {ctx.candidate_first_name}, "
            f"{ctx.recruiter_first_name} from Workforce. Reaching out on a "
            f"{ctx.requisition_title} — comp band looks above market. "
            f"Try me at {ctx.recruiter_email} or text back. Thanks.'"
        ),
    }


def _velocity_recap_v1(ctx: TemplateContext) -> dict[str, str]:
    return {
        "subject": f"{ctx.requisition_title} — fit recap",
        "body_text": (
            f"{ctx.candidate_first_name},\n\n"
            "Recap of the role I texted/called about:\n"
            f"- Title: {ctx.requisition_title}\n"
            f"- Location: {ctx.metro}\n"
            f"- Why it might fit: motion alignment + comp above current market band\n\n"
            f"Quick reply if you want the comp range. — {ctx.recruiter_first_name}"
        ),
    }


# --- close protection templates -------------------------------------------

def _cp(template: str) -> Callable[[TemplateContext], dict[str, str]]:
    def render(ctx: TemplateContext) -> dict[str, str]:
        return {
            "subject": f"{ctx.requisition_title} — checking in",
            "body_text": template.format(**{
                "first_name": ctx.candidate_first_name,
                "title": ctx.requisition_title,
                "client": ctx.client_name or "the team",
                "recruiter": ctx.recruiter_first_name,
            }),
        }
    return render


_CP_DAY1 = _cp(
    "Hey {first_name} — congrats on accepting the offer at {client}!\n\n"
    "Quick note while it's fresh: this is the moment when current employers "
    "start the counter. If anything comes up between now and your start "
    "date, my number is on file. Happy to talk through it.\n\n— {recruiter}"
)
_CP_DAY3 = _cp(
    "{first_name} — three days in. How's the resignation conversation going? "
    "What did your current manager say?\n\nNothing surprises me — just helpful "
    "for me to know if the script needs a tweak.\n\n— {recruiter}"
)
_CP_DAY7 = _cp(
    "{first_name} — week one done. Any second-thought moments? Reply with a "
    "single word and I'll know how to read it: 'great', 'fine', or 'wobbly'."
)
_CP_DAY10 = _cp(
    "{first_name} — sharing the start-date prep checklist {client}'s ops "
    "team uses. Equipment, calendar invites, first-week 1:1s, etc."
)
_CP_DAY14 = _cp(
    "{first_name} — two weeks until start. Any logistics still open?"
)
_CP_DAY21 = _cp(
    "{first_name} — three weeks in to notice. The last two weeks usually "
    "have the most counter activity. Anything I should know?"
)
_CP_DAY28 = _cp(
    "{first_name} — final stretch. Looking forward to your start at {client}."
)


TEMPLATES: dict[str, Callable[[TemplateContext], dict[str, str]]] = {
    "intro_v1": _intro_v1,
    "li_intro_v1": _li_intro_v1,
    "value_v1": _value_v1,
    "touch3_v1": _touch3_v1,
    "breakup_v1": _breakup_v1,
    "velocity_text_v1": _velocity_text_v1,
    "velocity_call_v1": _velocity_call_v1,
    "velocity_recap_v1": _velocity_recap_v1,
    "cp_day1_v1": _CP_DAY1,
    "cp_day3_v1": _CP_DAY3,
    "cp_day7_v1": _CP_DAY7,
    "cp_day10_v1": _CP_DAY10,
    "cp_day14_v1": _CP_DAY14,
    "cp_day21_v1": _CP_DAY21,
    "cp_day28_v1": _CP_DAY28,
}


def render(template_id: str, ctx: TemplateContext) -> dict[str, str]:
    fn = TEMPLATES.get(template_id)
    if fn is None:
        raise KeyError(f"unknown template_id {template_id}")
    return fn(ctx)
