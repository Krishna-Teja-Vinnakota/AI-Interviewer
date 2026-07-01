"""Interview service for question generation and flow management."""
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import get_database
from core.models import InterviewModel, QuestionModel, AnswerModel
from services.ai_service import generate_questions
from datetime import datetime


async def generate_interview_questions(jd_id: str, resume_id: str, num_questions: int = 10) -> List[Dict[str, Any]]:
    """Generate interview questions based on JD and resume."""
    from services.jd_service import get_jd_by_id
    db = get_database()
    
    # Get JD from MongoDB
    jd = await get_jd_by_id(jd_id)
    if not jd:
        raise ValueError("JD not found")
    
    # Get resume from MongoDB
    resume = await db.resumes.find_one({"_id": ObjectId(resume_id)})
    if not resume:
        raise ValueError("Resume not found")
    
    # Build context
    jd_text = f"{jd.get('title', '')}\n{jd.get('description', '')}\n{jd.get('requirements', '')}"
    resume_text = resume.get("parsed_content", "")
    
    # Generate questions using AI (returns list of dicts with 'text' and 'source')
    question_data_list = await generate_questions(jd_text, resume_text, num_questions)
    
    # Create question objects with source information
    questions = []
    for i, q_data in enumerate(question_data_list):
        question = {
            "question_id": str(ObjectId()),
            "text": q_data.get("text", q_data) if isinstance(q_data, dict) else q_data,
            "order": i + 1,
            "question_type": q_data.get("source", "general") if isinstance(q_data, dict) else "general",
            "source": q_data.get("source", "general") if isinstance(q_data, dict) else "general"
        }
        questions.append(question)
    
    return questions


async def create_interview(candidate_id: str, jd_id: str, resume_id: str) -> Dict[str, Any]:
    """Create a new interview session."""
    from core.config import settings
    db = get_database()
    
    # Generate questions
    questions = await generate_interview_questions(jd_id, resume_id)
    
    # Create interview document
    interview_doc = InterviewModel(
        candidate_id=ObjectId(candidate_id),
        jd_id=ObjectId(jd_id),
        questions=questions,
        status="scheduled"
    )
    
    result = await db.interviews.insert_one(
        interview_doc.model_dump(by_alias=True, exclude={"interview_id"})
    )
    
    interview_id = str(result.inserted_id)
    interview_link = f"{settings.BASE_URL}/interview.html?id={interview_id}"
    
    # Update interview with link
    await db.interviews.update_one(
        {"_id": result.inserted_id},
        {"$set": {"interview_link": interview_link}}
    )
    
    return {
        "interview_id": interview_id,
        "interview_link": interview_link,
        "questions": questions
    }


async def start_interview(interview_id: str) -> Dict[str, Any]:
    """Start interview session."""
    db = get_database()
    
    await db.interviews.update_one(
        {"_id": ObjectId(interview_id)},
        {
            "$set": {
                "status": "in_progress",
                "started_at": datetime.utcnow(),
                "current_question_index": 0
            }
        }
    )
    
    interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
    
    return {
        "message": "Interview started",
        "current_question_index": interview.get("current_question_index", 0),
        "questions": interview.get("questions", [])
    }


async def get_current_question(interview_id: str) -> Dict[str, Any]:
    """Get current question for interview."""
    db = get_database()
    
    interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
    if not interview:
        raise ValueError("Interview not found")
    
    questions = interview.get("questions", [])
    current_index = interview.get("current_question_index", 0)
    
    if current_index >= len(questions):
        return None
    
    current_question = questions[current_index]
    return {
        "question_id": current_question.get("question_id"),
        "text": current_question.get("text"),
        "order": current_question.get("order"),
        "question_index": current_index
    }


async def submit_answer(interview_id: str, transcription: str) -> Dict[str, Any]:
    """Submit answer for current question."""
    db = get_database()
    
    interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
    if not interview:
        raise ValueError("Interview not found")
    
    questions = interview.get("questions", [])
    current_index = interview.get("current_question_index", 0)
    
    if current_index >= len(questions):
        raise ValueError("No more questions")
    
    current_question = questions[current_index]
    
    # Create answer document
    answer_doc = AnswerModel(
        question_id=ObjectId(current_question.get("question_id")),
        interview_id=ObjectId(interview_id),
        transcription=transcription
    )
    
    result = await db.answers.insert_one(
        answer_doc.model_dump(by_alias=True, exclude={"answer_id"})
    )
    
    # Move to next question after saving answer
    await db.interviews.update_one(
        {"_id": ObjectId(interview_id)},
        {"$inc": {"current_question_index": 1}}
    )
    
    return {
        "answer_id": str(result.inserted_id),
        "message": "Answer saved successfully"
    }


async def move_to_next_question(interview_id: str) -> Dict[str, Any]:
    """Move to next question."""
    db = get_database()
    
    interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
    if not interview:
        raise ValueError("Interview not found")
    
    questions = interview.get("questions", [])
    current_index = interview.get("current_question_index", 0)
    
    # Move to next question
    next_index = current_index + 1
    
    if next_index >= len(questions):
        # Interview completed
        await db.interviews.update_one(
            {"_id": ObjectId(interview_id)},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.utcnow()
                }
            }
        )
        return None
    
    await db.interviews.update_one(
        {"_id": ObjectId(interview_id)},
        {"$set": {"current_question_index": next_index}}
    )
    
    next_question = questions[next_index]
    return {
        "current_question_index": next_index,
        "question": next_question
    }


async def complete_interview(interview_id: str, auto_submitted: bool = False, auto_submit_reason: Optional[str] = None) -> Dict[str, Any]:
    """Mark interview as complete."""
    db = get_database()
    
    update_data = {
        "status": "completed",
        "completed_at": datetime.utcnow()
    }
    
    if auto_submitted:
        update_data["auto_submitted"] = True
        update_data["auto_submit_reason"] = auto_submit_reason
    
    await db.interviews.update_one(
        {"_id": ObjectId(interview_id)},
        {"$set": update_data}
    )
    
    return {
        "message": "Interview completed successfully" if not auto_submitted else "Interview auto-submitted",
        "interview_id": interview_id,
        "auto_submitted": auto_submitted,
        "auto_submit_reason": auto_submit_reason
    }
