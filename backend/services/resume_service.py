"""Resume parsing and matching service."""
import pdfplumber
import logging
from typing import Dict, Any
from bson import ObjectId
from core.database import get_database, get_gridfs
from core.models import ResumeModel, JobDescriptionModel, CandidateModel
from services.ai_service import generate_embeddings

logger = logging.getLogger(__name__)


async def parse_resume_pdf(file_content: bytes) -> Dict[str, Any]:
    """Parse PDF resume and extract text."""
    import io
    import re
    from datetime import datetime
    from dateutil import parser as date_parser
    
    pdf_file = io.BytesIO(file_content)
    
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    
    # Extract basic information (simplified - can be enhanced with NLP)
    lines = text.split('\n')
    skills = []
    experience_years = None
    education = []
    
    # Simple extraction logic (can be improved with NLP)
    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in ['skill', 'technology', 'proficient']):
            # Extract skills (simplified)
            pass
        if any(keyword in line_lower for keyword in ['education', 'degree', 'university']):
            education.append(line.strip())
    
    # Extract and calculate experience from employment dates
    experience_years = _extract_experience_years(text)
    
    return {
        "parsed_content": text,
        "skills": skills,
        "experience_years": experience_years,
        "education": education
    }


def _extract_experience_years(text: str) -> float:
    """
    Extract and calculate total years of experience from resume text.
    Only looks for employment dates, excludes education dates.
    """
    import re
    from datetime import datetime
    from dateutil import parser as date_parser
    
    try:
        # Split resume into sections to identify Experience section
        lines = text.split('\n')
        
        # Find the Experience section (between "Experience" and "Skills"/"Education")
        experience_section = []
        in_experience_section = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Start of experience section
            if line_lower in ['experience', 'work experience', 'professional experience', 'employment history']:
                in_experience_section = True
                continue
            
            # End of experience section (start of other sections)
            if in_experience_section and line_lower in ['education', 'skills', 'certifications', 'projects', 'summary']:
                break
            
            if in_experience_section:
                experience_section.append(line)
        
        # If no clear experience section found, look for employment indicators
        if not experience_section:
            # Look for lines with job titles followed by dates
            for i, line in enumerate(lines):
                # Skip education section explicitly
                if any(keyword in line.lower() for keyword in ['university', 'college', 'school', 'b.tech', 'bachelor', 'master', 'degree']):
                    continue
                
                # Look for employment indicators
                if any(keyword in line.lower() for keyword in ['engineer', 'developer', 'analyst', 'manager', 'consultant', 'specialist']):
                    # Check next few lines for dates
                    for j in range(i, min(i+5, len(lines))):
                        if re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|\d{4})\s*[-–—]\s*(Current|Present|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|\d{4})', lines[j], re.IGNORECASE):
                            experience_section.append(lines[j])
        
        # Now extract dates only from experience section
        experience_text = '\n'.join(experience_section)
        
        # Date patterns with month names (more specific for employment)
        date_patterns = [
            r'([A-Za-z]+\s+\d{4})\s*[-–—]\s*(Current|Present|[A-Za-z]+\s+\d{4})',
            r'([A-Za-z]{3}\s+\d{4})\s*[-–—]\s*(Current|Present|[A-Za-z]{3}\s+\d{4})',
        ]
        
        total_months = 0
        current_date = datetime.now()
        found_dates = []
        
        for pattern in date_patterns:
            matches = re.findall(pattern, experience_text, re.IGNORECASE)
            
            for match in matches:
                start_str, end_str = match
                
                try:
                    # Parse start date
                    start_date = date_parser.parse(start_str, fuzzy=True)
                    
                    # Parse end date
                    if end_str.lower() in ['current', 'present']:
                        end_date = current_date
                    else:
                        end_date = date_parser.parse(end_str, fuzzy=True)
                    
                    # Calculate months difference
                    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                    
                    # Sanity checks
                    if months > 0 and months < 600:  # Less than 50 years
                        # Avoid duplicates
                        date_key = f"{start_str}-{end_str}"
                        if date_key not in found_dates:
                            found_dates.append(date_key)
                            total_months += months
                            logger.info(f"Found employment period: {start_str} to {end_str} = {months} months")
                
                except Exception as e:
                    logger.debug(f"Could not parse date range: {start_str} - {end_str}: {e}")
                    continue
        
        if total_months > 0:
            experience_years = round(total_months / 12, 1)
            logger.info(f"Calculated total experience: {experience_years} years ({total_months} months)")
            return experience_years
        
        return None
    
    except Exception as e:
        logger.error(f"Error extracting experience years: {e}")
        return None


async def upload_resume(file_content: bytes, candidate_name: str = None, 
                       candidate_email: str = None, candidate_phone: str = None) -> Dict[str, Any]:
    """Upload and process resume."""
    db = get_database()
    gridfs = get_gridfs()
    
    # Parse resume
    parsed_data = await parse_resume_pdf(file_content)
    
    # Store file in GridFS
    import io
    file_stream = io.BytesIO(file_content)
    file_id = await gridfs.upload_from_stream(
        "resume.pdf",
        file_stream,
        metadata={"type": "resume"}
    )
    
    # Generate embeddings
    embeddings = await generate_embeddings(parsed_data["parsed_content"])
    
    # Create or find candidate
    candidate_id = None
    if candidate_phone:
        candidate = await db.candidates.find_one({"phone": candidate_phone})
        if candidate:
            candidate_id = candidate["_id"]
        else:
            candidate_doc = CandidateModel(
                name=candidate_name or "Unknown",
                email=candidate_email,
                phone=candidate_phone
            )
            result = await db.candidates.insert_one(candidate_doc.model_dump(by_alias=True, exclude={"candidate_id"}))
            candidate_id = result.inserted_id
    
    # Create resume document
    resume_doc = ResumeModel(
        candidate_id=ObjectId(candidate_id) if candidate_id else None,
        file_id=file_id,
        parsed_content=parsed_data["parsed_content"],
        embeddings=embeddings,
        skills=parsed_data["skills"],
        experience_years=parsed_data["experience_years"],
        education=parsed_data["education"]
    )
    
    result = await db.resumes.insert_one(resume_doc.model_dump(by_alias=True, exclude={"resume_id"}))
    
    return {
        "resume_id": str(result.inserted_id),
        "candidate_id": str(candidate_id) if candidate_id else None
    }


async def match_resume_with_jd(resume_id: str, jd_id: str, file_name: str = "resume.pdf") -> Dict[str, Any]:
    """Match resume with job description using LLM analysis only (no similarity search)."""
    from services.jd_service import get_jd_by_id
    from services.ai_service import analyze_resume_jd_match, generate_questions
    from core.models import ScreeningResultModel
    db = get_database()
    
    # Get resume from MongoDB
    resume = await db.resumes.find_one({"_id": ObjectId(resume_id)})
    if not resume:
        raise ValueError("Resume not found")
    
    # Get JD from MongoDB
    jd = await get_jd_by_id(jd_id)
    if not jd:
        raise ValueError("JD not found")
    
    # Build JD payload for LLM
    jd_payload = {
        "jd_id": jd["jd_id"],
        "title": jd.get("title", ""),
        "description": jd.get("description", ""),
        "requirements": jd.get("requirements", ""),
        "skills_required": jd.get("skills_required", []),
        "location": jd.get("location", ""),
        "experience_required": jd.get("experience_required", ""),
        "salary_range": jd.get("salary_range", ""),
        "notice_period_acceptable": jd.get("notice_period_acceptable", ""),
        "job_description": jd.get("job_description", "")
    }
    
    logger.info(f"Analyzing resume {resume_id} against JD {jd_id} using LLM only")
    
    # Add calculated experience to resume content if available
    resume_content = resume["parsed_content"]
    calculated_experience = resume.get("experience_years")
    if calculated_experience:
        resume_content = f"[CALCULATED EXPERIENCE: {calculated_experience} years]\n\n{resume_content}"
        logger.info(f"Added calculated experience to resume context: {calculated_experience} years")
    
    # LLM-based detailed analysis (no similarity score)
    llm_analysis = await analyze_resume_jd_match(
        resume_content=resume_content,
        jd_payload=jd_payload
    )
    
    logger.info(f"LLM analysis complete. Overall match score: {llm_analysis.get('overall_match_score', 0):.1f}%")
    
    # Pre-generate interview questions
    logger.info(f"Pre-generating interview questions")
    try:
        jd_text = f"{jd_payload.get('title', '')} {jd_payload.get('description', '')} {jd_payload.get('requirements', '')}"
        generated_questions = await generate_questions(jd_text, resume["parsed_content"], num_questions=10)
    except Exception as e:
        logger.error(f"Failed to generate questions: {e}")
        generated_questions = []
    
    # Build final result
    final_result = {
        # LLM analysis results
        "overall_match_score": llm_analysis.get("overall_match_score", 0.0),
        "final_recommendation": llm_analysis.get("final_recommendation", "moderate_match"),
        "recommendation_action": llm_analysis.get("recommendation_action", "maybe"),
        
        # Detailed breakdowns
        "skills_analysis": llm_analysis.get("skills_analysis", {}),
        "experience_analysis": llm_analysis.get("experience_analysis", {}),
        "education_analysis": llm_analysis.get("education_analysis", {}),
        
        # Summary
        "strengths": llm_analysis.get("strengths", []),
        "weaknesses": llm_analysis.get("weaknesses", []),
        "detailed_explanation": llm_analysis.get("detailed_explanation", ""),
        
        "key_highlights": llm_analysis.get("key_highlights", []),
        "concerns": llm_analysis.get("concerns", []),
        "interview_focus_areas": llm_analysis.get("interview_focus_areas", []),
        
        # Additional factors
        "salary_expectation_alignment": llm_analysis.get("salary_expectation_alignment", "unknown"),
        "notice_period_concern": llm_analysis.get("notice_period_concern", False),
        "location_match": llm_analysis.get("location_match", "unknown"),
        
        # Pre-generated questions
        "generated_questions": generated_questions,
        
        # Backwards compatibility
        "is_match": llm_analysis.get("recommendation_action") == "proceed",
        "recommendation": llm_analysis.get("recommendation_action", "maybe"),
        "analysis": f"Overall Match Score: {llm_analysis.get('overall_match_score', 0):.1f}%. {llm_analysis.get('detailed_explanation', '')}",
        "match_score": llm_analysis.get("overall_match_score", 0.0) / 100.0  # For backwards compatibility
    }
    
    # Save screening result to MongoDB
    logger.info(f"Saving screening result to MongoDB")
    screening_result = ScreeningResultModel(
        resume_id=ObjectId(resume_id),
        jd_id=jd_id,
        candidate_id=resume.get("candidate_id"),
        file_name=file_name,
        semantic_similarity=0.0,  # No longer used, set to 0
        overall_match_score=final_result["overall_match_score"],
        final_recommendation=final_result["final_recommendation"],
        recommendation_action=final_result["recommendation_action"],
        skills_analysis=final_result["skills_analysis"],
        experience_analysis=final_result["experience_analysis"],
        education_analysis=final_result["education_analysis"],
        strengths=final_result["strengths"],
        weaknesses=final_result["weaknesses"],
        detailed_explanation=final_result["detailed_explanation"],
        key_highlights=final_result["key_highlights"],
        concerns=final_result["concerns"],
        interview_focus_areas=final_result["interview_focus_areas"],
        salary_expectation_alignment=final_result["salary_expectation_alignment"],
        notice_period_concern=final_result["notice_period_concern"],
        location_match=final_result["location_match"],
        generated_questions=generated_questions,
        status="pending"
    )
    
    result = await db.screening_results.insert_one(
        screening_result.model_dump(by_alias=True, exclude={"screening_id"})
    )
    
    # Add screening_id to final result
    final_result["screening_id"] = str(result.inserted_id)
    logger.info(f"Screening result saved with ID: {result.inserted_id}")
    
    return final_result
