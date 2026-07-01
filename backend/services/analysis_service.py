"""Analysis service for candidate evaluation."""
from typing import List, Dict, Any, Optional
from bson import ObjectId
from datetime import datetime
from core.database import get_database
from core.models import AnalysisResultModel
from services.ai_service import analyze_interview
import logging

logger = logging.getLogger(__name__)


async def analyze_interview_session(interview_id: str) -> Dict[str, Any]:
    """Analyze complete interview session - Q&A only."""
    db = get_database()
    
    interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
    if not interview:
        raise ValueError("Interview not found")
    
    questions = interview.get("questions", [])
    # Extract text from questions - handle both old string format and new dict format
    question_texts = []
    for q in questions:
        if isinstance(q, dict):
            question_texts.append(q.get("text", ""))
        else:
            question_texts.append(str(q))
    
    logger.info(f"Analyzing interview {interview_id} with {len(questions)} questions")
    
    # Query with string interview_id (not ObjectId) since answers collection stores it as string
    answers_cursor = db.answers.find({"interview_id": interview_id})
    answers_list = await answers_cursor.to_list(length=None)
    
    logger.info(f"Found {len(answers_list)} answers in database")
    
    answer_map = {}
    for answer in answers_list:
        # question_id is also stored as string in answers collection
        answer_qid = answer.get("question_id")
        answer_map[answer_qid] = answer
        logger.info(f"Answer has question_id: {answer_qid}, transcription length: {len(answer.get('transcription', ''))}")
    
    logger.info(f"Question IDs in questions array:")
    for i, q in enumerate(questions):
        q_id = q.get("question_id")  # Keep as-is (string)
        logger.info(f"  Q{i+1} question_id: {q_id}")
    
    answer_texts = []
    for q in questions:
        q_id = q.get("question_id")  # Keep as-is (string)
        answer = answer_map.get(q_id)
        if answer:
            transcription = answer.get("transcription", "")
            answer_texts.append(transcription if transcription.strip() else "[Question skipped by candidate]")
            logger.info(f"Q{len(answer_texts)}: Found answer with transcription length: {len(transcription)}")
        else:
            answer_texts.append("[Question skipped by candidate]")
            logger.info(f"Q{len(answer_texts)}: No answer found")
    
    logger.info(f"Sending to AI - Questions: {len(question_texts)}, Answers: {len(answer_texts)}")
    logger.info(f"Answer preview: {answer_texts[:2]}")  # Log first 2 answers
    
    # AI analysis - Q&A only, NO media processing
    analysis_result = await analyze_interview(question_texts, answer_texts)
    
    # Ensure answers included in question_analysis
    if "question_analysis" in analysis_result:
        for i, qa in enumerate(analysis_result["question_analysis"]):
            if i < len(answer_texts):
                qa["answer"] = answer_texts[i]
            if i < len(question_texts):
                qa["question"] = question_texts[i]
    else:
        analysis_result["question_analysis"] = [
            {
                "question": question_texts[i] if i < len(question_texts) else f"Question {i+1}",
                "answer": answer_texts[i] if i < len(answer_texts) else "",
                "score": 0.0,
                "feedback": "No analysis available"
            }
            for i in range(len(question_texts))
        ]
    
    analysis_doc = AnalysisResultModel(
        interview_id=ObjectId(interview_id),
        overall_score=analysis_result.get("overall_score", 5.0),
        recommendation=analysis_result.get("recommendation", "maybe"),
        status="completed",
        strengths=analysis_result.get("strengths", []),
        weaknesses=analysis_result.get("weaknesses", []),
        question_analysis=analysis_result.get("question_analysis", []),
        analyzed_at=datetime.utcnow()
    )
    
    doc_dict = analysis_doc.model_dump(by_alias=True, exclude={"analysis_id"})
    result = await db.analysis_results.insert_one(doc_dict)
    
    logger.info(f"Analysis completed: {result.inserted_id}")
    
    return {
        "analysis_id": str(result.inserted_id),
        "message": "Analysis completed successfully",
        "status": "completed",
        "overall_score": analysis_result.get("overall_score"),
        "recommendation": analysis_result.get("recommendation")
    }


async def get_analysis_results(interview_id: str) -> Dict[str, Any]:
    """Get analysis results for interview."""
    db = get_database()
    
    try:
        oid = ObjectId(interview_id)
    except Exception:
        oid = None
    
    # Try direct query
    analysis = None
    if oid:
        analysis = await db.analysis_results.find_one({"interview_id": oid})
    
    # Fallback: string format
    if not analysis:
        analysis = await db.analysis_results.find_one({"interview_id": interview_id})
    
    if not analysis:
        return {
            "overall_score": 0.0,
            "recommendation": "pending",
            "status": "pending",
            "analyzed_at": None
        }
    
    return {
        "overall_score": analysis.get("overall_score", 0.0),
        "recommendation": analysis.get("recommendation", "maybe"),
        "status": analysis.get("status", "processing"),
        "analyzed_at": analysis.get("analyzed_at")
    }


async def get_analysis_report(interview_id: str) -> Dict[str, Any]:
    """Get detailed analysis report."""
    db = get_database()
    
    try:
        oid = ObjectId(interview_id)
    except Exception:
        raise ValueError("Invalid interview ID format")
    
    # Try direct query first (most reliable)
    analysis = await db.analysis_results.find_one({"interview_id": oid})
    
    # Fallback: try with sort if needed
    if not analysis:
        try:
            analysis = await db.analysis_results.find_one(
                {"interview_id": oid},
                sort=[("_id", -1)]
            )
        except Exception:
            pass
    
    # Fallback: try string format
    if not analysis:
        analysis = await db.analysis_results.find_one({"interview_id": interview_id})
    
    if not analysis:
        raise ValueError("Analysis not found")
    
    return {
        "overall_score": analysis.get("overall_score", 0.0),
        "recommendation": analysis.get("recommendation", "maybe"),
        "strengths": analysis.get("strengths", []),
        "weaknesses": analysis.get("weaknesses", []),
        "question_analysis": analysis.get("question_analysis", []),
        "analyzed_at": analysis.get("analyzed_at")
    }
