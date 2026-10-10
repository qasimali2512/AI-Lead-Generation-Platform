# SoftPeak Technologies
## AI Lead Generation & Business Outreach Platform

An AI-powered platform designed to discover businesses, analyze their websites, identify potential improvement opportunities, and prepare personalized business outreach emails.

The platform combines a React frontend with a FastAPI backend and AI-assisted workflows to manage leads, campaigns, email drafts, and scheduled outreach.

---

## ✨ Key Features

- **Business Discovery** — Find businesses by country, location, and industry using supported data sources.
- **Lead Management** — Save, review, qualify, and organize discovered leads.
- **Website Analysis** — Scan business websites and identify potential technical, SEO, performance, and usability issues where measurable.
- **Website Opportunities** — Identify businesses without a detected website for relevant website-development outreach.
- **AI-Powered Emails** — Generate personalized email drafts based on available business data and verified findings.
- **Campaign Management** — Select leads, configure campaigns, and manage campaign status.
- **Email Account Management** — Connect authorized sending accounts when provider integration is configured.
- **Email Queue** — Organize approved emails for scheduled processing.
- **Follow-Up Workflows** — Support follow-up planning and campaign tracking.
- **Analytics & Notifications** — Review available campaign activity and application notifications.

> Feature availability depends on backend integration, configured credentials, database setup, and deployment environment.

---

## 🧰 Technology Stack

### Frontend
- React
- Vite
- JavaScript
- Axios
- React Router
- Tailwind CSS

### Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Uvicorn

### Database & Authentication
- Supabase
- PostgreSQL
- Supabase Authentication

### AI & Automation
- Cloudflare Workers AI
- Background workers and scheduling
- Email queue processing

### Deployment
- GitHub for source control
- AWS for backend hosting and background processing
- DuckDNS for a free subdomain
- Vercel for frontend hosting

---

## 🏗️ Architecture

```text
                  Users
                    |
                    v
            React Frontend
               (Vercel)
                    |
                    v
            FastAPI Backend
                (AWS)
              /    |    \
             v     v     v
        Supabase   AI   Email Queue
        PostgreSQL       |
                         v
                  Background Worker
                         |
                         v
                Authorized Email Provider
```

The frontend communicates with the backend API. Background workers and scheduling services are intended to process eligible queued tasks independently of the user's computer.

---

## 📁 Project Structure

```text
AI-Lead-Generation-Platform/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── services/
│   │   └── assets/
│   ├── package.json
│   └── .env.example
├── .gitignore
└── README.md
```

The exact folders may vary according to the current implementation.

---

## 🚀 Local Development

### Prerequisites

- Python installed
- Node.js and npm installed
- Git installed
- A configured Supabase project
- Required AI and email-provider credentials for the features you want to test

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd AI-Lead-Generation-Platform
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your actual repository URL.

### 2. Configure the backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file using the project's actual environment-variable requirements. Never commit real credentials.

Start the API from the backend directory:

```powershell
uvicorn app.main:app --reload
```

Open the interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### 3. Configure the frontend

Open another terminal:

```powershell
cd frontend
npm install
```

Create the frontend environment file using the variable names expected by the existing API client.

For a local backend, the API base URL may be:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Start the development server:

```powershell
npm run dev
```

Use the local URL printed by Vite in the terminal.

---

## ☁️ Deployment Plan

### Backend — AWS

The production backend is intended to run on AWS with:

- FastAPI API service
- HTTPS through a reverse proxy
- DuckDNS hostname pointing to the server
- Background worker for queued tasks
- Scheduler for due tasks
- Persistent database connectivity
- Secure environment variables and logging

### Frontend — Vercel

The frontend can be deployed from the GitHub repository to Vercel.

Configure the production API base URL using the environment-variable name expected by the frontend code.

### Database — Supabase

Configure the production Supabase project and apply the SQL migrations required by the application.

Never expose the Supabase secret/service-role key in frontend code.

> Deployment is complete only after API connectivity, authentication, database access, background processing, and email delivery have been tested.

---

## 🔐 Security & Responsible Outreach

- Keep API keys, OAuth secrets, database passwords, and tokens out of Git.
- Use authorized email accounts and respect provider sending limits.
- Use verified, relevant business information when generating outreach.
- Do not invent website issues, business facts, or performance metrics.
- Respect unsubscribe requests and maintain suppression lists.
- Handle bounces and complaints appropriately.
- Follow applicable privacy, data-protection, and anti-spam requirements.
- Use HTTPS for production traffic.
- Restrict access to campaign and account data.

---

## 🧪 Testing Checklist

- [ ] Backend starts successfully.
- [ ] Frontend builds and starts successfully.
- [ ] Authentication works.
- [ ] Database connectivity works.
- [ ] Business discovery returns valid results.
- [ ] Website analysis handles unavailable websites safely.
- [ ] AI drafts use available evidence.
- [ ] Email approval and queue processing work.
- [ ] Authorized email sending works.
- [ ] Scheduled tasks run when the laptop is offline.
- [ ] Failures, bounces, and opt-outs are handled correctly.

---

## 📌 Project Status

This repository is under active development. Production readiness depends on the completion and verification of the integrations described above.

## 📄 License

Choose and add a suitable license before distributing this project publicly.

---

**Built for SoftPeak Technologies**
