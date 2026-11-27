from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
from jinja2 import Template
import smtplib
import time
import random
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from pathlib import Path
import json
from datetime import datetime
# Removed Gemini imports
# Removed PyPDF2 import
# Removed scraping imports
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from email import message_from_bytes
import email.utils

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}})

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large. Maximum allowed upload size is 16 MB."}), 413

# Configuration
from werkzeug.utils import secure_filename
import re

# Configuration
UPLOAD_FOLDER = 'uploads'
RESUME_FOLDER = 'resumes'
CAMPAIGNS_FILE = 'campaigns.json'
EMAILS_FILE = 'emails.json'
DRAFTS_FOLDER = 'drafts'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESUME_FOLDER, exist_ok=True)
# Removed scraping constants
os.makedirs(DRAFTS_FOLDER, exist_ok=True)

# Email configuration
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
SENDER_NAME = os.getenv("SENDER_NAME", "Adithya Narayan")

# Removed Gemini AI configuration
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# if GEMINI_API_KEY:
#     genai.configure(api_key=GEMINI_API_KEY)

# Email sending configuration
DELAY_SECONDS_MIN = 4
DELAY_SECONDS_MAX = 8
BATCH_SIZE = 100
BATCH_BREAK_SECONDS = 300

# Gmail API configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.modify']
CLIENT_SECRETS_FILE = 'client_secret.json'  # User needs to create this from Google Cloud Console
CREDENTIALS_FILE = 'gmail_credentials.json'

# Helper functions
def load_campaigns():
    if os.path.exists(CAMPAIGNS_FILE):
        with open(CAMPAIGNS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_campaigns(campaigns):
    with open(CAMPAIGNS_FILE, 'w') as f:
        json.dump(campaigns, f, indent=2)

def load_emails():
    """Load emails from storage"""
    if os.path.exists(EMAILS_FILE):
        with open(EMAILS_FILE, 'r') as f:
            return json.load(f)
    return {"inbox": [], "sent": [], "drafts": []}

def save_emails(emails_data):
    """Save emails to storage"""
    with open(EMAILS_FILE, 'w') as f:
        json.dump(emails_data, f, indent=2)

def get_gmail_service():
    """Get Gmail API service instance, refreshing expired OAuth tokens when possible"""
    creds = None
    if os.path.exists(CREDENTIALS_FILE):
        try:
            creds = Credentials.from_authorized_user_file(CREDENTIALS_FILE, SCOPES)
        except Exception as e:
            print(f"Error loading Gmail credentials file: {type(e).__name__}")
            return None

    if not creds:
        return None

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(CREDENTIALS_FILE, 'w') as token_file:
                    token_file.write(creds.to_json())
            except Exception as e:
                print(f"Error refreshing Gmail credentials: {type(e).__name__}")
                return None
        else:
            return None

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building Gmail service: {type(e).__name__}")
        return None

def extract_template_subject_pattern():
    """Extract subject pattern from email template"""
    try:
        with open("email_template.txt", "r", encoding="utf-8") as f:
            template_content = f.read()
        # Extract subject line (first line after "Subject:")
        if "Subject:" in template_content:
            subject_line = template_content.split("Subject:")[1].split("\n")[0].strip()
            # Remove template variables to create pattern
            # Gmail search doesn't support regex, so we just use the static parts
            clean_subject = re.sub(r'\{\{.*?\}\}', ' ', subject_line)
            # Remove special characters that might confuse search
            clean_subject = re.sub(r'[^\w\s-]', ' ', clean_subject)
            # Remove extra whitespace
            pattern = ' '.join(clean_subject.split())
            return pattern
    except:
        pass
    return "Internship Application"

# AI functions removed
# def extract_text_from_pdf(pdf_path):
#     """Extract text from PDF file"""
#     try:
#         with open(pdf_path, 'rb') as file:
#             pdf_reader = PyPDF2.PdfReader(file)
#             text = ""
#             for page in pdf_reader.pages:
#                 text += page.extract_text()
#             return text
#     except Exception as e:
#         print(f"Error extracting PDF: {e}")
#         return ""

# def extract_resume_metadata_with_gemini(pdf_path):
#     """Extract resume metadata using Gemini AI"""
#     if not GEMINI_API_KEY:
#         return {
#             "name": "Not available",
#             "education": "Not available",
#             "skills": [],
#             "projects": [],
#             "interests": "Not available"
#         }
    
#     try:
#         # Extract text from PDF
#         resume_text = extract_text_from_pdf(pdf_path)
        
#         if not resume_text:
#             return None
        
#         # Use Gemini to extract metadata
#         model = genai.GenerativeModel('gemini-pro')
#         prompt = f"""Extract the following information from this resume text and return as JSON:
# {{
#     "name": "Full name",
#     "education": "College/University, Year, Major/Degree",
#     "skills": ["skill1", "skill2", ...],
#     "projects": ["project1 description", "project2 description", ...],
#     "interests": "Career interests or professional interests"
# }}

# Resume text:
# {resume_text[:3000]}

# Return only valid JSON, no additional text."""
        
#         response = model.generate_content(prompt)
#         result_text = response.text.strip()
        
#         response = model.generate_content(prompt)
#         result_text = response.text.strip()
        
#         # Robust JSON cleaning
#         try:
#             # Find the first '{' and last '}'
#             start_idx = result_text.find('{')
#             end_idx = result_text.rfind('}')
            
#             if start_idx != -1 and end_idx != -1:
#                 json_str = result_text[start_idx:end_idx+1]
#                 metadata = json.loads(json_str)
#             else:
#                 # If no JSON braces found, force empty structure
#                 raise ValueError("No JSON found in response")
                
#             return metadata
#         except Exception as e:
#             print(f"JSON parsing error: {str(e)}\nRaw text: {result_text}")
#             return {
#                 "name": "Extraction Failed",
#                 "education": "Could not extract",
#                 "skills": ["Manual entry required"],
#                 "projects": [],
#                 "interests": "Please upload again or edit manually"
#             }
#     except Exception as e:
#         print(f"Error extracting metadata with Gemini: {e}")
#         return {
#             "name": "Error extracting",
#             "education": "Error extracting",
#             "skills": [],
#             "projects": [],
#             "interests": "Error extracting"
#         }

def _format_file_size(file_size):
    """Format byte count into a consistent user-friendly size string"""
    if file_size < 1024:
        return f"{file_size} B"
    if file_size < 1024 * 1024:
        return f"{file_size / 1024:.1f} KB"
    return f"{file_size / (1024 * 1024):.2f} MB"

def _resolve_safe_resume_path(filename):
    """Resolve a PDF filename strictly inside RESUME_FOLDER, or return None"""
    safe_name = secure_filename(filename or "")
    if not safe_name or not safe_name.lower().endswith('.pdf'):
        return None
    resume_dir = os.path.abspath(RESUME_FOLDER)
    candidate = os.path.abspath(os.path.join(resume_dir, safe_name))
    if not candidate.startswith(resume_dir + os.sep):
        return None
    return candidate

def _list_resume_files():
    """Return full paths of all valid PDF files strictly inside RESUME_FOLDER"""
    resume_dir = os.path.abspath(RESUME_FOLDER)
    if not os.path.isdir(resume_dir):
        return []
    files = []
    for entry in os.listdir(resume_dir):
        if not entry.lower().endswith('.pdf'):
            continue
        full_path = os.path.abspath(os.path.join(resume_dir, entry))
        if full_path.startswith(resume_dir + os.sep) and os.path.isfile(full_path):
            files.append(full_path)
    return files

def _get_active_resume_path():
    """Return full path to the currently active PDF resume, or None"""
    resumes = _list_resume_files()
    if not resumes:
        return None
    return max(resumes, key=os.path.getmtime)

def send_email_smtp(receiver_email, subject, body, attachment_path=None):
    """Send email via SMTP"""
    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachment_path is not None:
        if not os.path.isfile(attachment_path):
            raise FileNotFoundError("Requested attachment file was not found")
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{Path(attachment_path).name}"')
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())

# API Routes

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/api/resume/upload', methods=['POST'])
def upload_resume():
    """Upload active PDF resume, replacing any previous active resume"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if not file or not file.filename or file.filename.strip() == '':
        return jsonify({"error": "No file selected"}), 400

    target_path = _resolve_safe_resume_path(file.filename)
    if not target_path:
        return jsonify({"error": "Invalid file type. Only PDF allowed"}), 400

    # Verify PDF magic header bytes (%PDF-) before modifying existing files
    header = file.stream.read(5)
    file.stream.seek(0)
    if header != b'%PDF-':
        return jsonify({"error": "Invalid PDF file content"}), 400

    os.makedirs(RESUME_FOLDER, exist_ok=True)
    temp_path = os.path.abspath(os.path.join(RESUME_FOLDER, f".upload_{int(time.time() * 1000)}.tmp"))
    try:
        file.save(temp_path)
        file_size = os.path.getsize(temp_path)
        if file_size == 0:
            os.remove(temp_path)
            return jsonify({"error": "Uploaded PDF file is empty"}), 400

        os.replace(temp_path, target_path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    # Enforce single active resume: remove any previous PDF resumes in RESUME_FOLDER
    target_norm = os.path.normcase(target_path)
    for existing_path in _list_resume_files():
        if os.path.normcase(existing_path) != target_norm:
            try:
                os.remove(existing_path)
            except OSError:
                pass

    filename = os.path.basename(target_path)
    file_size = os.path.getsize(target_path)
    uploaded_at = datetime.fromtimestamp(os.path.getmtime(target_path)).isoformat()

    return jsonify({
        "success": True,
        "name": filename,
        "filename": filename,
        "filepath": os.path.join(RESUME_FOLDER, filename),
        "size": _format_file_size(file_size),
        "uploadedAt": uploaded_at,
        "metadata": None
    })

@app.route('/api/resume', methods=['GET'])
def get_resume():
    """Get current active resume info"""
    active_path = _get_active_resume_path()
    if active_path:
        filename = os.path.basename(active_path)
        file_size = os.path.getsize(active_path)
        uploaded_at = datetime.fromtimestamp(os.path.getmtime(active_path)).isoformat()

        return jsonify({
            "name": filename,
            "filename": filename,
            "filepath": os.path.join(RESUME_FOLDER, filename),
            "size": _format_file_size(file_size),
            "uploadedAt": uploaded_at,
            "metadata": None
        })

    return jsonify({"error": "No resume found"}), 404

@app.route('/api/resume/<filename>', methods=['DELETE'])
def delete_resume(filename):
    """Delete active resume and clear any orphaned resume PDFs"""
    target_path = _resolve_safe_resume_path(filename)
    if not target_path:
        return jsonify({"error": "Invalid filename"}), 400

    if not os.path.isfile(target_path):
        return jsonify({"error": "File not found"}), 404

    os.remove(target_path)

    # Ensure no older orphaned PDF resumes remain active after deletion
    for remaining_path in _list_resume_files():
        try:
            os.remove(remaining_path)
        except OSError:
            pass

    return jsonify({"success": True})

@app.route('/api/campaigns', methods=['GET'])
def get_campaigns():
    """Get all campaigns"""
    campaigns = load_campaigns()
    return jsonify(campaigns)

@app.route('/api/campaigns', methods=['POST'])
def create_campaign():
    """Create a new campaign"""
    data = request.json or {}
    campaigns = load_campaigns()

    campaign_name = _clean_cell_value(data.get("name"))
    if not campaign_name:
        return jsonify({"error": "Campaign name is required"}), 400

    normalized_recipients = _normalize_recipients_list(data.get("recipients", []))
    if not normalized_recipients:
        return jsonify({"error": "At least one valid recipient email is required"}), 400

    new_campaign = {
        "id": int(time.time() * 1000),
        "name": campaign_name,
        "recipients": normalized_recipients,
        "attachResume": bool(data.get("attachResume", False)),
        "status": "draft",
        "createdAt": datetime.now().isoformat(),
        "emails": [],
        "stats": {
            "total": len(normalized_recipients),
            "sent": 0,
            "opened": 0,
            "replied": 0
        }
    }

    campaigns.append(new_campaign)
    save_campaigns(campaigns)

    return jsonify(new_campaign), 201

@app.route('/api/campaigns/<int:campaign_id>', methods=['GET'])
def get_campaign(campaign_id):
    """Get a specific campaign"""
    campaigns = load_campaigns()
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if campaign:
        return jsonify(campaign)
    return jsonify({"error": "Campaign not found"}), 404

@app.route('/api/campaigns/<int:campaign_id>/send', methods=['POST'])
def send_campaign(campaign_id):
    """Send emails for a campaign"""
    campaigns = load_campaigns()
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    
    if not campaign:
        return jsonify({"error": "Campaign not found"}), 404
    
    if not SENDER_EMAIL or not APP_PASSWORD:
        return jsonify({"error": "Email credentials not configured"}), 500
    
    # Load template
    template_path = "email_template.txt"
    if not os.path.exists(template_path):
        return jsonify({"error": "Email template not found"}), 500
    
    with open(template_path, "r", encoding="utf-8") as f:
        template = Template(f.read())
    
    # Resolve active resume path when attachment is enabled
    attach_resume_enabled = bool(campaign.get("attachResume", False))
    resume_path = None
    if attach_resume_enabled:
        resume_path = _get_active_resume_path()
        if not resume_path:
            return jsonify({
                "error": "Resume attachment is enabled for this campaign, but no resume is currently uploaded. Please upload a PDF resume in Profile & Resume first."
            }), 400

    # Update campaign status
    campaign["status"] = "sending"
    save_campaigns(campaigns)
    
    sent_count = 0
    failed_count = 0
    
    # Send emails
    for recipient in campaign.get("recipients", []):
        # Parse recipient (supports structured recipient dicts and legacy string recipients)
        parsed_recipient = _normalize_recipient_entry(recipient)
        if not parsed_recipient:
            continue

        email = parsed_recipient["email"]
        name = parsed_recipient["name"]
        company = parsed_recipient["company"]
        position = parsed_recipient["position"]
        industry = parsed_recipient["industry"]
        location = parsed_recipient["location"]

        # Prepare template context (populate recipient fields only when present so Jinja default() filters work)
        context = {
            "interest": "AI and Web Development",
            "skills": "Python, Machine Learning, and Web Development",
            "resume_attached": bool(resume_path),
        }
        if name:
            context["name"] = name
            context["Name"] = name
        if company:
            context["company_name"] = company
            context["company"] = company
            context["Company"] = company
        if position:
            context["position"] = position
            context["Position"] = position
        if industry:
            context["industry"] = industry
            context["Industry"] = industry
        if location:
            context["location"] = location
            context["Location"] = location

        rendered = template.render(**context)
        
        # Split subject and body
        if "\n\n" in rendered:
            subject_line, body = rendered.split("\n\n", 1)
        else:
            parts = rendered.split("\n", 1)
            subject_line = parts[0]
            body = parts[1] if len(parts) > 1 else ""
        
        subject = subject_line.replace("Subject:", "").strip()
        
        try:
            send_email_smtp(email, subject, body, resume_path)
            sent_count += 1
            campaign["stats"]["sent"] = sent_count

            # Log email
            email_record = {
                "id": int(time.time() * 1000) + sent_count,
                "recipient": email,
                "status": "sent",
                "resumeAttached": bool(resume_path),
                "sentAt": datetime.now().isoformat()
            }
            campaign["emails"].append(email_record)
            
            # Save to sent folder
            emails_data = load_emails()
            sent_email = {
                'id': int(time.time() * 1000) + sent_count,
                'subject': subject,
                'sender': SENDER_NAME,
                'email': email,
                'body': body,
                'preview': body[:100] + '...' if len(body) > 100 else body,
                'time': datetime.now().strftime('%b %d, %Y'),
                'date': datetime.now().isoformat(),
                'folder': 'sent',
                'read': True,
                'starred': False,
                'campaign_id': campaign_id
            }
            emails_data.setdefault('sent', []).insert(0, sent_email)
            save_emails(emails_data)
            
            # Delay between emails
            wait = random.uniform(DELAY_SECONDS_MIN, DELAY_SECONDS_MAX)
            time.sleep(wait)
            
        except Exception as e:
            failed_count += 1
            email_record = {
                "id": int(time.time() * 1000) + failed_count,
                "recipient": email,
                "status": "failed",
                "error": str(e),
                "sentAt": datetime.now().isoformat()
            }
            campaign["emails"].append(email_record)
    
    campaign["status"] = "completed"
    campaign["resumeAttached"] = bool(resume_path)
    save_campaigns(campaigns)

    return jsonify({
        "success": True,
        "sent": sent_count,
        "failed": failed_count,
        "resumeAttached": bool(resume_path),
        "campaign": campaign
    })

@app.route('/api/campaigns/<int:campaign_id>', methods=['DELETE'])
def delete_campaign(campaign_id):
    """Delete a campaign"""
    campaigns = load_campaigns()
    campaigns = [c for c in campaigns if c["id"] != campaign_id]
    save_campaigns(campaigns)
    return jsonify({"success": True})

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get analytics data"""
    campaigns = load_campaigns()
    
    total_campaigns = len(campaigns)
    total_sent = sum(c.get("stats", {}).get("sent", 0) for c in campaigns)
    total_opened = sum(c.get("stats", {}).get("opened", 0) for c in campaigns)
    total_replied = sum(c.get("stats", {}).get("replied", 0) for c in campaigns)
    
    return jsonify({
        "totalCampaigns": total_campaigns,
        "totalSent": total_sent,
        "totalOpened": total_opened,
        "totalReplied": total_replied,
        "openRate": (total_opened / total_sent * 100) if total_sent > 0 else 0,
        "replyRate": (total_replied / total_sent * 100) if total_sent > 0 else 0
    })

RECIPIENT_HEADER_ALIASES = {
    "email": [
        "email",
        "email address",
        "e-mail",
        "e-mail address",
        "mail",
        "recipient email",
        "contact email",
    ],
    "name": [
        "name",
        "full name",
        "recruiter name",
        "contact name",
        "recipient name",
        "person",
    ],
    "company": [
        "company",
        "company name",
        "organization",
        "organisation",
        "employer",
        "firm",
    ],
    "position": [
        "position",
        "role",
        "job title",
        "title",
        "target role",
        "designation",
    ],
    "industry": [
        "industry",
        "sector",
        "domain",
        "vertical",
    ],
    "location": [
        "location",
        "city",
        "country",
        "address",
        "region",
        "office",
    ],
}

def _clean_cell_value(val):
    """Convert cell/JSON value to clean string, handling NaN/None"""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    return str(val).strip()

def _normalize_header(col_name):
    """Normalize spreadsheet header by trimming, lowercasing, and collapsing whitespace"""
    if col_name is None:
        return ""
    return " ".join(str(col_name).strip().lower().split())

def _is_valid_recipient_email(email_addr):
    """Validate basic recipient email format and block header injection characters"""
    if not email_addr or "@" not in email_addr:
        return False
    if any(ch in email_addr for ch in ("\r", "\n", " ", "\t")):
        return False
    local_part, _, domain_part = email_addr.partition("@")
    return bool(local_part and domain_part and "." in domain_part)

def _normalize_recipient_entry(entry):
    """Normalize a string or dict recipient into canonical structured dict, or None if invalid"""
    if isinstance(entry, dict):
        normalized_map = {}
        for k, v in entry.items():
            norm_k = _normalize_header(k)
            cleaned_v = _clean_cell_value(v)
            if norm_k and cleaned_v and norm_k not in normalized_map:
                normalized_map[norm_k] = cleaned_v

        def pick(field):
            for alias in RECIPIENT_HEADER_ALIASES[field]:
                if normalized_map.get(alias):
                    return normalized_map[alias]
            return ""

        email_addr = pick("email")
        if not _is_valid_recipient_email(email_addr):
            return None

        name_val = pick("name")
        if not name_val:
            first = normalized_map.get("first name", "")
            last = normalized_map.get("last name", "")
            name_val = " ".join(part for part in (first, last) if part)

        return {
            "email": email_addr,
            "name": name_val,
            "company": pick("company"),
            "position": pick("position"),
            "industry": pick("industry"),
            "location": pick("location"),
        }

    if isinstance(entry, str):
        email_addr = _clean_cell_value(entry)
        if not _is_valid_recipient_email(email_addr):
            return None
        return {
            "email": email_addr,
            "name": "",
            "company": "",
            "position": "",
            "industry": "",
            "location": "",
        }

    return None

def _normalize_recipients_list(raw_recipients):
    """Normalize and deduplicate a list of recipients while preserving field values"""
    if not isinstance(raw_recipients, list):
        return []

    by_email = {}
    ordered_keys = []
    for item in raw_recipients:
        parsed = _normalize_recipient_entry(item)
        if not parsed:
            continue
        key = parsed["email"].lower()
        if key not in by_email:
            by_email[key] = parsed
            ordered_keys.append(key)
        else:
            existing = by_email[key]
            for field in ("name", "company", "position", "industry", "location"):
                if not existing[field] and parsed[field]:
                    existing[field] = parsed[field]

    return [by_email[k] for k in ordered_keys]

@app.route('/api/recipients/upload', methods=['POST'])
def upload_recipients():
    """Upload recipients CSV/Excel file"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if not file or not file.filename or file.filename.strip() == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        filename = secure_filename(file.filename)
        lower_name = filename.lower()
        if not filename or not lower_name.endswith(('.csv', '.xlsx', '.xls')):
            return jsonify({"error": "Unsupported file type. Use CSV or Excel files."}), 400

        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        if os.path.getsize(filepath) == 0:
            os.remove(filepath)
            return jsonify({"error": "Uploaded file is empty."}), 400

        # Read CSV or Excel
        try:
            if lower_name.endswith('.csv'):
                df = pd.read_csv(filepath)
            elif lower_name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath, engine='openpyxl')
            else:
                return jsonify({"error": "Unsupported file type. Use CSV or Excel files."}), 400
        except Exception as e:
            return jsonify({"error": f"Error reading file: {str(e)}"}), 400

        # Extract and normalize structured recipients using header alias mapping
        raw_rows = df.to_dict(orient='records')
        recipients = _normalize_recipients_list(raw_rows)

        return jsonify({
            "success": True,
            "recipients": recipients,
            "count": len(recipients)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Email scraping functions
# Scraping functions removed

@app.route('/api/template', methods=['GET'])
def get_template():
    """Get email template"""
    template_path = "email_template.txt"
    try:
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({"success": True, "content": content})
        else:
            return jsonify({"success": True, "content": ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/template', methods=['POST'])
def save_template():
    """Save email template"""
    data = request.json
    content = data.get('content', '')
    template_path = "email_template.txt"
    try:
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Gmail API Routes
@app.route('/api/gmail/auth', methods=['GET'])
def gmail_auth():
    """Initiate Gmail OAuth flow"""
    try:
        if not os.path.exists(CLIENT_SECRETS_FILE):
            error_msg = (
                "Gmail API credentials not found. Please:\n"
                "1. Go to Google Cloud Console\n"
                "2. Enable Gmail API\n"
                "3. Create OAuth 2.0 credentials\n"
                "4. Download as 'client_secret.json'\n"
                f"5. Place it in: {os.path.abspath('.')}"
            )
            return jsonify({"error": error_msg}), 400

        redirect_uri = request.host_url.rstrip('/') + '/api/gmail/callback'

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent screen to get refresh token
        )

        return jsonify({
            "auth_url": authorization_url,
            "state": state
        })
    except FileNotFoundError:
        error_msg = f"File not found: {CLIENT_SECRETS_FILE}. Please add client_secret.json to the project root."
        return jsonify({"error": error_msg}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to initiate Gmail authentication: {str(e)}"}), 500


@app.route('/api/email/send', methods=['POST'])
def send_single_email():
    """Send a single email with optional attachments"""
    try:
        sender_email = os.getenv("SENDER_EMAIL")
        app_password = os.getenv("APP_PASSWORD")
        sender_name = os.getenv("SENDER_NAME", "MAIL-CO User")

        if not sender_email or not app_password:
            return jsonify({"error": "Email credentials not configured in .env"}), 400

        data = request.form
        to_email = (data.get('to') or '').strip()
        subject = (data.get('subject') or '').strip()
        body = data.get('body') or ''

        if not to_email or not subject:
            return jsonify({"error": "Recipient and Subject are required"}), 400

        if '@' not in to_email or any(ch in to_email for ch in ('\r', '\n')) or any(ch in subject for ch in ('\r', '\n')):
            return jsonify({"error": "Invalid recipient email or subject"}), 400

        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Handle file attachments
        if 'files' in request.files:
            files = request.files.getlist('files')
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    if not filename:
                        continue
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(file.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{filename}"',
                    )
                    msg.attach(part)

        # Send email via SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)

        # Save to local storage (emails.json)
        emails_data = load_emails()
        new_email = {
            "id": f"sent_{int(time.time()*1000)}",
            "sender": "Me",
            "email": to_email,
            "subject": subject,
            "preview": body[:50] + "..." if len(body) > 50 else body,
            "time": datetime.now().strftime("%I:%M %p"),
            "date": datetime.now().isoformat(),
            "read": True,
            "starred": False,
            "folder": "sent",
            "body": body
        }
        emails_data.setdefault('sent', []).insert(0, new_email)
        save_emails(emails_data)

        return jsonify({"success": True, "message": "Email sent successfully"})

    except Exception as e:
        return jsonify({"error": f"Failed to send email: {str(e)}"}), 500

@app.route('/api/gmail/callback', methods=['GET'])
def gmail_callback():
    """Handle Gmail OAuth callback"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')

        if error:
            return jsonify({"error": f"Authorization failed: {error}"}), 400

        if not code:
            return jsonify({"error": "Authorization code not provided"}), 400

        if not os.path.exists(CLIENT_SECRETS_FILE):
            return jsonify({"error": f"File not found: {CLIENT_SECRETS_FILE}"}), 400

        redirect_uri = request.host_url.rstrip('/') + '/api/gmail/callback'

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            state=state,
            redirect_uri=redirect_uri
        )

        flow.fetch_token(code=code)
        creds = flow.credentials

        # Save credentials
        with open(CREDENTIALS_FILE, 'w') as token:
            token.write(creds.to_json())

        # Redirect / notify frontend with success message without exposing tokens
        frontend_url = os.getenv("FRONTEND_URL", request.host_url.replace(':5001', ':3000').rstrip('/'))
        safe_frontend_url = json.dumps(frontend_url)
        return (
            '<html><body><script>'
            f'var targetOrigin = {safe_frontend_url};'
            'if (window.opener) {'
            '  window.opener.postMessage({type: "gmail_connected", success: true}, targetOrigin);'
            '  window.close();'
            '} else {'
            '  window.location.href = targetOrigin;'
            '}'
            '</script><p>Gmail connected successfully! Redirecting...</p></body></html>',
            200
        )
    except Exception as e:
        return jsonify({"error": f"Failed to complete Gmail authentication: {str(e)}"}), 500

@app.route('/api/gmail/status', methods=['GET'])
def gmail_status():
    """Check if Gmail is connected"""
    service = get_gmail_service()
    if service:
        try:
            profile = service.users().getProfile(userId='me').execute()
            return jsonify({
                "connected": True,
                "email": profile.get('emailAddress', '')
            })
        except:
            return jsonify({"connected": False})
    return jsonify({"connected": False})

@app.route('/api/emails/sync', methods=['POST'])
def sync_emails():
    """Fetch emails from Gmail matching template subject"""
    service = get_gmail_service()
    if not service:
        return jsonify({"error": "Gmail not connected"}), 401
    
    try:
        emails_data = load_emails()
        subject_pattern = extract_template_subject_pattern()
        
        # Search for emails with matching subject
        query = f'subject:"{subject_pattern}"'
        
        # Get messages
        results = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
        messages = results.get('messages', [])
        
        new_emails = []
        sent_emails = []
        
        for msg in messages:
            try:
                message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                
                headers = message['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                to = next((h['value'] for h in headers if h['name'] == 'To'), '')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Parse date
                try:
                    parsed_date = email.utils.parsedate_to_datetime(date)
                    formatted_date = parsed_date.strftime('%b %d, %Y') if parsed_date else date
                except:
                    formatted_date = date
                
                # Extract body
                body = ''
                if 'parts' in message['payload']:
                    for part in message['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            data = part['body']['data']
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                            break
                elif message['payload'].get('body', {}).get('data'):
                    data = message['payload']['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                
                # Determine if it's sent or received using Gmail labels
                label_ids = message.get('labelIds', [])
                is_sent = 'SENT' in label_ids
                
                email_obj = {
                    'id': message['id'],
                    'gmail_id': message['id'],
                    'subject': subject,
                    'sender': sender.split('<')[0].strip() if '<' in sender else sender,
                    'email': sender.split('<')[1].split('>')[0] if '<' in sender else sender,
                    'body': body,
                    'preview': body[:100] + '...' if len(body) > 100 else body,
                    'time': formatted_date,
                    'date': date,
                    'folder': 'sent' if is_sent else 'inbox',
                    'read': 'UNREAD' not in message.get('labelIds', []),
                    'starred': 'STARRED' in message.get('labelIds', []),
                    'threadId': message.get('threadId', '')
                }
                
                if is_sent:
                    sent_emails.append(email_obj)
                else:
                    new_emails.append(email_obj)
                    
            except Exception as e:
                print(f"Error processing message {msg['id']}: {e}")
                continue
        
        # Merge with existing emails (avoid duplicates)
        existing_ids = {e.get('gmail_id') for e in emails_data.get('inbox', []) + emails_data.get('sent', [])}
        
        for email_obj in new_emails:
            if email_obj['gmail_id'] not in existing_ids:
                emails_data.setdefault('inbox', []).append(email_obj)
        
        for email_obj in sent_emails:
            if email_obj['gmail_id'] not in existing_ids:
                emails_data.setdefault('sent', []).append(email_obj)
        
        save_emails(emails_data)
        
        return jsonify({
            "success": True,
            "synced": len(new_emails) + len(sent_emails),
            "inbox": len(new_emails),
            "sent": len(sent_emails)
        })
        
    except HttpError as e:
        return jsonify({"error": f"Gmail API error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _normalize_email_record(item, default_folder='inbox'):
    """Ensure email/draft record has safe fields for frontend rendering"""
    if not isinstance(item, dict):
        return None
    normalized = dict(item)
    folder = normalized.get('folder') or default_folder
    normalized['folder'] = folder
    body_text = normalized.get('body') or ''
    normalized['body'] = body_text
    normalized['subject'] = normalized.get('subject') or '(no subject)'
    if not normalized.get('sender'):
        normalized['sender'] = normalized.get('to') or 'Draft' if folder == 'drafts' else 'Unknown'
    if not normalized.get('email'):
        normalized['email'] = normalized.get('to') or ''
    if 'preview' not in normalized or normalized.get('preview') is None:
        normalized['preview'] = (body_text[:100] + '...') if len(body_text) > 100 else body_text
    normalized['read'] = bool(normalized.get('read', folder != 'inbox'))
    normalized['starred'] = bool(normalized.get('starred', False))
    normalized['time'] = normalized.get('time') or ''
    return normalized

def _email_matches_id(email_obj, target_id):
    """Match email by id or gmail_id safely across string and integer IDs"""
    target_str = str(target_id)
    item_id = email_obj.get('id')
    gmail_id = email_obj.get('gmail_id')
    return (item_id is not None and str(item_id) == target_str) or (
        gmail_id is not None and str(gmail_id) == target_str
    )

@app.route('/api/emails', methods=['GET'])
def get_emails():
    """Get emails by folder ('inbox', 'sent', 'drafts', 'starred', or 'all')"""
    folder = (request.args.get('folder') or 'inbox').strip().lower()
    emails_data = load_emails()

    if folder in ('starred', 'all'):
        combined = []
        seen_keys = set()
        for f_name in ('inbox', 'sent', 'drafts'):
            for raw_item in emails_data.get(f_name, []):
                norm_item = _normalize_email_record(raw_item, default_folder=f_name)
                if not norm_item:
                    continue
                if folder == 'starred' and not norm_item.get('starred'):
                    continue
                dedup_key = f"{f_name}:{norm_item.get('gmail_id') or norm_item.get('id')}"
                if dedup_key not in seen_keys:
                    seen_keys.add(dedup_key)
                    combined.append(norm_item)
        return jsonify(combined)

    folder_items = [
        norm_item
        for raw_item in emails_data.get(folder, [])
        for norm_item in (_normalize_email_record(raw_item, default_folder=folder),)
        if norm_item is not None
    ]
    return jsonify(folder_items)

@app.route('/api/emails/<email_id>/star', methods=['POST'])
def toggle_star_email(email_id):
    """Toggle star status of an email"""
    service = get_gmail_service()
    emails_data = load_emails()

    # Find email across all folders (string/int safe ID comparison)
    matched_emails = []
    gmail_msg_id = None
    for f in ('inbox', 'sent', 'drafts'):
        for e in emails_data.get(f, []):
            if isinstance(e, dict) and _email_matches_id(e, email_id):
                matched_emails.append(e)
                if not gmail_msg_id and e.get('gmail_id'):
                    gmail_msg_id = e.get('gmail_id')

    if not matched_emails:
        return jsonify({"error": "Email not found"}), 404

    new_starred = not bool(matched_emails[0].get('starred', False))
    for e in matched_emails:
        e['starred'] = new_starred

    # Update in Gmail if connected
    if service and gmail_msg_id:
        try:
            if new_starred:
                service.users().messages().modify(
                    userId='me',
                    id=gmail_msg_id,
                    body={'addLabelIds': ['STARRED']}
                ).execute()
            else:
                service.users().messages().modify(
                    userId='me',
                    id=gmail_msg_id,
                    body={'removeLabelIds': ['STARRED']}
                ).execute()
        except Exception:
            pass  # Continue even if Gmail update fails

    save_emails(emails_data)
    return jsonify({"success": True, "starred": new_starred})

@app.route('/api/emails/<email_id>/read', methods=['POST'])
def toggle_read_email(email_id):
    """Toggle or explicitly set read status of an email"""
    service = get_gmail_service()
    emails_data = load_emails()
    payload = request.get_json(silent=True) or {}

    matched_emails = []
    gmail_msg_id = None
    for f in ('inbox', 'sent', 'drafts'):
        for e in emails_data.get(f, []):
            if isinstance(e, dict) and _email_matches_id(e, email_id):
                matched_emails.append(e)
                if not gmail_msg_id and e.get('gmail_id'):
                    gmail_msg_id = e.get('gmail_id')

    if not matched_emails:
        return jsonify({"error": "Email not found"}), 404

    if isinstance(payload.get('read'), bool):
        new_read = payload['read']
    else:
        new_read = not bool(matched_emails[0].get('read', False))

    for e in matched_emails:
        e['read'] = new_read

    # Sync UNREAD label in Gmail when connected
    if service and gmail_msg_id:
        try:
            if new_read:
                service.users().messages().modify(
                    userId='me',
                    id=gmail_msg_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
            else:
                service.users().messages().modify(
                    userId='me',
                    id=gmail_msg_id,
                    body={'addLabelIds': ['UNREAD']}
                ).execute()
        except Exception:
            pass  # Continue even if Gmail update fails

    save_emails(emails_data)
    return jsonify({"success": True, "read": new_read})

@app.route('/api/compose/send', methods=['POST'])
def send_composed_email():
    """Send email from compose window"""
    data = request.json
    to = data.get('to', '')
    subject = data.get('subject', '')
    body = data.get('body', '')
    attachments = data.get('attachments', [])  # Array of file paths
    
    if not to or not subject:
        return jsonify({"error": "To and Subject are required"}), 400
    
    if not SENDER_EMAIL or not APP_PASSWORD:
        return jsonify({"error": "Email credentials not configured"}), 500
    
    try:
        # Create email message
        msg = MIMEMultipart()
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        # Add attachments
        for attachment_path in attachments:
            if not attachment_path:
                continue
            resolved_path = os.path.abspath(attachment_path)
            allowed_dirs = (os.path.abspath(UPLOAD_FOLDER), os.path.abspath(RESUME_FOLDER))
            if not any(resolved_path.startswith(d + os.sep) for d in allowed_dirs):
                return jsonify({"error": "Invalid attachment path"}), 400
            if os.path.exists(resolved_path) and os.path.isfile(resolved_path):
                with open(resolved_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{Path(resolved_path).name}"')
                msg.attach(part)
        
        # Send email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, to, msg.as_string())
        
        # Save to sent folder
        emails_data = load_emails()
        sent_email = {
            'id': int(time.time() * 1000),
            'subject': subject,
            'sender': SENDER_NAME,
            'email': to,
            'body': body,
            'preview': body[:100] + '...' if len(body) > 100 else body,
            'time': datetime.now().strftime('%b %d, %Y'),
            'date': datetime.now().isoformat(),
            'folder': 'sent',
            'read': True,
            'starred': False
        }
        emails_data.setdefault('sent', []).insert(0, sent_email)
        save_emails(emails_data)
        
        return jsonify({"success": True, "message": "Email sent successfully"})
        
    except Exception as e:
        # Save to drafts on failure
        emails_data = load_emails()
        draft = {
            'id': int(time.time() * 1000),
            'subject': subject,
            'to': to,
            'body': body,
            'attachments': attachments,
            'time': datetime.now().strftime('%b %d, %Y'),
            'folder': 'drafts',
            'error': str(e)
        }
        emails_data.setdefault('drafts', []).insert(0, draft)
        save_emails(emails_data)
        
        return jsonify({"error": f"Failed to send email: {str(e)}"}), 500

@app.route('/api/compose/upload', methods=['POST'])
def upload_compose_attachment():
    """Upload attachment for compose window"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if not file or not file.filename or file.filename.strip() == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({"error": "Invalid filename"}), 400
        filepath = os.path.join(UPLOAD_FOLDER, f"compose_{int(time.time())}_{filename}")
        file.save(filepath)

        return jsonify({
            "success": True,
            "filepath": filepath,
            "filename": filename
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/drafts', methods=['GET'])
def get_drafts():
    """Get all drafts"""
    emails_data = load_emails()
    return jsonify(emails_data.get('drafts', []))

@app.route('/api/drafts/<draft_id>', methods=['DELETE'])
def delete_draft(draft_id):
    """Delete a draft"""
    emails_data = load_emails()
    drafts = emails_data.get('drafts', [])
    emails_data['drafts'] = [d for d in drafts if str(d.get('id')) != str(draft_id)]
    save_emails(emails_data)
    return jsonify({"success": True})

if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="127.0.0.1", debug=debug_mode, port=5001)

