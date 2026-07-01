"""MongoDB document models and schemas."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class PyObjectId(ObjectId):
    """Custom ObjectId for Pydantic v2."""
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        
        def validate_object_id(value):
            if isinstance(value, ObjectId):
                return value
            if isinstance(value, str):
                if ObjectId.is_valid(value):
                    return ObjectId(value)
                raise ValueError("Invalid ObjectId")
            raise ValueError("Invalid ObjectId")
        
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(validate_object_id),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )


# Resume Models
class ResumeModel(BaseModel):
    """Resume document model."""
    resume_id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    candidate_id: Optional[PyObjectId] = None
    file_id: Optional[ObjectId] = None  # GridFS file ID
    parsed_content: str = ""
    embeddings: Optional[List[float]] = None
    skills: List[str] = []
    experience_years: Optional[float] = None
    education: List[str] = []
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, PyObjectId: str}
    )


# Job Description Models
class JobDescriptionModel(BaseModel):
    """Job description document model."""
    jd_id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    title: str
    description: str
    requirements: str
    skills: List[str] = []
    location: Optional[str] = None
    experience_required: Optional[str] = None
    salary_range: Optional[str] = None
    notice_period_acceptable: Optional[str] = None
    embeddings: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, PyObjectId: str}
    )


# Candidate Models
class CandidateModel(BaseModel):
    """Candidate document model."""
    candidate_id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str
    email: Optional[str] = None
    phone: str
    resume_id: Optional[PyObjectId] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, PyObjectId: str}
    )


# Interview Models
class QuestionModel(BaseModel):
    """Interview question model."""
    question_id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    text: str
    order: int
    question_type: str = "technical"  # technical, behavioral, situational
    source: str = "general"  # jd, resume, behavioral, general
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, PyObjectId: str}
    )


class AnswerModel(BaseModel):
    """Candidate answer model."""
    answer_id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    question_id: PyObjectId
    interview_id: PyObjectId
    transcription: str = ""
    answered_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, PyObjectId: str}
    )


class InterviewModel(BaseModel):
    """Interview document model."""
    interview_id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    candidate_id: Optional[PyObjectId] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    jd_id: str  # Can be string (Qdrant ID) or ObjectId
    resume_id: Optional[PyObjectId] = None
    screening_id: Optional[PyObjectId] = None
    invitation_code: Optional[str] = None
    status: str = "scheduled"  # scheduled, in_progress, completed, cancelled
    scheduled_time: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_question_index: int = 0
    questions: List[Dict[str, Any]] = []  # List of question dicts
    interview_link: Optional[str] = None
    video_url: Optional[str] = None
    video_size: Optional[int] = None
    video_uploaded_at: Optional[datetime] = None
    auto_submitted: bool = False
    auto_submit_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, PyObjectId: str}
    )


# Analysis Models
class AnalysisResultModel(BaseModel):
    """Analysis result document model."""
    analysis_id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    interview_id: PyObjectId
    overall_score: float
    recommendation: str  # proceed, reject, maybe
    status: str = "processing"  # processing, completed, failed
    strengths: List[str] = []
    weaknesses: List[str] = []
    question_analysis: List[Dict[str, Any]] = []
    analyzed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, PyObjectId: str}
    )


# Screening Result Models
class ScreeningResultModel(BaseModel):
    """Screening result document model."""
    screening_id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    resume_id: PyObjectId
    jd_id: str  # JD ID from Qdrant
    candidate_id: Optional[PyObjectId] = None
    file_name: str
    
    # Scores
    semantic_similarity: float
    overall_match_score: float
    
    # Analysis
    final_recommendation: str  # strong_match, moderate_match, weak_match
    recommendation_action: str  # proceed, maybe, reject
    skills_analysis: Dict[str, Any] = {}
    experience_analysis: Dict[str, Any] = {}
    education_analysis: Dict[str, Any] = {}
    
    strengths: List[str] = []
    weaknesses: List[str] = []
    detailed_explanation: str = ""
    key_highlights: List[str] = []
    concerns: List[str] = []
    interview_focus_areas: List[str] = []
    
    # Additional factors
    salary_expectation_alignment: str = "unknown"
    notice_period_concern: bool = False
    location_match: str = "unknown"
    
    # Pre-generated questions for interview
    generated_questions: List[Dict[str, Any]] = []
    
    # Status
    status: str = "pending"  # pending, invited, interview_scheduled, rejected
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, PyObjectId: str}
    )


# Interview Invitation Models
class InterviewInvitationModel(BaseModel):
    """Interview invitation with unique code."""
    invitation_id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    invitation_code: str  # Unique code sent to candidate
    screening_id: PyObjectId  # Link to screening result
    resume_id: PyObjectId
    jd_id: str
    candidate_id: Optional[PyObjectId] = None
    candidate_email: Optional[str] = None
    
    # Status
    status: str = "sent"  # sent, accessed, interview_started, interview_completed, expired
    
    # Timestamps
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    accessed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Interview link (when created)
    interview_id: Optional[PyObjectId] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, PyObjectId: str}
    )
