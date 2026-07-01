"""All API routes for the AI Interview System."""
import logging
import re
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, Response
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

from core.database import get_database
from core.schemas import *
from services.resume_service import upload_resume, match_resume_with_jd
from services.interview_service import (
    create_interview, start_interview, get_current_question,
    submit_answer, move_to_next_question, complete_interview
)
from services.analysis_service import analyze_interview_session, get_analysis_results, get_analysis_report
from services.bunny_service import bunny_service
from utils.timezone import convert_to_ist

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["api"])


# Helper functions
def validate_pdf(file: UploadFile) -> bool:
    """Validate PDF file."""
    return file.content_type == "application/pdf" and file.filename.endswith(".pdf")


async def read_file_content(file: UploadFile) -> bytes:
    """Read file content."""
    return await file.read()


# ==================== Resume Management ====================

@router.post("/resumes/upload", response_model=dict)
async def upload_resume_endpoint(
    file: UploadFile = File(...),
    candidate_name: Optional[str] = Form(None),
    candidate_email: Optional[str] = Form(None),
    candidate_phone: Optional[str] = Form(None)
):
    """Upload resume PDF file."""
    if not validate_pdf(file):
        raise HTTPException(status_code=400, detail="Invalid PDF file")
    
    file_content = await read_file_content(file)
    result = await upload_resume(file_content, candidate_name, candidate_email, candidate_phone)
    
    return {
        "resume_id": result["resume_id"],
        "candidate_id": result.get("candidate_id"),
        "message": "Resume uploaded successfully"
    }


@router.get("/resumes/{resume_id}", response_model=ResumeResponse)
async def get_resume(resume_id: str):
    """Get resume details."""
    try:
        db = get_database()
        resume = await db.resumes.find_one({"_id": ObjectId(resume_id)})
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        return ResumeResponse(
            resume_id=str(resume["_id"]),
            candidate_id=str(resume["candidate_id"]) if resume.get("candidate_id") else None,
            parsed_content=resume.get("parsed_content", ""),
            uploaded_at=resume.get("uploaded_at")
        )
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid resume ID")


@router.get("/resumes", response_model=List[ResumeListResponse])
async def list_resumes():
    """List all resumes."""
    db = get_database()
    resumes = await db.resumes.find().to_list(length=None)
    
    result = []
    for resume in resumes:
        candidate_name = None
        if resume.get("candidate_id"):
            candidate = await db.candidates.find_one({"_id": resume["candidate_id"]})
            candidate_name = candidate.get("name") if candidate else None
        
        result.append(ResumeListResponse(
            resume_id=str(resume["_id"]),
            candidate_name=candidate_name,
            uploaded_at=resume.get("uploaded_at")
        ))
    
    return result


# ==================== Job Description Management ====================

@router.post("/jds", response_model=dict)
async def create_jd(request: JDCreateRequest):
    """Create new job description."""
    from services.jd_service import create_jd as create_jd_service
    
    # Create JD in MongoDB
    jd_id = await create_jd_service(
        title=request.title,
        description=request.description,
        requirements=request.requirements,
        skills=request.skills,
        location=request.location,
        experience_required=request.experience_required,
        salary_range=request.salary_range,
        notice_period_acceptable=request.notice_period_acceptable
    )
    
    logger.info(f"Created JD {jd_id} in MongoDB")
    return {"jd_id": jd_id, "message": "JD created successfully"}


@router.get("/jds", response_model=List[JDListResponse])
async def list_jds():
    """List all job descriptions."""
    from services.jd_service import get_all_jds
    
    jds = await get_all_jds()
    
    return [JDListResponse(
        jd_id=jd["jd_id"],
        title=jd.get("title", ""),
        created_at=jd.get("created_at", datetime.utcnow())
    ) for jd in jds]


@router.get("/jds/{jd_id}", response_model=JDResponse)
async def get_jd(jd_id: str):
    """Get specific JD details."""
    try:
        from services.jd_service import get_jd_by_id
        
        jd = await get_jd_by_id(jd_id)
        if not jd:
            raise HTTPException(status_code=404, detail="JD not found")
        
        return JDResponse(
            jd_id=jd["jd_id"],
            title=jd.get("title", ""),
            description=jd.get("description", ""),
            requirements=jd.get("requirements", ""),
            skills=jd.get("skills_required", []),
            location=jd.get("location"),
            experience_required=jd.get("experience_required"),
            salary_range=jd.get("salary_range"),
            notice_period_acceptable=jd.get("notice_period_acceptable"),
            created_at=jd.get("created_at", datetime.utcnow())
        )
    except Exception as e:
        logger.error(f"Error getting JD: {e}")
        raise HTTPException(status_code=404, detail="JD not found")


@router.put("/jds/{jd_id}")
async def update_jd(jd_id: str, request: JDUpdateRequest):
    """Update job description."""
    try:
        from services.jd_service import update_jd as update_jd_service
        
        # Update JD in MongoDB
        success = await update_jd_service(
            jd_id=jd_id,
            title=request.title,
            description=request.description,
            requirements=request.requirements,
            skills=request.skills,
            location=request.location,
            experience_required=request.experience_required,
            salary_range=request.salary_range,
            notice_period_acceptable=request.notice_period_acceptable
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="JD not found")
        
        logger.info(f"Updated JD {jd_id} in MongoDB")
        return {"message": "JD updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating JD: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jds/{jd_id}")
async def delete_jd(jd_id: str):
    """Delete job description."""
    try:
        from services.jd_service import delete_jd as delete_jd_service
        
        # Delete from MongoDB
        success = await delete_jd_service(jd_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="JD not found")
        
        logger.info(f"Deleted JD {jd_id} from MongoDB")
        return {"message": "JD deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting JD: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Resume-JD Matching ====================

@router.post("/resumes/{resume_id}/match", response_model=MatchResponse)
async def match_resume(resume_id: str, request: MatchRequest):
    """Match resume with a job description."""
    try:
        # Get file name from resume
        db = get_database()
        resume = await db.resumes.find_one({"_id": ObjectId(resume_id)})
        file_name = "resume.pdf"  # Default name
        
        if resume and resume.get("candidate_id"):
            candidate = await db.candidates.find_one({"_id": resume["candidate_id"]})
            if candidate and candidate.get("name"):
                file_name = f"{candidate['name']}-Resume.pdf"
        
        result = await match_resume_with_jd(resume_id, request.jd_id, file_name)
        return MatchResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")


# ==================== Screening Results Management ====================

@router.get("/screening-results")
async def list_screening_results(jd_id: Optional[str] = Query(None), status: Optional[str] = Query(None)):
    """List all screening results with optional filters."""
    db = get_database()
    query = {}
    
    if jd_id:
        query["jd_id"] = jd_id
    if status:
        query["status"] = status
    
    results = await db.screening_results.find(query).sort("created_at", -1).to_list(length=None)
    
    # Enrich with candidate and JD info
    enriched_results = []
    for result in results:
        candidate_name = None
        if result.get("candidate_id"):
            candidate = await db.candidates.find_one({"_id": result["candidate_id"]})
            if candidate:
                candidate_name = candidate.get("name")
        
        enriched_results.append({
            "screening_id": str(result["_id"]),
            "file_name": result.get("file_name", "Unknown"),
            "candidate_name": candidate_name,
            "jd_id": result.get("jd_id"),
            "overall_match_score": result.get("overall_match_score", 0),
            "final_recommendation": result.get("final_recommendation"),
            "recommendation_action": result.get("recommendation_action"),
            "status": result.get("status", "pending"),
            "created_at": result.get("created_at"),
            "face_verification_enabled": result.get("face_verification_enabled", False)
        })
    
    return enriched_results


@router.get("/screening-results/{screening_id}")
async def get_screening_result(screening_id: str):
    """Get detailed screening result."""
    try:
        db = get_database()
        result = await db.screening_results.find_one({"_id": ObjectId(screening_id)})
        if not result:
            raise HTTPException(status_code=404, detail="Screening result not found")
        
        # Convert ObjectIds to strings
        result["screening_id"] = str(result.pop("_id"))
        result["resume_id"] = str(result.get("resume_id"))
        if result.get("candidate_id"):
            result["candidate_id"] = str(result["candidate_id"])
        
        return result
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid screening ID")


@router.delete("/screening-results/{screening_id}")
async def delete_screening_result(screening_id: str):
    """Delete a screening result."""
    try:
        db = get_database()
        result = await db.screening_results.delete_one({"_id": ObjectId(screening_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Screening result not found")
        
        logger.info(f"Deleted screening result: {screening_id}")
        return {"message": "Screening result deleted successfully"}
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid screening ID")


@router.post("/screening-results/{screening_id}/upload-reference-photo")
async def upload_reference_photo(screening_id: str, file: UploadFile = File(...)):
    """Upload candidate reference photo for face verification during interview."""
    try:
        db = get_database()

        # Validate screening exists
        try:
            oid = ObjectId(screening_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid screening ID")

        screening = await db.screening_results.find_one({"_id": oid})
        if not screening:
            raise HTTPException(status_code=404, detail="Screening result not found")

        # Validate file type (images only)
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WebP images are accepted")

        # Validate file size (max 5MB)
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image size must be under 5MB")

        # Store photo in GridFS
        import gridfs
        from motor.motor_asyncio import AsyncIOMotorGridFSBucket
        fs = AsyncIOMotorGridFSBucket(db)
        file_id = await fs.upload_from_stream(
            file.filename or "reference_photo.jpg",
            content,
            metadata={"content_type": file.content_type, "screening_id": screening_id}
        )

        # Save reference to screening result
        await db.screening_results.update_one(
            {"_id": oid},
            {"$set": {
                "reference_photo_id": file_id,
                "face_verification_enabled": True,
                "reference_photo_uploaded_at": datetime.utcnow()
            }}
        )

        logger.info(f"Reference photo uploaded for screening {screening_id}: {file_id}")
        return {"success": True, "photo_id": str(file_id), "message": "Reference photo uploaded successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading reference photo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screening-results/{screening_id}/reference-photo")
async def get_reference_photo(screening_id: str):
    """Serve the reference photo for a screening result."""
    try:
        db = get_database()

        try:
            oid = ObjectId(screening_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid screening ID")

        screening = await db.screening_results.find_one({"_id": oid})
        if not screening:
            raise HTTPException(status_code=404, detail="Screening result not found")

        if not screening.get("reference_photo_id"):
            raise HTTPException(status_code=404, detail="No reference photo uploaded")

        from motor.motor_asyncio import AsyncIOMotorGridFSBucket
        fs = AsyncIOMotorGridFSBucket(db)
        grid_out = await fs.open_download_stream(screening["reference_photo_id"])
        content = await grid_out.read()
        content_type = grid_out.metadata.get("content_type", "image/jpeg") if grid_out.metadata else "image/jpeg"

        return Response(content=content, media_type=content_type)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving reference photo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screening-results/{screening_id}/proceed")
async def proceed_with_candidate(screening_id: str):
    """
    Simplified flow:
    1. Get screening result
    2. Extract email from resume
    3. Generate invitation code
    4. Send email with code
    5. Return success
    """
    import secrets
    import string
    from datetime import timedelta
    from core.models import InterviewInvitationModel
    
    try:
        db = get_database()
        
        # Get screening result
        screening = await db.screening_results.find_one({"_id": ObjectId(screening_id)})
        if not screening:
            raise HTTPException(status_code=404, detail="Screening result not found")
        
        logger.info(f"Proceeding with screening: {screening_id}")
        
        # Get resume
        resume_id = screening["resume_id"]
        if isinstance(resume_id, str):
            resume_id = ObjectId(resume_id)
        
        resume = await db.resumes.find_one({"_id": resume_id})
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found in database")
        
        # Extract email from resume
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, resume["parsed_content"])
        candidate_email = emails[0] if emails else None
        
        if not candidate_email:
            raise HTTPException(status_code=400, detail="Email not found in resume. Please ensure resume contains email address.")
        
        # Extract candidate name (first non-email line)
        candidate_name = "Candidate"
        lines = resume["parsed_content"].split('\n')
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 3 and len(line) < 50 and '@' not in line:
                candidate_name = line
                break
        
        # Get JD details
        from services.jd_service import get_jd_by_id
        jd = await get_jd_by_id(screening["jd_id"])
        jd_title = jd.get("title", "Position") if jd else "Position"
        
        # Generate unique 8-character invitation code
        invitation_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        
        # Create invitation record
        invitation = InterviewInvitationModel(
            invitation_code=invitation_code,
            screening_id=ObjectId(screening_id),
            resume_id=resume_id,
            jd_id=screening["jd_id"],
            candidate_id=screening.get("candidate_id"),
            candidate_email=candidate_email,
            status="sent",
            expires_at=datetime.utcnow() + timedelta(days=7)  # Valid for 7 days
        )
        
        # Save invitation to database
        result = await db.interview_invitations.insert_one(
            invitation.model_dump(by_alias=True, exclude={"invitation_id"})
        )
        
        # Send email with invitation code (MANDATORY - no fallback!)
        try:
            from services.email_service import send_interview_invitation_email
            await send_interview_invitation_email(
                candidate_email=candidate_email,
                candidate_name=candidate_name,
                invitation_code=invitation_code,
                jd_title=jd_title,
                expires_at=invitation.expires_at
            )
            logger.info(f"Email sent successfully to {candidate_email}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            # Delete the invitation since email failed (mandatory requirement)
            await db.interview_invitations.delete_one({"_id": result.inserted_id})
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to send email to {candidate_email}. Please configure SMTP settings in .env file. Error: {str(e)}"
            )
        
        # Update screening status (only if email sent successfully)
        await db.screening_results.update_one(
            {"_id": ObjectId(screening_id)},
            {"$set": {
                "status": "invited",
                "invitation_sent_at": datetime.utcnow(),
                "candidate_email": candidate_email,
                "candidate_name": candidate_name
            }}
        )
        
        logger.info(f"Invitation sent successfully for screening {screening_id}. Code: {invitation_code}")
        
        return {
            "success": True,
            "invitation_code": invitation_code,
            "candidate_email": candidate_email,
            "candidate_name": candidate_name,
            "jd_title": jd_title,
            "expires_at": invitation.expires_at,
            "message": "Invitation email sent successfully"
        }
        
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid screening ID")




@router.post("/invitations/verify")
async def verify_invitation_code(invitation_code: str = Query(...)):
    """Verify invitation code and return screening details."""
    db = get_database()
    
    logger.info(f"Verifying invitation code: {invitation_code}")
    
    invitation = await db.interview_invitations.find_one({"invitation_code": invitation_code})
    if not invitation:
        logger.error(f"Invitation code not found: {invitation_code}")
        raise HTTPException(status_code=404, detail="Invalid invitation code")
    
    logger.info(f"Found invitation: {invitation.get('_id')}")
    
    # Check if expired
    if invitation.get("expires_at") and invitation["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invitation code expired")
    
    # Update accessed_at
    await db.interview_invitations.update_one(
        {"_id": invitation["_id"]},
        {"$set": {"accessed_at": datetime.utcnow(), "status": "accessed"}}
    )
    
    # Get screening details
    screening_id = invitation["screening_id"]
    logger.info(f"Looking for screening_id: {screening_id} (type: {type(screening_id)})")
    
    if isinstance(screening_id, str):
        screening_id = ObjectId(screening_id)
    
    screening = await db.screening_results.find_one({"_id": screening_id})
    if not screening:
        logger.error(f"Screening result not found for ID: {screening_id}")
        # List all screening results for debugging
        all_screenings = await db.screening_results.find().to_list(100)
        logger.error(f"Available screening IDs: {[str(s['_id']) for s in all_screenings]}")
        raise HTTPException(status_code=404, detail="Screening result not found. Please contact the hiring team.")
    
    logger.info(f"Found screening result: {screening.get('_id')}")
    
    # Get JD details from MongoDB
    from services.jd_service import get_jd_by_id
    jd = await get_jd_by_id(screening["jd_id"])
    
    return {
        "invitation_code": invitation_code,
        "invitation_id": str(invitation["_id"]),
        "screening_id": str(screening["_id"]),
        "jd_title": jd.get("title") if jd else "Unknown",
        "jd_id": screening["jd_id"],
        "resume_id": str(screening["resume_id"]),
        "overall_match_score": screening.get("overall_match_score"),
        "generated_questions": screening.get("generated_questions", []),
        "interview_id": str(invitation["interview_id"]) if invitation.get("interview_id") else None,
        "face_verification_enabled": screening.get("face_verification_enabled", False)
    }


@router.post("/invitations/{invitation_code}/start-interview")
async def start_interview_from_invitation(invitation_code: str):
    """Create and start an interview session from invitation code."""
    db = get_database()
    
    logger.info(f"Starting interview for invitation code: {invitation_code}")
    
    # Get invitation
    invitation = await db.interview_invitations.find_one({"invitation_code": invitation_code})
    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid invitation code")
    
    # Check if expired
    if invitation.get("expires_at") and invitation["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invitation code expired")
    
    # Check if interview already exists and is completed - prevent retaking
    if invitation.get("interview_id"):
        existing_interview = await db.interviews.find_one({"_id": invitation["interview_id"]})
        if existing_interview:
            if existing_interview.get("status") == "completed":
                raise HTTPException(
                    status_code=400, 
                    detail="You have already completed this interview. Thank you for your participation."
                )
            logger.info(f"Interview already exists: {invitation['interview_id']}")
            return {
                "interview_id": str(invitation["interview_id"]),
                "message": "Interview session restored"
            }
    
    # Get screening result to get questions and candidate info
    screening_id = invitation["screening_id"]
    if isinstance(screening_id, str):
        screening_id = ObjectId(screening_id)
    
    screening = await db.screening_results.find_one({"_id": screening_id})
    if not screening:
        raise HTTPException(status_code=404, detail="Screening result not found")
    
    # Get resume to extract candidate name
    resume_id = invitation["resume_id"]
    if isinstance(resume_id, str):
        resume_id = ObjectId(resume_id)
    
    resume = await db.resumes.find_one({"_id": resume_id})
    candidate_name = screening.get("candidate_name") or invitation.get("candidate_email", "Candidate")
    candidate_email = invitation.get("candidate_email")
    
    # Extract candidate name from resume if available
    if resume and not screening.get("candidate_name"):
        lines = resume.get("parsed_content", "").split('\n')
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 3 and len(line) < 50 and '@' not in line:
                candidate_name = line
                break
    
    # Create or get candidate record
    candidate_id = invitation.get("candidate_id")
    if not candidate_id and candidate_email:
        # Try to find existing candidate by email
        existing_candidate = await db.candidates.find_one({"email": candidate_email})
        if existing_candidate:
            candidate_id = existing_candidate["_id"]
        else:
            # Create new candidate
            from core.models import CandidateModel
            candidate_doc = CandidateModel(
                name=candidate_name,
                email=candidate_email,
                phone="",  # Not available from invitation
                resume_id=resume_id
            )
            cand_result = await db.candidates.insert_one(
                candidate_doc.model_dump(by_alias=True, exclude={"candidate_id"})
            )
            candidate_id = cand_result.inserted_id
            
            # Update invitation with candidate_id
            await db.interview_invitations.update_one(
                {"_id": invitation["_id"]},
                {"$set": {"candidate_id": candidate_id}}
            )
    
    # Use generated questions from screening if available, otherwise generate new ones
    questions = []
    if screening.get("generated_questions"):
        for i, q in enumerate(screening["generated_questions"]):
            # q may be a dict {"text": "...", "source": "..."} or a plain string
            if isinstance(q, dict):
                q_text = q.get("text", "")
                q_source = q.get("source", "")
            else:
                q_text = str(q)
                q_source = ""
            questions.append({
                "question_id": str(ObjectId()),
                "text": q_text,
                "source": q_source,
                "order": i + 1,
                "question_type": "technical" if i < len(screening["generated_questions"]) * 0.6 else "behavioral"
            })
    else:
        # Generate questions using the interview service
        from services.interview_service import generate_interview_questions
        questions = await generate_interview_questions(
            screening["jd_id"], 
            str(resume_id),
            num_questions=10
        )
    
    # Create interview with proper candidate info
    interview_doc = {
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "jd_id": screening["jd_id"],
        "resume_id": resume_id,
        "screening_id": screening_id,
        "invitation_code": invitation_code,
        "questions": questions,
        "status": "scheduled",
        "current_question_index": 0,
        "created_at": datetime.utcnow(),
        "scheduled_time": datetime.utcnow()
    }
    
    result = await db.interviews.insert_one(interview_doc)
    interview_id = str(result.inserted_id)
    
    # Update invitation with interview_id
    await db.interview_invitations.update_one(
        {"_id": invitation["_id"]},
        {"$set": {
            "interview_id": result.inserted_id,
            "status": "interview_started"
        }}
    )
    
    logger.info(f"Created interview {interview_id} for invitation {invitation_code}")
    
    return {
        "interview_id": interview_id,
        "message": "Interview session created successfully"
    }


# ==================== Interview Management ====================

@router.get("/interviews", response_model=List[InterviewListResponse])
async def list_interviews(status: Optional[str] = Query(None)):
    """List all interviews."""
    db = get_database()
    query = {}
    if status:
        query["status"] = status
    
    interviews = await db.interviews.find(query).sort("created_at", -1).to_list(length=None)
    
    result = []
    for interview in interviews:
        candidate_name = interview.get("candidate_name")
        
        # Try to get candidate name from candidate_id if not in interview doc
        if not candidate_name and interview.get("candidate_id"):
            candidate = await db.candidates.find_one({"_id": interview["candidate_id"]})
            candidate_name = candidate.get("name") if candidate else None
        
        # Use scheduled_time, started_at, or created_at for date display
        interview_date = interview.get("completed_at") or interview.get("started_at") or interview.get("scheduled_time") or interview.get("created_at")
        
        result.append(InterviewListResponse(
            interview_id=str(interview["_id"]),
            candidate_name=candidate_name,
            status=interview.get("status", "scheduled"),
            scheduled_time=interview_date
        ))
    
    return result


@router.get("/interviews/{interview_id}", response_model=InterviewResponse)
async def get_interview(interview_id: str):
    """Get interview details."""
    try:
        db = get_database()
        interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Get candidate name if not in interview doc
        candidate_name = interview.get("candidate_name")
        if not candidate_name and interview.get("candidate_id"):
            candidate = await db.candidates.find_one({"_id": interview["candidate_id"]})
            candidate_name = candidate.get("name") if candidate else None
        
        # Get all answers for this interview
        answers = await db.answers.find({"interview_id": ObjectId(interview_id)}).to_list(length=None)
        
        return InterviewResponse(
            interview_id=str(interview["_id"]),
            candidate_id=str(interview["candidate_id"]) if interview.get("candidate_id") else None,
            candidate_name=candidate_name,
            jd_id=str(interview["jd_id"]),
            status=interview.get("status", "scheduled"),
            scheduled_time=interview.get("scheduled_time"),
            started_at=interview.get("started_at"),
            completed_at=interview.get("completed_at"),
            questions=interview.get("questions", []),
            current_question_index=interview.get("current_question_index", 0),
            total_answers=len(answers),
            video_url=interview.get("video_url"),
            video_size=interview.get("video_size"),
            video_uploaded_at=interview.get("video_uploaded_at"),
            auto_submitted=interview.get("auto_submitted", False),
            auto_submit_reason=interview.get("auto_submit_reason")
        )
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid interview ID")


@router.post("/interviews/{interview_id}/start", response_model=StartInterviewResponse)
async def start_interview_endpoint(interview_id: str):
    """Start interview session."""
    try:
        result = await start_interview(interview_id)
        return StartInterviewResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid interview ID")


@router.get("/interviews/{interview_id}/questions", response_model=QuestionsResponse)
async def get_questions(interview_id: str):
    """Get all interview questions."""
    try:
        db = get_database()
        interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        return QuestionsResponse(questions=interview.get("questions", []))
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid interview ID")


@router.get("/interviews/{interview_id}/questions/current", response_model=QuestionResponse)
async def get_current_question_endpoint(interview_id: str):
    """Get current question."""
    try:
        question = await get_current_question(interview_id)
        if not question:
            raise HTTPException(status_code=404, detail="No more questions")
        return QuestionResponse(**question)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid interview ID")


@router.post("/interviews/{interview_id}/answer", response_model=AnswerResponse)
async def submit_answer_endpoint(
    interview_id: str,
    transcription: str = Form(...),
    audio_file: Optional[UploadFile] = File(None)
):
    """Submit answer for current question."""
    try:
        audio_file_id = None
        if audio_file and validate_audio(audio_file):
            from services.media_service import upload_audio_chunk
            audio_content = await read_file_content(audio_file)
            result = await upload_audio_chunk(interview_id, audio_content, datetime.utcnow())
            audio_file_id = ObjectId(result["file_id"])
        
        result = await submit_answer(interview_id, transcription, audio_file_id)
        return AnswerResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid interview ID")


@router.post("/interviews/{interview_id}/next", response_model=NextQuestionResponse)
async def next_question(interview_id: str):
    """Move to next question."""
    try:
        result = await move_to_next_question(interview_id)
        if not result:
            raise HTTPException(status_code=404, detail="Interview completed")
        return NextQuestionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid interview ID")


@router.post("/interviews/{interview_id}/complete", response_model=CompleteInterviewResponse)
async def complete_interview_endpoint(interview_id: str, request: Request):
    """Mark interview as complete."""
    try:
        # Get request body
        body = {}
        try:
            if request.headers.get('content-type') == 'application/json':
                body = await request.json()
        except Exception:
            pass  # If body parsing fails, use defaults
        
        auto_submitted = body.get('auto_submitted', False)
        auto_submit_reason = body.get('auto_submit_reason', None)
        
        result = await complete_interview(interview_id, auto_submitted, auto_submit_reason)
        return CompleteInterviewResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid interview ID")


# ==================== Interview Configuration ====================

@router.get("/config/deepgram-key")
async def get_deepgram_key():
    """Get Deepgram API key for frontend."""
    from core.config import settings
    return {"api_key": settings.DEEPGRAM_API_KEY}


@router.post("/interviews/{interview_id}/submit-answer")
async def submit_answer_endpoint(
    interview_id: str,
    answer_request: AnswerRequest
):
    """Submit answer with transcription."""
    result = await submit_answer(
        interview_id, 
        answer_request.transcription
    )
    
    return {
        "answer_id": result["answer_id"],
        "message": "Answer saved successfully"
    }


@router.post("/interviews/{interview_id}/upload-video")
async def upload_interview_video(
    interview_id: str,
    video_file: UploadFile = File(...)
):
    """Upload complete interview video to Bunny CDN."""
    
    try:
        video_content = await video_file.read()
        
        result = await bunny_service.upload_video(video_content, interview_id)
        
        db = get_database()
        await db.interviews.update_one(
            {"_id": ObjectId(interview_id)},
            {
                "$set": {
                    "video_url": result["cdn_url"],
                    "video_size": result["size_bytes"],
                    "video_uploaded_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Video uploaded for interview {interview_id}")
        
        return {
            "success": True,
            "video_url": result["cdn_url"],
            "message": "Video uploaded successfully"
        }
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Analysis & Results ====================

@router.post("/interviews/{interview_id}/analyze", response_model=AnalyzeResponse)
async def analyze_interview_endpoint(interview_id: str, force: bool = Query(False, description="Force re-analysis even if one exists")):
    """Trigger analysis of interview."""
    try:
        db = get_database()
        
        # Check if analysis already exists (with robust query)
        existing_analysis = None
        try:
            existing_analysis = await db.analysis_results.find_one(
                {"interview_id": ObjectId(interview_id)},
                sort=[("created_at", -1)]
            )
            if not existing_analysis:
                existing_analysis = await db.analysis_results.find_one(
                    {"interview_id": ObjectId(interview_id)}
                )
        except Exception as e:
            logger.warning(f"Error checking for existing analysis: {e}")
        
        # If force is True, delete existing analysis and create new one
        if force and existing_analysis:
            logger.info(f"Force re-analysis requested, deleting existing analysis for interview {interview_id}")
            await db.analysis_results.delete_many({"interview_id": ObjectId(interview_id)})
            existing_analysis = None
        
        if existing_analysis and existing_analysis.get("status") == "completed":
            logger.info(f"Analysis already exists for interview {interview_id}")
            return AnalyzeResponse(
                analysis_id=str(existing_analysis["_id"]),
                message="Analysis already completed",
                status="completed",
                overall_score=existing_analysis.get("overall_score"),
                recommendation=existing_analysis.get("recommendation")
            )
        
        # Check if analysis is in progress
        if existing_analysis and existing_analysis.get("status") == "processing":
            raise HTTPException(
                status_code=409, 
                detail="Analysis already in progress. Please wait a few minutes."
            )
        
        # Start new analysis
        result = await analyze_interview_session(interview_id)
        return AnalyzeResponse(**result)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid interview ID")
    except Exception as e:
        logger.error(f"Analysis error for interview {interview_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again later.")


@router.get("/interviews/{interview_id}/results", response_model=AnalysisResultsResponse)
async def get_results(interview_id: str):
    """Get analysis results."""
    try:
        result = await get_analysis_results(interview_id)
        return AnalysisResultsResponse(**result)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid interview ID")


@router.get("/interviews/{interview_id}/report", response_model=AnalysisReportResponse)
async def get_report(interview_id: str):
    """Get detailed evaluation report."""
    try:
        result = await get_analysis_report(interview_id)
        return AnalysisReportResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid interview ID")


# ==================== Candidate Management ====================

@router.get("/candidates", response_model=List[CandidateListResponse])
async def list_candidates():
    """List all candidates."""
    db = get_database()
    candidates = await db.candidates.find().to_list(length=None)
    
    return [CandidateListResponse(
        candidate_id=str(c["_id"]),
        name=c.get("name", ""),
        phone=c.get("phone", ""),
        email=c.get("email")
    ) for c in candidates]


@router.get("/candidates/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(candidate_id: str):
    """Get candidate details."""
    try:
        db = get_database()
        candidate = await db.candidates.find_one({"_id": ObjectId(candidate_id)})
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        return CandidateResponse(
            candidate_id=str(candidate["_id"]),
            name=candidate.get("name", ""),
            phone=candidate.get("phone", ""),
            email=candidate.get("email"),
            resume_id=str(candidate["resume_id"]) if candidate.get("resume_id") else None
        )
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid candidate ID")


# ==================== Health Check ====================

@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow()
    )
