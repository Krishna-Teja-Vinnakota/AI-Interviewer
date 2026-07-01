"""Bunny CDN storage service for video uploads."""
import httpx
from core.config import settings
import logging

logger = logging.getLogger(__name__)


class BunnyStorageService:
    """Bunny CDN storage service."""
    
    def __init__(self):
        self.storage_zone = settings.BUNNY_STORAGE_ZONE
        self.api_key = settings.BUNNY_API_KEY
        self.cdn_hostname = settings.BUNNY_CDN_HOSTNAME
        self.region = settings.BUNNY_STORAGE_REGION
        
        if self.region == "de":
            self.storage_endpoint = "https://storage.bunnycdn.com"
        elif self.region == "ny":
            self.storage_endpoint = "https://ny.storage.bunnycdn.com"
        elif self.region == "la":
            self.storage_endpoint = "https://la.storage.bunnycdn.com"
        elif self.region == "sg":
            self.storage_endpoint = "https://sg.storage.bunnycdn.com"
        else:
            self.storage_endpoint = "https://storage.bunnycdn.com"
    
    async def upload_video(self, video_content: bytes, interview_id: str) -> dict:
        """Upload complete interview video to Bunny Storage."""
        
        file_path = f"interviews/{interview_id}/complete.webm"
        upload_url = f"{self.storage_endpoint}/{self.storage_zone}/{file_path}"
        
        headers = {
            "AccessKey": self.api_key,
            "Content-Type": "video/webm"
        }
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.put(
                    upload_url,
                    headers=headers,
                    content=video_content
                )
                
                response.raise_for_status()
                
                cdn_url = f"https://{self.cdn_hostname}/{file_path}"
                
                logger.info(f"Video uploaded: {cdn_url} ({len(video_content)} bytes)")
                
                return {
                    "storage_path": file_path,
                    "cdn_url": cdn_url,
                    "size_bytes": len(video_content)
                }
                
        except Exception as e:
            logger.error(f"Bunny upload failed: {e}")
            raise
    
    async def delete_video(self, interview_id: str) -> bool:
        """Delete interview video from storage."""
        
        file_path = f"interviews/{interview_id}/complete.webm"
        delete_url = f"{self.storage_endpoint}/{self.storage_zone}/{file_path}"
        
        headers = {"AccessKey": self.api_key}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(delete_url, headers=headers)
                response.raise_for_status()
                logger.info(f"Video deleted: {file_path}")
                return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False


bunny_service = BunnyStorageService()
