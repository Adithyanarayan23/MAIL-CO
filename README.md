# 📧 MAIL-CO: Local Cold Email Outreach Platform

MAIL-CO is a privacy-focused cold email outreach application that runs locally on your machine. It allows you to manage outreach campaigns, personalize templates, attach resumes, and track replies directly with your Gmail account.

## ✨ Features

- **🏠 100% Local**: Your data stays on your computer.
- **📩 Gmail Integration**: Send emails using your own Gmail account via App Passwords.
- **🔄 Smart Inbox**: Syncs your Gmail inbox to show replies relevant to your outreach campaigns.
- **📄 Resume Attachment**: Upload your PDF resume once, and automatically attach it to campaign emails.
- **✍️ Dynamic Templates**: Personalize email templates using Jinja2 syntax (e.g., `{{ company_name }}`, `{{ position }}`).
- **📊 Campaign Management**: Create campaigns, upload CSV/Excel recipient lists, and track outreach metrics.
- **⭐ Starred & Drafts**: Manage important conversations directly from the app.

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+**: [Download Here](https://www.python.org/downloads/)
- **Node.js & npm**: [Download Here](https://nodejs.org/en/download/)

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/Adithyanarayan23/MAIL-CO.git
cd MAIL-CO

# Install Backend requirements
pip install -r requirements.txt

# Install Frontend dependencies
npm install
```

### 2. Configuration (`.env`)

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   # Or on Windows PowerShell:
   # Copy-Item .env.example .env
   ```
2. Open `.env` and fill in your details:
   ```ini
   SENDER_EMAIL=your.email@gmail.com
   APP_PASSWORD=xxxx xxxx xxxx xxxx
   SENDER_NAME=Adithya Narayan
   ```

   **🔍 How to get a Gmail App Password:**
   1. Go to your [Google Account Security](https://myaccount.google.com/security) settings.
   2. Enable **2-Step Verification**.
   3. Search for **App passwords**.
   4. Create a new app password named **MAIL-CO**.
   5. Copy the 16-character code into your `.env` file.

### 3. Google OAuth Setup (For Inbox Sync)

To sync your inbox and read replies, place a `client_secret.json` file from Google Cloud in the project root:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a **New Project** and enable the **Gmail API**.
3. Go to **Credentials** → **Create Credentials** → **OAuth Client ID** (Web application or Desktop app) and add `http://localhost:5001/api/gmail/callback` to Authorized Redirect URIs.
4. Download the JSON file, rename it to `client_secret.json`, and place it in the root folder of this project.

### 4. Running the App

Open two terminals:

**Terminal 1 (Backend):**
```bash
python app.py
```

**Terminal 2 (Frontend):**
```bash
npm run dev
```

The app will open at `http://localhost:3000`.
