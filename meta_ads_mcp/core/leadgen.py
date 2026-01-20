"""Lead generation form functionality for Meta Ads API."""

import json
from typing import Optional, Dict, Any, List
from .api import meta_api_tool, make_api_request
from .server import mcp_server
from .http_auth_integration import FastMCPAuthIntegration


def get_page_token_or_default(access_token: Optional[str] = None) -> str:
    """Get page access token from context if available, otherwise use default token.
    
    Args:
        access_token: Default access token (ad account token)
        
    Returns:
        Page access token if available, otherwise the default token
    """
    # Try to get page token from the HTTP auth integration
    page_token = FastMCPAuthIntegration.get_page_access_token()
    if page_token:
        return page_token
    return access_token


@mcp_server.tool()
@meta_api_tool
async def get_lead_forms(
    page_id: str,
    access_token: Optional[str] = None,
    limit: int = 25
) -> str:
    """
    Get all lead generation forms for a Facebook Page.
    
    Args:
        page_id: Facebook Page ID
        access_token: Meta API access token (optional - will use cached token if not provided)
        limit: Maximum number of forms to return (default: 25)
    
    Returns:
        JSON string with list of lead forms
    """
    if not page_id:
        return json.dumps({"error": "No page ID provided"}, indent=2)
    
    # Use page access token if available (required for lead form operations)
    token = get_page_token_or_default(access_token)
    
    endpoint = f"{page_id}/leadgen_forms"
    params = {
        "fields": "id,name,status,locale,context_card,privacy_policy,questions,legal_content,follow_up_action_url,is_optimized_for_quality,created_time",
        "limit": limit
    }
    
    data = await make_api_request(endpoint, token, params)
    
    return json.dumps(data, indent=2)


@mcp_server.tool()
@meta_api_tool
async def get_lead_form_details(
    form_id: str,
    access_token: Optional[str] = None
) -> str:
    """
    Get detailed information about a specific lead generation form.
    
    Args:
        form_id: Lead form ID
        access_token: Meta API access token (optional - will use cached token if not provided)
    
    Returns:
        JSON string with lead form details
    """
    if not form_id:
        return json.dumps({"error": "No form ID provided"}, indent=2)
    
    # Use page access token if available
    token = get_page_token_or_default(access_token)
    
    endpoint = f"{form_id}"
    params = {
        "fields": "id,name,status,locale,context_card,privacy_policy,questions,legal_content,follow_up_action_url,is_optimized_for_quality,created_time,page"
    }
    
    data = await make_api_request(endpoint, token, params)
    
    return json.dumps(data, indent=2)


@mcp_server.tool()
@meta_api_tool
async def create_lead_form(
    page_id: str,
    name: str,
    privacy_policy_url: str,
    access_token: Optional[str] = None,
    locale: str = "en_US",
    questions: Optional[List[Dict[str, Any]]] = None,
    context_card_title: Optional[str] = None,
    context_card_content: Optional[str] = None,
    context_card_button_text: Optional[str] = None,
    context_card_style: str = "PARAGRAPH_STYLE",
    thank_you_page_title: Optional[str] = None,
    thank_you_page_body: Optional[str] = None,
    thank_you_page_button_type: str = "VIEW_WEBSITE",
    thank_you_page_button_text: Optional[str] = None,
    thank_you_page_website_url: Optional[str] = None,
    follow_up_action_url: Optional[str] = None,
    is_optimized_for_quality: bool = False
) -> str:
    """
    Create a new lead generation form for a Facebook Page.
    
    Args:
        page_id: Facebook Page ID
        name: Name of the lead form (internal name, not shown to users)
        privacy_policy_url: URL to your privacy policy (REQUIRED by Meta)
        access_token: Meta API access token (optional - will use cached token if not provided)
        locale: Locale for the form (default: en_US)
        questions: List of form questions. Each question is a dict with:
                   - type: FULL_NAME, EMAIL, PHONE, etc.
                   - key: Unique identifier for the question
                   - label: Question text shown to user (optional for predefined fields)
                   Example: [{"type": "FULL_NAME"}, {"type": "EMAIL"}, {"type": "PHONE"}]
        context_card_title: Title shown on the form intro screen
        context_card_content: Description shown on the form intro screen
        context_card_button_text: Text for the CTA button (default: "Sign Up")
        context_card_style: Intro card visual style (default: PARAGRAPH_STYLE). Options:
                            PARAGRAPH_STYLE (Classic - title + paragraph),
                            BULLET_STYLE (Bullet points list),
                            IMAGE_STYLE (Image-based intro)
        thank_you_page_title: Title shown after form submission
        thank_you_page_body: Message shown after form submission
        thank_you_page_button_type: Button action type (default: VIEW_WEBSITE). Options:
                                     VIEW_WEBSITE, WHATSAPP, CALL_BUSINESS, MESSAGE_BUSINESS,
                                     DOWNLOAD, SCHEDULE_APPOINTMENT, VIEW_ON_FACEBOOK,
                                     PROMO_CODE, NONE, P2B_MESSENGER, BOOK_ON_WEBSITE
        thank_you_page_button_text: Custom button text (has smart defaults per button_type)
        thank_you_page_website_url: URL for VIEW_WEBSITE button type
        follow_up_action_url: URL to redirect users after form submission
        is_optimized_for_quality: Enable higher intent signals (recommended for B2B)
    
    Returns:
        JSON string with created form ID and details
    
    Example:
        Create a lead form with WhatsApp button:
        {
            "page_id": "123456789",
            "name": "Contact Form",
            "privacy_policy_url": "https://example.com/privacy",
            "questions": [
                {"type": "FULL_NAME"},
                {"type": "EMAIL"},
                {"type": "PHONE"}
            ],
            "context_card_title": "Get in Touch",
            "context_card_content": "Fill out this form and we'll contact you soon!",
            "thank_you_page_title": "Thanks!",
            "thank_you_page_body": "We'll be in touch shortly.",
            "thank_you_page_button_type": "VIEW_WEBSITE",
            "thank_you_page_button_text": "Visit Our Site",
            "thank_you_page_website_url": "https://example.com"
        }
    """
    if not page_id:
        return json.dumps({"error": "No page ID provided"}, indent=2)
    
    if not name:
        return json.dumps({"error": "No form name provided"}, indent=2)
    
    if not privacy_policy_url:
        return json.dumps({"error": "Privacy policy URL is required"}, indent=2)
    
    # Use page access token if available (REQUIRED for lead form creation)
    token = get_page_token_or_default(access_token)
    
    endpoint = f"{page_id}/leadgen_forms"
    
    # Build form data
    params = {
        "name": name,
        "locale": locale,
        "privacy_policy": {
            "url": privacy_policy_url
        }
    }
    
    # Add questions (default to basic contact info if not provided)
    if not questions:
        questions = [
            {"type": "FULL_NAME"},
            {"type": "EMAIL"},
            {"type": "PHONE"}
        ]
    
    params["questions"] = questions
    
    # Add context card (intro screen) - REQUIRED by Meta API
    if context_card_title or context_card_content or context_card_button_text:
        context_card = {
            "style": context_card_style  # REQUIRED: PARAGRAPH_STYLE, BULLET_STYLE, or IMAGE_STYLE
        }
        if context_card_title:
            context_card["title"] = context_card_title
        if context_card_content:
            context_card["content"] = context_card_content
        if context_card_button_text:
            context_card["button_text"] = context_card_button_text
        params["context_card"] = context_card
    
    # Add thank you page
    if thank_you_page_title or thank_you_page_body:
        thank_you_page = {}
        if thank_you_page_title:
            thank_you_page["title"] = thank_you_page_title
        if thank_you_page_body:
            thank_you_page["body"] = thank_you_page_body
        
        # Add button configuration (required by Meta API)
        thank_you_page["button_type"] = thank_you_page_button_type
        
        if thank_you_page_button_text:
            thank_you_page["button_text"] = thank_you_page_button_text
        elif thank_you_page_button_type != "NONE":
            # Provide default button text based on type
            button_defaults = {
                "VIEW_WEBSITE": "Learn More",
                "WHATSAPP": "Chat on WhatsApp",
                "CALL_BUSINESS": "Call Us",
                "MESSAGE_BUSINESS": "Send Message",
                "DOWNLOAD": "Download",
                "SCHEDULE_APPOINTMENT": "Schedule Now",
                "VIEW_ON_FACEBOOK": "View on Facebook",
                "PROMO_CODE": "Get Code",
                "P2B_MESSENGER": "Message Us",
                "BOOK_ON_WEBSITE": "Book Now"
            }
            thank_you_page["button_text"] = button_defaults.get(thank_you_page_button_type, "Continue")
        
        # Add website URL for VIEW_WEBSITE button type
        if thank_you_page_button_type == "VIEW_WEBSITE" and thank_you_page_website_url:
            thank_you_page["website_url"] = thank_you_page_website_url
        
        params["thank_you_page"] = thank_you_page
    
    # Add follow-up action URL
    if follow_up_action_url:
        params["follow_up_action_url"] = follow_up_action_url
    
    # Add quality optimization
    if is_optimized_for_quality:
        params["is_optimized_for_quality"] = True
    
    # Use page access token if available (REQUIRED for lead form creation)
    token = get_page_token_or_default(access_token)
    
    try:
        data = await make_api_request(endpoint, token, params, method="POST")
        return json.dumps(data, indent=2)
    except Exception as e:
        error_msg = str(e)
        return json.dumps({
            "error": "Failed to create lead form",
            "details": error_msg,
            "params_sent": params
        }, indent=2)


@mcp_server.tool()
@meta_api_tool
async def get_lead_form_leads(
    form_id: str,
    access_token: Optional[str] = None,
    limit: int = 100
) -> str:
    """
    Get leads (submissions) from a lead generation form.
    
    Args:
        form_id: Lead form ID
        access_token: Meta API access token (optional - will use cached token if not provided)
        limit: Maximum number of leads to return (default: 100)
    
    Returns:
        JSON string with list of leads
    """
    if not form_id:
        return json.dumps({"error": "No form ID provided"}, indent=2)
    
    # Use page access token if available
    token = get_page_token_or_default(access_token)
    
    endpoint = f"{form_id}/leads"
    params = {
        "fields": "id,created_time,field_data",
        "limit": limit
    }
    
    data = await make_api_request(endpoint, token, params)
    
    return json.dumps(data, indent=2)


@mcp_server.tool()
@meta_api_tool
async def update_lead_form(
    form_id: str,
    access_token: Optional[str] = None,
    name: Optional[str] = None,
    status: Optional[str] = None,
    follow_up_action_url: Optional[str] = None
) -> str:
    """
    Update an existing lead generation form.
    
    Args:
        form_id: Lead form ID
        access_token: Meta API access token (optional - will use cached token if not provided)
        name: New name for the form
        status: Form status - "ACTIVE" or "ARCHIVED"
        follow_up_action_url: New follow-up URL
    
    Returns:
        JSON string with update result
    """
    if not form_id:
        return json.dumps({"error": "No form ID provided"}, indent=2)
    
    params = {}
    
    if name:
        params["name"] = name
    
    if status:
        if status not in ["ACTIVE", "ARCHIVED"]:
            return json.dumps({"error": "Status must be ACTIVE or ARCHIVED"}, indent=2)
        params["status"] = status
    
    if follow_up_action_url:
        params["follow_up_action_url"] = follow_up_action_url
    
    if not params:
        return json.dumps({"error": "No update parameters provided"}, indent=2)
    
    # Use page access token if available
    token = get_page_token_or_default(access_token)
    
    endpoint = f"{form_id}"
    
    try:
        data = await make_api_request(endpoint, token, params, method="POST")
        return json.dumps(data, indent=2)
    except Exception as e:
        error_msg = str(e)
        return json.dumps({
            "error": "Failed to update lead form",
            "details": error_msg,
            "params_sent": params
        }, indent=2)
