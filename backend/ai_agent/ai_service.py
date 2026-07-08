# backend/ai_agent/ai_service.py
import os
from groq import Groq
from ai_agent.prompts import build_system_prompt

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def test_groq_connection():
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": "hello"}
        ]
    )
    return response.choices[0].message.content


def test_system_prompt():
    system = build_system_prompt(
        job_title="Backend Developer",
        job_description="We need a Python/FastAPI developer with SQL experience."
    )
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": "Hello, I'm ready to start."}
        ]
    )
    return response.choices[0].message.content

def start_interview(job_title: str, job_description: str, required_skills: str = "", candidate_cv: str = "", candidate_name: str = ""):
    system = build_system_prompt(
        job_title=job_title,
        job_description=job_description,
        required_skills=required_skills,
        candidate_cv=candidate_cv,
        candidate_name=candidate_name
    )
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": "Hello, I am ready to start the interview."}
        ]
    )
    
    return response.choices[0].message.content


def continue_interview(
    job_title: str,
    job_description: str,
    required_skills: str,
    candidate_cv: str,
    candidate_name: str,
    conversation_history: list,
    force_end: bool = False
):
    system = build_system_prompt(
        job_title=job_title,
        job_description=job_description,
        required_skills=required_skills,
        candidate_cv=candidate_cv,
        candidate_name=candidate_name
    )

    if force_end:
        system += (
            "\n\nImportant: this should be the final interview question. "
            "If the interview has concluded, end your response with [INTERVIEW_END]."
        )

    # build the messages list for Groq
    messages = [{"role": "system", "content": system}]

    # add the full conversation history
    for msg in conversation_history:
        if msg.role == "ai":
            messages.append({"role": "assistant", "content": msg.content})
        else:
            messages.append({"role": "user", "content": msg.content})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
    )

    return response.choices[0].message.content


MAX_QUESTIONS = 25  # hard cap safety net

def should_force_end(message_count: int) -> bool:
    # message_count = number of AI questions asked so far
    return message_count >= MAX_QUESTIONS