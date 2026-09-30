import json

import ollama

from build_candidate_context import (
    build_candidate_context,
)
from candidate_shortlist import (
    create_shortlist,
)


MODEL_NAME = "qwen2.5:3b-instruct"


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "analyses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "reasoning": {
                        "type": "string"
                    }
                },
                "required": [
                    "name",
                    "reasoning"
                ]
            }
        }
    },
    "required": [
        "analyses"
    ]
}


SYSTEM_PROMPT = """
You are a fantasy football draft analyst.

Python has already ranked the candidates using deterministic draft rules.

You MUST NOT change the supplied ranking.

Your job is only to explain why each candidate is ranked where they are.

Use only the supplied information.

Do not use outside NFL knowledge.

Do not invent facts.

Do not exaggerate injuries or statuses.

Treat these fields as authoritative:

- deterministic_rank
- market_tier
- performance_trend
- availability_level
- role_quality
- current_status_category
- fills_unfilled_starter
- decision_flags

ADP is a market baseline.

Lower ADP means a player is generally drafted earlier.

Players in the same market tier are close enough in ADP that roster construction, selected draft strategy, current status, role, recent trend, and availability can affect their order.

Do not contradict the supplied deterministic ranking.

If a candidate was moved above another candidate because they fill an unfilled starter position, explain that when relevant.

If decision_flags indicate that a candidate matches the selected RB-heavy or WR-heavy strategy, you may mention that when relevant.

If a current injury, suspension, or role concern exists, explain it without increasing its severity.

For defenses, discuss only ADP, ranking, roster timing, and supplied team news.

Explanation rules:

- Do not describe injury information as suspension information.
- Do not describe suspension information as injury information.
- Never say "high ADP" or "low ADP".
- Say "earlier ADP" for a lower numerical ADP and "later ADP" for a higher numerical ADP.
- Do not say a player is already rostered unless that exact player is actually in the user's roster.
- If a position's starting slots are filled, say the position's starting slots are filled.
- Do not contradict authoritative fields.

Explain the candidates in the exact deterministic ranking order provided.

Keep each explanation to one concise sentence.
"""


def build_user_prompt(
    shortlist,
    starter_context,
    current_round,
    total_rounds,
    strategy,
    picks_until_next_turn=None,
):
    prompt_data = {
        "current_round": (
            current_round
        ),
        "total_rounds": (
            total_rounds
        ),
        "selected_strategy": (
            strategy
        ),
        "starter_context": (
            starter_context
        ),
        "ranked_shortlist": (
            shortlist
        ),
    }

    if (
        picks_until_next_turn
        is not None
    ):
        prompt_data[
            "picks_until_next_turn"
        ] = picks_until_next_turn

    return json.dumps(
        prompt_data,
        separators=(",", ":"),
    )


def validate_analysis(
    result,
    shortlist,
):
    analyses = result.get(
        "analyses",
        [],
    )

    explanation_lookup = {
        analysis.get(
            "name"
        ): analysis.get(
            "reasoning",
            "",
        )
        for analysis in analyses
    }

    rankings = []

    for candidate in shortlist:
        name = candidate["name"]

        rankings.append({
            "rank": candidate[
                "deterministic_rank"
            ],
            "name": name,
            "reasoning": (
                explanation_lookup.get(
                    name,
                    "No explanation returned.",
                )
            ),
        })

    return {
        "recommended_player": (
            rankings[0]["name"]
            if rankings
            else None
        ),
        "rankings": rankings,
        "shortlist": shortlist,
    }


def rank_players(
    candidates,
    my_roster,
    current_round,
    total_rounds,
    strategy="balanced",
    starter_requirements=None,
    picks_until_next_turn=None,
    shortlist_limit=5,
    live_data=None,
):
    candidate_context = (
        build_candidate_context(
            candidates=candidates,
            my_roster=my_roster,
            starter_requirements=(
                starter_requirements
            ),
            live_data=live_data,
        )
    )

    shortlist = create_shortlist(
        candidate_context=(
            candidate_context
        ),
        current_round=(
            current_round
        ),
        total_rounds=(
            total_rounds
        ),
        strategy=strategy,
        limit=shortlist_limit,
    )

    user_prompt = build_user_prompt(
        shortlist=shortlist,
        starter_context=(
            candidate_context[
                "starter_context"
            ]
        ),
        current_round=(
            current_round
        ),
        total_rounds=(
            total_rounds
        ),
        strategy=strategy,
        picks_until_next_turn=(
            picks_until_next_turn
        ),
    )

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    SYSTEM_PROMPT
                ),
            },
            {
                "role": "user",
                "content": (
                    user_prompt
                ),
            },
        ],
        format=RESPONSE_SCHEMA,
        options={
            "temperature": 0.1,
            "num_predict": 500,
        },
        keep_alive="30m",
    )

    result = json.loads(
        response[
            "message"
        ][
            "content"
        ]
    )

    return validate_analysis(
        result,
        shortlist,
    )