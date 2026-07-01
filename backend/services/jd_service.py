"""Job Description service for MongoDB CRUD operations."""
import logging
from typing import List, Dict, Any, Optional
from bson import ObjectId
from datetime import datetime
from core.database import get_database
from core.models import JobDescriptionModel

logger = logging.getLogger(__name__)


async def create_jd(
    title: str,
    description: str,
    requirements: str,
    skills: List[str],
    location: Optional[str] = None,
    experience_required: Optional[str] = None,
    salary_range: Optional[str] = None,
    notice_period_acceptable: Optional[str] = None
) -> str:
    """Create a new job description in MongoDB."""
    try:
        db = get_database()
        
        jd_doc = JobDescriptionModel(
            title=title,
            description=description,
            requirements=requirements,
            skills=skills,
            location=location,
            experience_required=experience_required,
            salary_range=salary_range,
            notice_period_acceptable=notice_period_acceptable,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        result = await db.job_descriptions.insert_one(
            jd_doc.model_dump(by_alias=True, exclude={"jd_id"})
        )
        
        jd_id = str(result.inserted_id)
        logger.info(f"Created JD {jd_id} in MongoDB")
        return jd_id
        
    except Exception as e:
        logger.error(f"Failed to create JD: {e}")
        raise


async def get_jd_by_id(jd_id: str) -> Optional[Dict[str, Any]]:
    """Get job description by ID from MongoDB."""
    try:
        db = get_database()
        
        jd = await db.job_descriptions.find_one({"_id": ObjectId(jd_id)})
        
        if jd:
            # Convert to dict format compatible with current code
            jd["jd_id"] = str(jd["_id"])
            jd["skills_required"] = jd.get("skills", [])
            jd["job_description"] = jd.get("description", "")
            logger.info(f"Retrieved JD: {jd_id} from MongoDB")
            return jd
        
        logger.warning(f"JD not found: {jd_id}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to get JD by ID: {e}")
        return None


async def get_all_jds() -> List[Dict[str, Any]]:
    """Get all job descriptions from MongoDB."""
    try:
        db = get_database()
        
        cursor = db.job_descriptions.find({})
        jds = await cursor.to_list(length=1000)
        
        # Convert to dict format compatible with current code
        for jd in jds:
            jd["jd_id"] = str(jd["_id"])
            jd["skills_required"] = jd.get("skills", [])
            jd["job_description"] = jd.get("description", "")
        
        logger.info(f"Retrieved {len(jds)} JDs from MongoDB")
        return jds
        
    except Exception as e:
        logger.error(f"Failed to get all JDs: {e}")
        return []


async def update_jd(
    jd_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    requirements: Optional[str] = None,
    skills: Optional[List[str]] = None,
    location: Optional[str] = None,
    experience_required: Optional[str] = None,
    salary_range: Optional[str] = None,
    notice_period_acceptable: Optional[str] = None
) -> bool:
    """Update job description in MongoDB."""
    try:
        db = get_database()
        
        # Build update dict with only provided fields
        update_fields = {"updated_at": datetime.utcnow()}
        
        if title is not None:
            update_fields["title"] = title
        if description is not None:
            update_fields["description"] = description
        if requirements is not None:
            update_fields["requirements"] = requirements
        if skills is not None:
            update_fields["skills"] = skills
        if location is not None:
            update_fields["location"] = location
        if experience_required is not None:
            update_fields["experience_required"] = experience_required
        if salary_range is not None:
            update_fields["salary_range"] = salary_range
        if notice_period_acceptable is not None:
            update_fields["notice_period_acceptable"] = notice_period_acceptable
        
        result = await db.job_descriptions.update_one(
            {"_id": ObjectId(jd_id)},
            {"$set": update_fields}
        )
        
        if result.modified_count > 0 or result.matched_count > 0:
            logger.info(f"Updated JD {jd_id} in MongoDB")
            return True
        
        logger.warning(f"JD not found for update: {jd_id}")
        return False
        
    except Exception as e:
        logger.error(f"Failed to update JD: {e}")
        raise


async def delete_jd(jd_id: str) -> bool:
    """Delete job description from MongoDB."""
    try:
        db = get_database()
        
        result = await db.job_descriptions.delete_one({"_id": ObjectId(jd_id)})
        
        if result.deleted_count > 0:
            logger.info(f"Deleted JD {jd_id} from MongoDB")
            return True
        
        logger.warning(f"JD not found for deletion: {jd_id}")
        return False
        
    except Exception as e:
        logger.error(f"Failed to delete JD: {e}")
        raise
