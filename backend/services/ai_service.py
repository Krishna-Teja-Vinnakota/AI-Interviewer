"""AI services: Vertex AI (Gemini, embeddings), Google TTS."""
import os
import json
import logging
from typing import List, Optional
import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel
import google.cloud.texttospeech as tts
from core.config import settings, get_vertex_ai_credentials, get_google_tts_credentials

logger = logging.getLogger(__name__)

# Initialize Vertex AI
_vertex_ai_initialized = False


def _init_vertex_ai():
    """Initialize Vertex AI with service account credentials."""
    global _vertex_ai_initialized
    if _vertex_ai_initialized:
        return
    
    try:
        credentials = get_vertex_ai_credentials()
        project_id = settings.VERTEX_AI_PROJECT_ID or credentials.get("project_id")
        location = settings.VERTEX_AI_LOCATION
        
        # Set credentials as environment variable
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.VERTEX_AI_SERVICE_ACCOUNT_PATH
        
        vertexai.init(project=project_id, location=location)
        _vertex_ai_initialized = True
        logger.info(f"Vertex AI initialized successfully for project: {project_id}")
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}")
        raise


async def generate_embeddings(text: str) -> List[float]:
    """Generate embeddings using text-embedding-004."""
    try:
        _init_vertex_ai()
        
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        embeddings = model.get_embeddings([text])
        logger.info("Successfully generated embeddings")
        return embeddings[0].values
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise


async def generate_questions(jd_text: str, resume_text: str, num_questions: int = 10) -> List[dict]:
    """Generate interview questions using Gemini 2.5 Pro.
    
    Returns questions with source tags:
    - 4 questions from JD
    - 4 questions from resume
    - 2 behavioral questions
    """
    try:
        _init_vertex_ai()
        
        model = GenerativeModel("gemini-2.5-pro")
        
        prompt = f"""You are an expert technical interviewer. Based on the job description and candidate resume, generate EXACTLY 10 interview questions following this strict breakdown:

Job Description:
{jd_text}

Candidate Resume:
{resume_text}

CRITICAL REQUIREMENTS:
Generate EXACTLY:
1. 4 questions based SPECIFICALLY on the Job Description requirements, skills, and responsibilities mentioned in the JD
2. 4 questions based SPECIFICALLY on the candidate's Resume - their experience, projects, and skills they've listed
3. 2 behavioral/situational questions to assess soft skills and cultural fit

Return ONLY a JSON object with three arrays, no additional text. Format:
{{
    "jd_questions": ["question1", "question2", "question3", "question4"],
    "resume_questions": ["question1", "question2", "question3", "question4"],
    "behavioral_questions": ["question1", "question2"]
}}

IMPORTANT:
- JD questions should probe whether candidate can fulfill the job requirements
- Resume questions should dig deeper into their actual experience and projects
- Behavioral questions should assess teamwork, problem-solving, and communication
- Each array must have the EXACT number of questions specified above"""

        response = model.generate_content(prompt)
        
        # Parse JSON response
        try:
            import json
            questions_text = response.text.strip()
            # Remove markdown code blocks if present
            if questions_text.startswith("```"):
                questions_text = questions_text.split("```")[1]
                if questions_text.startswith("json"):
                    questions_text = questions_text[4:]
            questions_data = json.loads(questions_text)
            
            # Combine questions with source tags
            all_questions = []
            
            # Add JD questions
            for q in questions_data.get("jd_questions", [])[:4]:
                all_questions.append({"text": q, "source": "jd"})
            
            # Add resume questions
            for q in questions_data.get("resume_questions", [])[:4]:
                all_questions.append({"text": q, "source": "resume"})
            
            # Add behavioral questions
            for q in questions_data.get("behavioral_questions", [])[:2]:
                all_questions.append({"text": q, "source": "behavioral"})
            
            logger.info(f"Successfully generated {len(all_questions)} questions (JD: 4, Resume: 4, Behavioral: 2)")
            return all_questions
        except Exception as e:
            logger.error(f"JSON parsing failed: {e}")
            raise
    except Exception as e:
        logger.error(f"Failed to generate questions: {e}")
        raise


async def analyze_interview(
    questions: List[str],
    answers: List[str]
) -> dict:
    """Analyze interview using Gemini 2.5 Pro."""
    _init_vertex_ai()
    
    model = GenerativeModel("gemini-2.5-pro")
    
    # Build Q&A context
    qa_context = "\n".join([
        f"Q{i+1}: {q}\nA{i+1}: {a}\n" 
        for i, (q, a) in enumerate(zip(questions, answers))
    ])
    
    prompt = f"""Analyze the following interview and provide a comprehensive evaluation.

Questions and Answers:
{qa_context}

IMPORTANT INSTRUCTIONS:
1. If an answer is "[Question skipped by candidate]" or empty:
   - Give it a score of 0/10
   - Feedback: "Question was not answered by the candidate."
   
2. If an answer contains actual text (not the skip message):
   - Analyze the ACTUAL content provided by the candidate
   - Score based on relevance, technical accuracy, completeness, and communication
   - Provide detailed feedback on the response quality
   
3. Do NOT make up or imagine answers - only analyze what the candidate actually said.

4. Overall scoring:
   - If most questions were skipped, overall score should be very low (0-3/10)
   - If candidate provided good answers, score them appropriately (7-10/10 for excellent)
   - The recommendation should be "reject" if more than 30% of questions were skipped
   - The recommendation should be "proceed" if candidate answered well with good technical depth

Provide analysis in the following JSON format:
{{
    "overall_score": <float 0-10>,
    "recommendation": "<proceed|reject|maybe>",
    "strengths": ["strength1", "strength2", ...],
    "weaknesses": ["weakness1", "weakness2", ...],
    "question_analysis": [
        {{
            "question": "question text",
            "answer": "answer text",
            "score": <float 0-10>,
            "feedback": "detailed feedback"
        }},
        ...
    ]
}}

Return ONLY valid JSON, no additional text."""

    response = model.generate_content(prompt)
    
    try:
        import json
        result_text = response.text.strip()
        # Remove markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        return json.loads(result_text)
    except Exception as e:
        # Fallback response
        return {
            "overall_score": 5.0,
            "recommendation": "maybe",
            "strengths": [],
            "weaknesses": ["Unable to parse analysis"],
            "question_analysis": []
        }


async def text_to_speech(text: str, output_file: Optional[str] = None) -> bytes:
    """Convert text to speech using Google TTS."""
    credentials = get_google_tts_credentials()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_TTS_CREDENTIALS_PATH or settings.VERTEX_AI_SERVICE_ACCOUNT_PATH
    
    client = tts.TextToSpeechClient()
    
    synthesis_input = tts.SynthesisInput(text=text)
    voice = tts.VoiceSelectionParams(
        language_code="en-IN",  # English with Indian accent
        ssml_gender=tts.SsmlVoiceGender.NEUTRAL
    )
    audio_config = tts.AudioConfig(
        audio_encoding=tts.AudioEncoding.MP3
    )
    
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    
    return response.audio_content


async def analyze_call_conversation(transcript: str) -> dict:
    """
    Analyze call conversation to determine:
    1. Is candidate interested?
    2. What's the reason if not interested?
    3. Extract candidate name if mentioned
    """
    try:
        _init_vertex_ai()
        model = GenerativeModel("gemini-2.5-pro")
        
        prompt = f"""Analyze this phone conversation transcript from a recruitment call.

TRANSCRIPT:
{transcript}

Determine:
1. Is the candidate interested in proceeding with the interview?
2. If not interested, what's the reason?
3. What's the candidate's name if mentioned?
4. Provide a brief summary of the conversation

Return ONLY valid JSON in this format:
{{
    "candidate_interested": <boolean>,
    "candidate_name": "<name or 'Candidate'>",
    "rejection_reason": "<reason if not interested, otherwise empty string>",
    "summary": "<brief 1-2 sentence summary>",
    "confidence_score": <float 0-1>
}}

Focus on keywords like "yes", "interested", "no", "not available", "not interested", etc."""

        response = model.generate_content(prompt)
        
        result_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.rsplit("```", 1)[0]
        
        analysis = json.loads(result_text)
        logger.info(f"Call analysis: Interested={analysis.get('candidate_interested')}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to analyze call conversation: {e}")
        # Fallback - assume interested if we can't analyze
        return {
            "candidate_interested": True,
            "candidate_name": "Candidate",
            "rejection_reason": "",
            "summary": "Unable to analyze conversation",
            "confidence_score": 0.5
        }


async def analyze_resume_jd_match(resume_content: str, jd_payload: dict) -> dict:
    """
    Analyze resume-JD match using Gemini 2.5 Pro for detailed evaluation.
    
    Args:
        resume_content: Full text content of the resume
        jd_payload: Complete job description payload with all details
    
    Returns:
        Detailed analysis with scores, explanations, and recommendations
    """
    try:
        _init_vertex_ai()
        model = GenerativeModel("gemini-2.5-pro")
        
        # Get current date for accurate experience calculation
        from datetime import datetime
        current_date = datetime.now().strftime("%B %d, %Y")
        current_month_year = datetime.now().strftime("%B %Y")
        
        # Build comprehensive JD context
        jd_context = f"""
Job Title: {jd_payload.get('title', 'N/A')}

Job Description:
{jd_payload.get('description', 'N/A')}

Requirements:
{jd_payload.get('requirements', 'N/A')}

Required Skills: {', '.join(jd_payload.get('skills_required', []))}

Location: {jd_payload.get('location', 'N/A')}
Experience Required: {jd_payload.get('experience_required', 'N/A')}
Salary Range: {jd_payload.get('salary_range', 'N/A')}
Notice Period Acceptable: {jd_payload.get('notice_period_acceptable', 'N/A')}
"""
        
        prompt = f"""You are an expert technical recruiter and hiring manager. Analyze this candidate's resume against the job requirements and provide a comprehensive evaluation.

IMPORTANT CONTEXT FOR DATE CALCULATIONS:
- Today's date is: {current_date}
- Current month and year: {current_month_year}
- When you see "Current", "Present", or similar terms in employment dates, it means {current_month_year}
- Calculate experience duration ACCURATELY from start date to end date
- Example: "March 2024 - Current" means March 2024 to {current_month_year}, which is approximately {(datetime.now().year - 2024) * 12 + (datetime.now().month - 3)} months
- Do NOT flag ongoing employment as suspicious or claim it's "impossible"
- Verify that project durations fit within the employment period before raising concerns
- If the resume includes "[CALCULATED EXPERIENCE: X years]" at the top, this is the programmatically calculated total experience - use this as the ground truth

JOB DESCRIPTION:
{jd_context}

CANDIDATE RESUME:
{resume_content}

Perform a thorough analysis and provide your response in the following JSON format:

{{
    "overall_match_score": <float 0-100>,
    "final_recommendation": "<strong_match|moderate_match|weak_match>",
    "recommendation_action": "<proceed|maybe|reject>",
    
    "skills_analysis": {{
        "required_skills_matched": ["skill1", "skill2", ...],
        "required_skills_missing": ["skill1", "skill2", ...],
        "additional_relevant_skills": ["skill1", "skill2", ...],
        "skills_match_percentage": <float 0-100>
    }},
    
    "experience_analysis": {{
        "candidate_experience": "<summary>",
        "experience_match": "<excellent|good|partial|poor>",
        "relevant_projects": ["project1", "project2", ...],
        "explanation": "<detailed explanation>"
    }},
    
    "education_analysis": {{
        "education_match": "<excellent|good|adequate|poor>",
        "details": "<explanation>"
    }},
    
    "strengths": [
        "<specific strength 1>",
        "<specific strength 2>",
        ...
    ],
    
    "weaknesses": [
        "<specific weakness 1>",
        "<specific weakness 2>",
        ...
    ],
    
    "detailed_explanation": "<2-3 paragraphs explaining why this candidate is or isn't a good fit>",
    
    "key_highlights": [
        "<highlight 1>",
        "<highlight 2>",
        ...
    ],
    
    "concerns": [
        "<concern 1>",
        "<concern 2>",
        ...
    ],
    
    "interview_focus_areas": [
        "<area 1 to probe in interview>",
        "<area 2 to probe in interview>",
        ...
    ],
    
    "salary_expectation_alignment": "<likely_within_budget|needs_discussion|outside_budget>",
    
    "notice_period_concern": <boolean>,
    
    "location_match": "<perfect|acceptable|requires_relocation|mismatch>"
}}

IMPORTANT INSTRUCTIONS:
1. Be thorough and specific in your analysis
2. Match score should reflect actual fit based on resume content and job requirements
3. Consider both technical skills and soft skills/experience
4. Provide actionable insights for the recruiter
5. Base your evaluation purely on the provided resume and job description

CRITICAL - Experience Calculation Rules:
6. Use the current date context provided above to calculate experience accurately
7. When you see "Current" or "Present" in employment dates, use {current_month_year} as the end date
8. Calculate total months/years precisely using start and end dates
9. Do NOT flag ongoing employment as suspicious or impossible
10. Verify project durations fit within employment periods before raising timeline concerns
11. If a candidate has been employed from "March 2024 - Current", they have approximately {(datetime.now().year - 2024) * 12 + (datetime.now().month - 3)} months of experience
12. Only raise credibility concerns if there are actual mathematical impossibilities (e.g., project duration > employment duration)

13. Return ONLY valid JSON, no markdown or extra text"""

        response = model.generate_content(prompt)
        
        # Parse JSON response
        result_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.rsplit("```", 1)[0]
        
        analysis = json.loads(result_text)
        logger.info(f"Successfully analyzed resume-JD match with LLM. Score: {analysis.get('overall_match_score', 0)}")
        
        return analysis
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Raw response: {result_text[:500]}")
        # Return fallback response
        return {
            "overall_match_score": 50.0,
            "final_recommendation": "moderate_match",
            "recommendation_action": "maybe",
            "skills_analysis": {
                "required_skills_matched": [],
                "required_skills_missing": [],
                "additional_relevant_skills": [],
                "skills_match_percentage": 50.0
            },
            "experience_analysis": {
                "candidate_experience": "Unable to analyze",
                "experience_match": "unknown",
                "relevant_projects": [],
                "explanation": "LLM analysis failed, using fallback"
            },
            "education_analysis": {
                "education_match": "unknown",
                "details": "Unable to analyze"
            },
            "strengths": [],
            "weaknesses": ["Unable to perform detailed analysis"],
            "detailed_explanation": "Detailed LLM analysis failed. Please review manually.",
            "key_highlights": [],
            "concerns": ["Automated analysis incomplete"],
            "interview_focus_areas": [],
            "salary_expectation_alignment": "needs_discussion",
            "notice_period_concern": False,
            "location_match": "unknown"
        }
    except Exception as e:
        logger.error(f"Failed to analyze resume-JD match: {e}")
        raise
