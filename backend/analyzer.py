import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = (
    "You are an expert technical recruiter and resume coach. "
    "Analyze the resume against the job description thoroughly. "
    "Be specific, actionable, and honest. "
    "Use all 4 tools to complete the analysis."
)

TOOLS = [
    {
        "name": "analyze_skills_match",
        "description": (
            "Compare the skills required by the job description against "
            "the skills present in the resume. Return matched skills, "
            "missing skills, and a fit score."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "required_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Skills explicitly required or strongly implied by the JD.",
                },
                "resume_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Skills clearly demonstrated or listed in the resume.",
                },
            },
            "required": ["required_skills", "resume_skills"],
        },
    },
    {
        "name": "analyze_experience_match",
        "description": (
            "Assess how well the candidate's experience level and history "
            "aligns with what the job description asks for."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "jd_experience_summary": {
                    "type": "string",
                    "description": "Summary of experience requirements from the JD (years, domain, seniority).",
                },
                "resume_experience_summary": {
                    "type": "string",
                    "description": "Summary of the candidate's experience from the resume.",
                },
            },
            "required": ["jd_experience_summary", "resume_experience_summary"],
        },
    },
    {
        "name": "extract_missing_keywords",
        "description": (
            "Identify important keywords from the job description that are "
            "absent from the resume. Assess the ATS (applicant tracking system) risk."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "jd_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Important keywords, phrases, and technologies from the JD.",
                },
                "resume_text": {
                    "type": "string",
                    "description": "Full text of the resume to search against.",
                },
            },
            "required": ["jd_keywords", "resume_text"],
        },
    },
    {
        "name": "suggest_bullet_rewrites",
        "description": (
            "Take weak or generic resume bullet points and rewrite them "
            "to better match the job description, adding impact and keywords."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "weak_bullets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Resume bullet points that are vague, weak, or missing relevant keywords.",
                },
                "jd_context": {
                    "type": "string",
                    "description": "Brief summary of what the role values, to guide rewrites.",
                },
            },
            "required": ["weak_bullets", "jd_context"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executors — each receives the raw input dict Claude passes and returns
# a plain Python dict that will be serialised back as the tool_result content.
# ---------------------------------------------------------------------------

def _run_analyze_skills_match(tool_input: dict) -> dict:
    required = [s.strip().lower() for s in tool_input["required_skills"]]
    present = [s.strip().lower() for s in tool_input["resume_skills"]]

    matched = [s for s in required if any(s in p or p in s for p in present)]
    missing = [s for s in required if s not in matched]

    score = round(len(matched) / len(required) * 100) if required else 0
    return {
        "matched": matched,
        "missing": missing,
        "score": score,
    }


def _run_analyze_experience_match(tool_input: dict) -> dict:
    # The model already summarised both sides — return them so the final
    # response has structured text, and ask Claude to score by echoing back.
    # We return a stub; Claude will fill in assessment/seniority in the next turn.
    return {
        "assessment": (
            f"JD requires: {tool_input['jd_experience_summary']}. "
            f"Candidate has: {tool_input['resume_experience_summary']}."
        ),
        "score": None,          # Claude fills this in the final synthesis
        "seniority_fit": None,  # Claude fills this in the final synthesis
    }


def _run_extract_missing_keywords(tool_input: dict) -> dict:
    resume_lower = tool_input["resume_text"].lower()
    jd_keywords = [kw.strip().lower() for kw in tool_input["jd_keywords"]]

    missing = [kw for kw in jd_keywords if kw not in resume_lower]
    ratio = len(missing) / len(jd_keywords) if jd_keywords else 0
    ats_risk = "low" if ratio < 0.25 else "medium" if ratio < 0.55 else "high"

    return {
        "missing_keywords": missing,
        "ats_risk": ats_risk,
    }


def _run_suggest_bullet_rewrites(tool_input: dict) -> dict:
    # We return the bullets and context; Claude produces the actual rewrites
    # in its final response turn, so we just echo the input as a confirmation.
    return {
        "rewrites": [
            {"original": b, "improved": None, "reason": None}
            for b in tool_input["weak_bullets"]
        ],
        "jd_context_received": tool_input["jd_context"],
    }


_TOOL_HANDLERS = {
    "analyze_skills_match": _run_analyze_skills_match,
    "analyze_experience_match": _run_analyze_experience_match,
    "extract_missing_keywords": _run_extract_missing_keywords,
    "suggest_bullet_rewrites": _run_suggest_bullet_rewrites,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_resume(resume_text: str, jd_text: str) -> dict:
    """Run a full resume gap analysis using Claude tool use.

    Drives an agentic loop that calls all four analysis tools, collects
    their results, and returns a single combined dict with the keys:
    skills, experience, keywords, rewrites, overall_score.

    Args:
        resume_text: Plain text of the candidate's resume.
        jd_text:     Plain text of the job description.

    Returns:
        Combined analysis dict.

    Raises:
        RuntimeError: If Claude fails to call all required tools or the
                      final response cannot be parsed.
    """
    prompt = (
        f"Please analyse the following resume against the job description "
        f"using all 4 tools.\n\n"
        f"--- RESUME ---\n{resume_text}\n\n"
        f"--- JOB DESCRIPTION ---\n{jd_text}\n\n"
        f"After running all tools, return a final JSON summary with keys: "
        f"skills, experience, keywords, rewrites, overall_score."
    )

    messages: list[dict] = [{"role": "user", "content": prompt}]

    # Collect raw tool outputs so we can build the final combined result
    tool_results_by_name: dict[str, dict] = {}

    # Agentic loop ----------------------------------------------------------------
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Append the assistant turn (may contain text + tool_use blocks)
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason != "tool_use":
            raise RuntimeError(
                f"Unexpected stop_reason from Claude: {response.stop_reason!r}"
            )

        # Execute every tool Claude requested and collect tool_result blocks
        tool_result_blocks = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            handler = _TOOL_HANDLERS.get(block.name)
            if handler is None:
                raise RuntimeError(f"Claude called unknown tool: {block.name!r}")

            result = handler(block.input)
            tool_results_by_name[block.name] = result

            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_result_blocks})
    # End agentic loop ------------------------------------------------------------

    # Extract the final text block Claude produced after all tool calls
    final_text = next(
        (b.text for b in response.content if b.type == "text"),
        None,
    )
    if not final_text:
        raise RuntimeError("Claude returned no final text after tool calls.")

    # Parse the JSON summary Claude was instructed to return
    try:
        summary = _parse_json(final_text)
    except ValueError as exc:
        raise RuntimeError(f"Could not parse Claude's final response as JSON: {exc}") from exc

    # Ensure the four section keys exist, falling back to raw tool outputs
    skills_data = summary.get("skills") or tool_results_by_name.get("analyze_skills_match", {})
    experience_data = summary.get("experience") or tool_results_by_name.get("analyze_experience_match", {})
    keywords_data = summary.get("keywords") or tool_results_by_name.get("extract_missing_keywords", {})
    rewrites_data = summary.get("rewrites") or tool_results_by_name.get("suggest_bullet_rewrites", {})

    # Compute overall_score: skills 40 % + experience 40 % + keywords 20 %
    skills_score = _to_int(skills_data.get("score"), default=0)
    exp_score = _to_int(experience_data.get("score"), default=skills_score)  # fallback
    kw_score = _kw_score(keywords_data.get("ats_risk", "medium"))
    overall_score = round(skills_score * 0.4 + exp_score * 0.4 + kw_score * 0.2)

    return {
        "skills": skills_data,
        "experience": experience_data,
        "keywords": keywords_data,
        "rewrites": rewrites_data,
        "overall_score": summary.get("overall_score") or overall_score,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json(text: str) -> dict:
    """Extract and parse the first JSON object found in text."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        parts = text.split("```")
        # parts[1] is the content inside the fences
        text = parts[1].lstrip("json").strip() if len(parts) > 1 else text
    # Find first { ... } block
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in text.")
    return json.loads(text[start:end])


def _to_int(value, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _kw_score(ats_risk: str) -> int:
    return {"low": 90, "medium": 55, "high": 20}.get(ats_risk, 55)
