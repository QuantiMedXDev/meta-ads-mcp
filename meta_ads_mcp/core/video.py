"""Video-related functionality for Meta Ads API."""

import json
import os
import uuid
import tempfile
import subprocess
import httpx
from typing import Optional, Dict, Any

from .api import meta_api_tool, make_api_request
from .server import mcp_server
from .utils import logger

# GCS Configuration
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "zorgsocialwebsite")
GCS_FOLDER = os.environ.get("GCS_FOLDER", "assets/ad_thumbnails")


def _get_gcs_bucket():
    """Get GCS bucket using credentials from environment."""
    try:
        from google.cloud import storage
        from google.oauth2 import service_account
        
        # Try inline JSON credentials first
        gcs_key = os.environ.get("GOOGLE_CLOUD_KEY")
        if gcs_key:
            try:
                credentials_dict = json.loads(gcs_key)
                credentials = service_account.Credentials.from_service_account_info(credentials_dict)
                storage_client = storage.Client(credentials=credentials)
                return storage_client.bucket(GCS_BUCKET_NAME)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse GOOGLE_CLOUD_KEY: {e}")
        
        # Try file path
        key_file = os.environ.get("GOOGLE_CLOUD_KEY_FILE")
        if key_file and os.path.exists(key_file):
            credentials = service_account.Credentials.from_service_account_file(key_file)
            storage_client = storage.Client(credentials=credentials)
            return storage_client.bucket(GCS_BUCKET_NAME)
        
        # Try default credentials
        storage_client = storage.Client()
        return storage_client.bucket(GCS_BUCKET_NAME)
        
    except Exception as e:
        logger.error(f"Failed to get GCS bucket: {e}")
        return None


async def extract_video_thumbnail(video_url: str) -> Optional[str]:
    """
    Extract a frame from a video URL using ffmpeg and upload to GCS.
    Returns the thumbnail URL or None if extraction fails.
    """
    try:
        logger.info(f"[extract_video_thumbnail] Extracting thumbnail from: {video_url}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "thumbnail.jpg")
            
            # Use ffmpeg to extract a frame at 1 second (or first frame if video is shorter)
            cmd = [
                "ffmpeg",
                "-i", video_url,
                "-ss", "1",
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                output_path
            ]
            
            logger.info(f"[extract_video_thumbnail] Running ffmpeg command")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.warning(f"[extract_video_thumbnail] ffmpeg failed: {result.stderr}")
                # Try extracting from the very start if 1s seek failed
                cmd[4] = "0"
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    logger.error(f"[extract_video_thumbnail] ffmpeg failed again: {result.stderr}")
                    return None
            
            if not os.path.exists(output_path):
                logger.error("[extract_video_thumbnail] Thumbnail file not created")
                return None
            
            with open(output_path, "rb") as f:
                thumbnail_data = f.read()
            
            logger.info(f"[extract_video_thumbnail] Thumbnail extracted, size: {len(thumbnail_data)} bytes")
            
            # Get GCS bucket and upload
            bucket = _get_gcs_bucket()
            if not bucket:
                logger.error("[extract_video_thumbnail] Could not get GCS bucket")
                return None
            
            unique_id = str(uuid.uuid4())
            blob_name = f"{GCS_FOLDER}/{unique_id}.jpg"
            
            blob = bucket.blob(blob_name)
            blob.content_type = "image/jpeg"
            blob.cache_control = "public, max-age=3600"
            blob.upload_from_string(thumbnail_data, content_type="image/jpeg")
            
            thumbnail_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_name}"
            logger.info(f"[extract_video_thumbnail] Thumbnail uploaded to: {thumbnail_url}")
            
            return thumbnail_url
            
    except subprocess.TimeoutExpired:
        logger.error("[extract_video_thumbnail] ffmpeg timeout")
        return None
    except Exception as e:
        logger.error(f"[extract_video_thumbnail] Error: {str(e)}")
        return None


@mcp_server.tool()
@meta_api_tool
async def upload_ad_video(
    page_id: str,
    video_url: str,
    access_token: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """
    Upload a video to a Facebook Page for use in ad creatives.
    
    Args:
        page_id: Facebook Page ID where the video will be uploaded
        video_url: Direct URL to the video file (must be publicly accessible)
        access_token: Meta API access token (will use cached token if not provided)
        title: Optional video title
        description: Optional video description
    
    Returns:
        JSON response with video_id for use in ad creative creation
    """
    if not page_id:
        return json.dumps({"error": "No page ID provided"}, indent=2)
    
    if not video_url:
        return json.dumps({"error": "No video URL provided"}, indent=2)
    
    try:
        # First, get the page access token from the user token
        # This is required for uploading videos to pages
        logger.info(f"[upload_ad_video] Getting page access token for page {page_id}")
        
        page_token_endpoint = f"{page_id}"
        page_token_params = {"fields": "access_token,name"}
        page_data = await make_api_request(page_token_endpoint, access_token, page_token_params)
        
        page_access_token = page_data.get("access_token")
        if not page_access_token:
            logger.warning(f"[upload_ad_video] Could not get page access token, using user token. Response: {page_data}")
            # Fall back to user token - might work for some use cases
            page_access_token = access_token
        else:
            logger.info(f"[upload_ad_video] Got page access token for: {page_data.get('name', page_id)}")
        
        # Upload video to Page's videos endpoint as unpublished
        endpoint = f"{page_id}/videos"
        
        params = {
            "file_url": video_url,
            "published": "false",  # Upload as unpublished for ad use
        }
        
        if title:
            params["title"] = title
        if description:
            params["description"] = description
        
        logger.info(f"[upload_ad_video] Uploading video to page {page_id}")
        # Use page_access_token for video upload
        data = await make_api_request(endpoint, page_access_token, params, method="POST")
        
        if "error" in data:
            return json.dumps({
                "error": "Failed to upload video",
                "details": data.get("error"),
                "page_id": page_id,
                "video_url": video_url
            }, indent=2)
        
        video_id = data.get("id")
        
        if video_id:
            logger.info(f"[upload_ad_video] Video uploaded successfully, video_id: {video_id}")
            
            # Also extract a thumbnail for use in the creative
            thumbnail_url = await extract_video_thumbnail(video_url)
            
            return json.dumps({
                "success": True,
                "video_id": video_id,
                "page_id": page_id,
                "thumbnail_url": thumbnail_url,
                "message": "Video uploaded successfully. Use the video_id with create_video_ad_creative to create an ad."
            }, indent=2)
        else:
            return json.dumps({
                "error": "Video upload succeeded but no video_id returned",
                "raw_response": data
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "error": "Failed to upload video",
            "details": str(e),
            "page_id": page_id
        }, indent=2)


@mcp_server.tool()
@meta_api_tool
async def create_video_ad_creative(
    account_id: str,
    video_id: str,
    page_id: str,
    access_token: Optional[str] = None,
    name: Optional[str] = None,
    message: Optional[str] = None,
    title: Optional[str] = None,
    link_url: Optional[str] = None,
    call_to_action_type: str = "LEARN_MORE",
    thumbnail_url: Optional[str] = None,
    instagram_actor_id: Optional[str] = None
) -> str:
    """
    Create a new ad creative using an uploaded video.
    
    Args:
        account_id: Meta Ads account ID (format: act_XXXXXXXXX)
        video_id: ID of the uploaded video (from upload_ad_video)
        page_id: Facebook Page ID for the ad
        access_token: Meta API access token (will use cached token if not provided)
        name: Creative name
        message: Ad copy/text (primary text)
        title: Video title/headline
        link_url: Destination URL when user clicks (defaults to facebook.com)
        call_to_action_type: CTA button type (LEARN_MORE, SHOP_NOW, SIGN_UP, etc.)
        thumbnail_url: Custom thumbnail URL (extracted automatically if not provided)
        instagram_actor_id: Optional Instagram account ID for Instagram placements
    
    Returns:
        JSON response with created creative details including creative_id
    """
    if not account_id:
        return json.dumps({"error": "No account ID provided"}, indent=2)
    
    if not video_id:
        return json.dumps({"error": "No video ID provided"}, indent=2)
    
    if not page_id:
        return json.dumps({"error": "No page ID provided"}, indent=2)
    
    # Ensure account_id has 'act_' prefix
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"
    
    try:
        import time
        
        creative_name = name or f"Video Creative {int(time.time())}"
        link_value = link_url or "https://www.facebook.com"
        
        # Build video_data object story spec
        video_data = {
            "video_id": video_id,
            "message": message or "",
            "call_to_action": {
                "type": call_to_action_type,
                "value": {"link": link_value}
            }
        }
        
        # CRITICAL: Thumbnail is REQUIRED by Meta API
        # If not provided, use a fallback placeholder image
        if thumbnail_url:
            video_data["image_url"] = thumbnail_url
        else:
            # Use a fallback placeholder - this should be replaced with actual thumbnail
            logger.warning("[create_video_ad_creative] No thumbnail_url provided, using fallback")
            # Fallback to a publicly accessible placeholder
            fallback_thumbnail = "https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=1200&h=628&fit=crop"
            video_data["image_url"] = fallback_thumbnail
        
        # Add title if provided
        if title:
            video_data["title"] = title
        
        # Build object_story_spec
        object_story_spec = {
            "page_id": page_id,
            "video_data": video_data
        }
        
        # Add Instagram actor if provided
        if instagram_actor_id:
            object_story_spec["instagram_actor_id"] = instagram_actor_id
        
        # Create the creative
        endpoint = f"{account_id}/adcreatives"
        params = {
            "name": creative_name,
            "object_story_spec": object_story_spec
        }
        
        logger.info(f"[create_video_ad_creative] Creating video creative: {params}")
        data = await make_api_request(endpoint, access_token, params, method="POST")
        
        if "error" in data:
            return json.dumps({
                "error": "Failed to create video creative",
                "details": data.get("error"),
                "params_sent": {
                    "name": creative_name,
                    "video_id": video_id,
                    "page_id": page_id
                }
            }, indent=2)
        
        creative_id = data.get("id")
        
        if creative_id:
            logger.info(f"[create_video_ad_creative] Creative created: {creative_id}")
            return json.dumps({
                "success": True,
                "creative_id": creative_id,
                "account_id": account_id,
                "video_id": video_id,
                "page_id": page_id,
                "name": creative_name,
                "message": "Video creative created successfully. Use create_ad with this creative_id to complete ad creation."
            }, indent=2)
        else:
            return json.dumps({
                "error": "Creative creation succeeded but no creative_id returned",
                "raw_response": data
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "error": "Failed to create video creative",
            "details": str(e)
        }, indent=2)


@mcp_server.tool()
@meta_api_tool
async def create_complete_video_ad(
    account_id: str,
    page_id: str,
    adset_id: str,
    video_url: str,
    ad_name: str,
    access_token: Optional[str] = None,
    primary_text: Optional[str] = None,
    headline: Optional[str] = None,
    link_url: Optional[str] = None,
    call_to_action: str = "LEARN_MORE",
    instagram_actor_id: Optional[str] = None
) -> str:
    """
    Create a complete video ad in one step: uploads video, creates creative, and creates ad.
    
    This is a convenience function that combines upload_ad_video, create_video_ad_creative, and create_ad.
    
    Args:
        account_id: Meta Ads account ID (format: act_XXXXXXXXX)
        page_id: Facebook Page ID for the ad
        adset_id: Ad Set ID where this ad will be placed
        video_url: Direct URL to the video file (must be publicly accessible)
        ad_name: Name for the ad
        access_token: Meta API access token (will use cached token if not provided)
        primary_text: Ad copy/message text
        headline: Video title/headline
        link_url: Destination URL (defaults to facebook.com)
        call_to_action: CTA button type (LEARN_MORE, SHOP_NOW, SIGN_UP, etc.)
        instagram_actor_id: Optional Instagram account ID
    
    Returns:
        JSON response with video_id, creative_id, and ad_id
    """
    if not account_id:
        return json.dumps({"error": "No account ID provided"}, indent=2)
    
    if not page_id:
        return json.dumps({"error": "No page ID provided"}, indent=2)
    
    if not adset_id:
        return json.dumps({"error": "No ad set ID provided"}, indent=2)
    
    if not video_url:
        return json.dumps({"error": "No video URL provided"}, indent=2)
    
    # Ensure account_id has 'act_' prefix
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"
    
    try:
        # Step 1: Upload video
        logger.info(f"[create_complete_video_ad] Step 1: Uploading video from {video_url}")
        
        upload_result = await upload_ad_video(
            page_id=page_id,
            video_url=video_url,
            access_token=access_token,
            title=headline,
            description=primary_text
        )
        
        upload_data = json.loads(upload_result)
        if "error" in upload_data:
            return json.dumps({
                "error": "Failed at Step 1: Video upload",
                "details": upload_data
            }, indent=2)
        
        video_id = upload_data.get("video_id")
        thumbnail_url = upload_data.get("thumbnail_url")
        
        logger.info(f"[create_complete_video_ad] Video uploaded: {video_id}")
        
        # Step 2: Create video creative
        logger.info(f"[create_complete_video_ad] Step 2: Creating video creative")
        
        creative_result = await create_video_ad_creative(
            account_id=account_id,
            video_id=video_id,
            page_id=page_id,
            access_token=access_token,
            name=f"{ad_name} Creative",
            message=primary_text,
            title=headline,
            link_url=link_url,
            call_to_action_type=call_to_action,
            thumbnail_url=thumbnail_url,
            instagram_actor_id=instagram_actor_id
        )
        
        creative_data = json.loads(creative_result)
        if "error" in creative_data:
            return json.dumps({
                "error": "Failed at Step 2: Creative creation",
                "video_id": video_id,
                "details": creative_data
            }, indent=2)
        
        creative_id = creative_data.get("creative_id")
        logger.info(f"[create_complete_video_ad] Creative created: {creative_id}")
        
        # Step 3: Create the ad
        logger.info(f"[create_complete_video_ad] Step 3: Creating ad")
        
        endpoint = f"{account_id}/ads"
        params = {
            "name": ad_name,
            "adset_id": adset_id,
            "creative": {"creative_id": creative_id},
            "status": "PAUSED"
        }
        
        data = await make_api_request(endpoint, access_token, params, method="POST")
        
        if "error" in data:
            return json.dumps({
                "error": "Failed at Step 3: Ad creation",
                "video_id": video_id,
                "creative_id": creative_id,
                "details": data.get("error")
            }, indent=2)
        
        ad_id = data.get("id")
        logger.info(f"[create_complete_video_ad] Ad created: {ad_id}")
        
        return json.dumps({
            "success": True,
            "ad_id": ad_id,
            "creative_id": creative_id,
            "video_id": video_id,
            "ad_name": ad_name,
            "adset_id": adset_id,
            "account_id": account_id,
            "page_id": page_id,
            "thumbnail_url": thumbnail_url,
            "message": "Video ad created successfully! The ad is currently PAUSED. Use update_ad_status to activate it."
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": "Failed to create complete video ad",
            "details": str(e)
        }, indent=2)
