"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# Resume Schemas
class ResumeUploadRequest(BaseModel):
    """Request schema for resume upload."""
    candidate_name: Optional[str] = None
    candidate_email: Optional[EmailStr] = None
    candidate_phone: Optional[str] = None


class ResumeResponse(BaseModel):
    """Response schema for resume."""
    resume_id: str
    candidate_id: Optional[str] = None
    parsed_content: str
    uploaded_at: datetime


class ResumeListResponse(BaseModel):
    """Response schema for resume list."""
    resume_id: str
    candidate_name: Optional[str] = None
    uploaded_at: datetime


# Job Description Schemas
class JDCreateRequest(BaseModel):
    """Request schema for creating JD."""
    title: str
    description: str
    requirements: str
    skills: List[str] = []
    location: Optional[str] = None
    experience_required: Optional[str] = None
    salary_range: Optional[str] = None
    notice_period_acceptable: Optional[str] = None


class JDUpdateRequest(BaseModel):
    """Request schema for updating JD."""
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    skills: Optional[List[str]] = None
    location: Optional[str] = None
    experience_required: Optional[str] = None
    salary_range: Optional[str] = None
    notice_period_acceptable: Optional[str] = None


class JDResponse(BaseModel):
    """Response schema for JD."""
    jd_id: str
    title: str
    description: str
    requirements: str
    skills: List[str]
    location: Optional[str] = None
    experience_required: Optional[str] = None
    salary_range: Optional[str] = None
    notice_period_acceptable: Optional[str] = None
    created_at: datetime


class JDListResponse(BaseModel):
    """Response schema for JD list."""
    jd_id: str
    title: str
    created_at: datetime


# Matching Schemas
class MatchRequest(BaseModel):
    """Request schema for resume-JD matching."""
    jd_id: str


class MatchResponse(BaseModel):
    """Response schema for matching result."""
    match_score: float
    is_match: bool
    recommendation: str  # proceed, maybe, reject
    
    # Detailed analysis from LLM
    overall_match_score: float
    final_recommendation: str
    
    skills_analysis: Dict[str, Any]
    experience_analysis: Dict[str, Any]
    education_analysis: Dict[str, Any]
    
    strengths: List[str]
    weaknesses: List[str]
    detailed_explanation: str
    
    key_highlights: List[str]
    concerns: List[str]
    interview_focus_areas: List[str]
    
    salary_expectation_alignment: str
    notice_period_concern: bool
    location_match: str
    
    # Legacy fields for backwards compatibility
    analysis: str
    
    # Generated questions for interview
    generated_questions: List[Dict[str, Any]] = []
    
    # Screening result ID (saved in DB)
    screening_id: Optional[str] = None


# Candidate Schemas
class CandidateResponse(BaseModel):
    """Response schema for candidate."""
    candidate_id: str
    name: str
    phone: str
    email: Optional[str] = None
    resume_id: Optional[str] = None


class CandidateListResponse(BaseModel):
    """Response schema for candidate list."""
    candidate_id: str
    name: str
    phone: str
    email: Optional[str] = None


# Interview Schemas
class InterviewResponse(BaseModel):
    """Response schema for interview."""
    interview_id: str
    candidate_id: Optional[str] = None
    candidate_name: Optional[str] = None
    jd_id: str
    status: str
    scheduled_time: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    questions: List[Dict[str, Any]] = []
    current_question_index: int = 0
    total_answers: int = 0
    video_url: Optional[str] = None
    video_size: Optional[int] = None
    video_uploaded_at: Optional[datetime] = None
    auto_submitted: bool = False
    auto_submit_reason: Optional[str] = None


class InterviewListResponse(BaseModel):
    """Response schema for interview list."""
    interview_id: str
    candidate_name: Optional[str] = None
    status: str
    scheduled_time: Optional[datetime] = None


class StartInterviewResponse(BaseModel):
    """Response schema for starting interview."""
    message: str
    current_question_index: int
    questions: List[Dict[str, Any]] = []


class QuestionResponse(BaseModel):
    """Response schema for question."""
    question_id: str
    text: str
    order: int
    question_index: int


class QuestionsResponse(BaseModel):
    """Response schema for questions list."""
    questions: List[Dict[str, Any]]


class AnswerRequest(BaseModel):
    """Request schema for submitting answer."""
    transcription: str


class AnswerResponse(BaseModel):
    """Response schema for answer submission."""
    answer_id: str
    message: str


class NextQuestionResponse(BaseModel):
    """Response schema for next question."""
    current_question_index: int
    question: Dict[str, Any]


class CompleteInterviewResponse(BaseModel):
    """Response schema for completing interview."""
    message: str
    interview_id: str
    auto_submitted: bool = False
    auto_submit_reason: Optional[str] = None


# Analysis Schemas
class AnalyzeResponse(BaseModel):
    """Response schema for analysis trigger."""
    analysis_id: str
    message: str
    status: str


class AnalysisResultsResponse(BaseModel):
    """Response schema for analysis results."""
    overall_score: float
    recommendation: str
    status: str
    analyzed_at: Optional[datetime] = None


class AnalysisReportResponse(BaseModel):
    """Response schema for detailed analysis report."""
    overall_score: float
    recommendation: str
    strengths: List[str]
    weaknesses: List[str]
    question_analysis: List[Dict[str, Any]]
    analyzed_at: Optional[datetime] = None


# Health Check Schema
class HealthResponse(BaseModel):
    """Response schema for health check."""
    status: str
    timestamp: datetime
