
# Vaani Sentinel X

Vaani Sentinel X is an AI-integrated, voice-first platform that autonomously generates platform-specific content (tweets, Instagram posts, and voice scripts) from structured knowledge, schedules social media posts, and ensures security through content verification and encryption. It serves as a blueprint for building secure, scalable, and modular AI systems for real-time public interaction.


## 🧠 Project Overview

Vaani Sentinel X implements a modular, agent-based system managed via a command-line interface (CLI) and a secure web interface.
The system prioritizes backend intelligence, security, modularity, and voice-driven interaction.


## Key Features:

 - Structured content mining from raw data.
 - AI-driven content generation (text + voice)
 - Secure scheduling and simulated publishing.
 - Web UI for monitoring, playback, and alert handling.
 - Security modules for content flagging, encryption, and emergency data wiping.


## Folder Structure

```bash
  vaani-sentinel-x/
 ├── agents/
 │   ├── miner_sanitizer.py         # Agent A: Sanitizes and structures raw data
 │   ├── ai_writer_voicegen.py      # Agent B: Generates tweets, posts, and TTS
 │   ├── scheduler.py               # Agent D: Schedules posts
 │   ├── publisher_sim.py           # Agent D: Simulates publishing
 │   └── security_guard.py          # Agent E: Flags and encrypts content
 ├── web-ui/
 │   └── nextjs-voice-panel/        # Agent C: Secure Next.js UI
 ├── content/
 │   ├── raw/                       # Raw input files
 │   ├── structured/                # Structured content blocks
 │   └── content_ready/             # Generated content (tweets, posts, TTS)
 ├── logs/                          # Security logs
 ├── scheduler_db/                  # Scheduled posts database
 ├── cli.py                         # CLI Command Center
 ├── kill_switch.py                 # Emergency data wipe
 └── README.md                      # Project documentation
```


## 🤖 Agents and Their Functions

| Agent | File     | Purpose                |
| :-------- | :------- | :------------------------- |
| Agent A | `miner_sanitizer.py` | Sanitizes and structures raw CSV data into verified JSON content blocks|
| Agent B | `ai_writer_voicegen.py` | Generates tweets (≤280 chars), Instagram/LinkedIn posts, voice scripts, and TTS (MP3). |
| Agent C | `web-ui/nextjs-voice-panel` | Next.js-based UI for viewing, downloading, and playing content with security dashboards. |
| Agent D | `scheduler.py , publisher_sim.py` | Schedules posts and simulates publishing to mock social media endpoints. |
| Agent E | `security_guard.py` | Flags controversial content, encrypts archives, logs alerts, and provides a kill switch. |



## Setup Instructions
**Prerequisites**
 - Python: 3.8 or higher
 - Node.js: v16 or higher
 - NPM: (comes with Node.js)
 - SQLite: Lightweight database
 - Git: Version control

**Installation Steps**
1) Clone the Repository
```bash
git clone https://github.com/your-username/vaani-sentinel-x.git
cd vaani-sentinel-x
```
2) Set Up Environment Variables
- Create ```.env``` in the root ```(vaani-sentinel-x/)```
```bash
GROQ_API_KEY=your-groq-api-key
```
- Create ```.env``` in  ```web-ui/nextjs-voice-panel/```
```
JWT_SECRET=your-jwt-secret
PORT=5000
SECRET_KEY=your-secret-key
```
3) Install Backend Dependencies
```pip install requests textblob python-dotenv gtts groq datetime better_profanity cryptography.fernet ```
- And if there are still any missing to install,install them

4) Install Frontend Dependencies
```cd web-ui/nextjs-voice-panel - npm install```

5) Run the Backend Server
```npm run server```
- Backend runs at: http://localhost:5000

6) Run the Frontend
```npm run dev``` Frontend runs at: http://localhost:3000
Login credentials:
- Email: ```test@vaani.com```
- Password:  ```password123```


## 🛠️ Running the System
You can run the whole pipeline via CLI commands:
| Command | Action     | 
| :-------- | :------- | 
| `python cli.py sanitize` | Processes raw CSV and structures the content. | 
| `python cli.py generate` | Generates tweets, posts, voice scripts, and TTS files. 
| `python -u "e:\..\..\agents\security_guard.py"` | Flags and encrypts content. |
| `python cli.py schedule` | Schedules posts for publishing. |
| `python cli.py publish` | Simulates publishing posts to mock endpoints. |

- ( Run this security_guard.py **individually** because it has an library based error mostly difficult to fix so only this one like e.g (python -u "e:\projects\vaani-sentinel-x\agents\security_guard.py") )

## 🖥️ Web Interface Usage

- Content Tab: View, play, and download tweets, posts, and TTS files.
- Dashboard Tab: View content ethics, virality, and neutrality scores.
- Alerts Tab: See flagged/controversial content.

## 🛡️ Security Features
- JWT Authentication: Secures frontend and backend communication.
- Content Flagging: Detects and flags sensitive/controversial material.
- Encryption: Archives and encrypts content to protect sensitive data.
- Kill Switch: ```kill_switch.py``` wipes critical data in case of security breaches.

## 📚 Libraries Used
**Python Backend**
- ```requests```: For HTTP requests to endpoints.
- ```textblob```: Sentiment analysis for neutrality scoring.
- ```sqlite3```: Local database for scheduling posts.
- ```python-dotenv```: Load environment variables.
- ```glob, pathlib```: For file handling and management.
**Frontend**
- ```next```: Next.js framework.
- ```react```: Building UI components.
- ```jsonwebtoken```: Secure authentication using JWT.
- ```express```: Backend server for APIs.
- ```cors```: Enable Cross-Origin Resource Sharing.
- ```dotenv```: Manage environment variables.

## 🐛 Blockers Faced & Resolutions
| Issue | Resolution     | 
| :-------- | :------- | 
| Issue	Resolution Connection Refused Errors during publishing | Made sure backend server (`npm run server`) was running before executing cli.py publish.|
| 403 Forbidden Errors | Publisher used a mock token; fixed by updating `publisher_sim.py` to request a real JWT token via /api/login.|
| Audio Playback/Download Fails |Updated `ContentPanel.tsx` to correctly attach JWT tokens to download/play requests.|

## 🚀 Future Improvements
- Replace SQLite with PostgreSQL for production-grade scalability.
- Add a "Run Full Pipeline" button in the frontend.
- Integrate a more powerful LLM for enhanced content generation.