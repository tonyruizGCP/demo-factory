"""Local LLM-as-judge for `custom_response_quality` (see eval_config.yaml).

Aligned with the Standardized 1-5 Evaluation Rating Scale from the
Gemini Enterprise Technical Deployment Runbook (Phase 4, Section 4.5).
"""

from google import genai
from google.genai import types
from pydantic import BaseModel


class _Verdict(BaseModel):
    score: int  # 1-5
    explanation: str


def evaluate(instance):
    reference = instance.get("reference")
    rubric = (
        "You are an impartial expert evaluator grading the quality of an enterprise AI "
        "assistant's response against a verified Golden Ground Truth answer and retrieved "
        "source context on a 1-5 scale (1 poor, 5 excellent). Focus strictly on factual "
        "correctness, relevance to the user's question, and completeness of key requirements. "
        "Ignore minor stylistic differences, tone variations, organization prefix names, or "
        "bullet formatting unless they alter factual meaning."
    )
    if reference:
        rubric += (
            " The response should agree with the core facts of the expected answer below; "
            "do not penalize additional helpful grounded context retrieved from the tools."
        )
    prompt = (
        f"{rubric}\n"
        f"User Prompt: {instance.get('prompt', '')}\n"
        f"Final Response: {instance.get('response', '')}\n"
    )
    if reference:
        prompt += f"Expected Answer (ground truth): {reference}\n"
    prompt += f"Full Agent Trace: {instance.get('agent_data', '')}\n"

    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=_Verdict,
        ),
    )
    verdict = response.parsed
    if verdict is None:
        return {"score": 0, "explanation": response.text or ""}
    return {"score": max(1, min(5, verdict.score)), "explanation": verdict.explanation}
