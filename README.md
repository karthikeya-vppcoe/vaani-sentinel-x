
# Vaani Sentinel X

Vaani Sentinel X is an AI-integrated, voice-first platform that autonomously generates platform-specific content (tweets, Instagram posts, and voice scripts) from structured knowledge, schedules social media posts, and ensures security through content verification and encryption. It serves as a blueprint for building secure, scalable, and modular AI systems for real-time public interaction. It is designed with multilingual capabilities (initially Hindi and Sanskrit, with plans to include more vernacular Indian languages) and aims to be a production-grade autonomous system featuring adaptive publishing and smarter moderation. Vaani Sentinel X is a critical building block of the Sanatan AI Engine.


## 🧠 Project Overview

Vaani Sentinel X implements a modular, agent-based system managed via a command-line interface (CLI) and a secure web interface.
The system prioritizes backend intelligence, security, modularity, and voice-driven interaction. It is evolving into a multilingual, production-grade autonomous system with adaptive publishing and smarter moderation, playing a key role in the Sanatan AI Engine.


## Key Features:

 - Structured content mining from raw data.
 - AI-driven content generation (text + voice).
 - Multilingual content ingestion and processing (Hindi, Sanskrit, and planned vernacular Indian languages).
 - Automatic language detection.
 - Adaptive AI writing style (formal, casual, devotional).
 - Dynamic TTS voice selection based on language.
 - Sentiment tuning (uplifting, neutral, devotional).
 - Context-aware platform targeting (hashtags, post formats, audio lengths).
 - Secure scheduling and simulated publishing.
 - Web UI for monitoring, playback, and alert handling (with optional display of language and sentiment metadata).
 - Security modules for content flagging, encryption, and emergency data wiping.
 - Basic detection of harmful religious bias triggers.
 - Encryption of multilingual archives separately by language.
 - Checksum generation for archives.
 - Enhanced CLI for manual agent control, process logs, and pipeline management.


## Folder Structure

```bash
vaani-sentinel-x/
 ├── agents/
 │   ├── miner_sanitizer.py         # Agent A: Sanitizes and structures raw data
 │   ├── ai_writer_voicegen.py      # Agent B: Generates tweets, posts, and TTS
 │   ├── scheduler.py               # Agent D: Schedules posts
 │   ├── publisher_sim.py           # Agent D: Simulates publishing
 │   ├── security_guard.py          # Agent E: Flags and encrypts content
 │   ├── multilingual_pipeline.py   # Handles multilingual content processing
 │   ├── sentiment_tuner.py         # Adjusts content sentiment
 │   └── adaptive_targeter.py       # Adapts content for specific platforms
 ├── web-ui/
 │   └── nextjs-voice-panel/        # Agent C: Secure Next.js UI
 ├── cli/
 │   └── command_center.py          # CLI Command Center
 ├── content/
 │   ├── raw/                       # Raw input files
 │   ├── structured/                # Structured content blocks
 │   ├── content_ready/             # Generated content (tweets, posts, TTS)
 │   └── multilingual_ready/        # Processed multilingual content
 ├── logs/                          # Security and process logs
 ├── scheduler_db/                  # Scheduled posts database
 ├── archives/
 │   ├── encrypted_eng/             # Encrypted English content archives
 │   ├── encrypted_hin/             # Encrypted Hindi content archives
 │   └── encrypted_san/             # Encrypted Sanskrit content archives
 ├── kill_switch.py                 # Emergency data wipe
 └── README.md                      # Project documentation
```


## 🤖 Agents and Their Functions

| Agent | File     | Purpose                |
| :-------- | :------- | :------------------------- |
| Agent A | `miner_sanitizer.py` | Sanitizes and structures raw CSV data into verified JSON content blocks. |
| Agent B | `ai_writer_voicegen.py` | Enhances content generation with adaptive styles (Formal for LinkedIn, Casual for Instagram, Neutral/Devotional for Sanatan voice assistants). Features dynamic TTS voice selection (Hindi/Sanskrit/English) using services like ElevenLabs Multilingual or Google Cloud TTS. Generates tweets, posts, voice scripts, and MP3s. |
| Agent C | `web-ui/nextjs-voice-panel` | Next.js-based UI for viewing, downloading, and playing content with security dashboards. |
| Agent D | `scheduler.py`, `publisher_sim.py` | Schedules posts. `publisher_sim.py` simulates publishing to mock social media endpoints, working with Agent I for platform-specific adaptations. |
| Agent E | `security_guard.py` | Flags controversial content, encrypts archives (including per-language encryption for multilingual content with checksums), logs alerts, provides a kill switch, and includes basic detection of harmful religious bias triggers. |
| Agent F | `multilingual_pipeline.py` | Expands Agent A to handle Hindi and Sanskrit text ingestion. Adds automatic language detection and auto-routes content for multilingual processing. |
| Agent H | `sentiment_tuner.py` | New micro-agent to adjust sentiment (uplifting, neutral, devotional) of content before final generation. Sentiment tuning options selectable at runtime. |
| Agent I | `adaptive_targeter.py` | Tailors hashtags, post formats, and audio lengths according to the platform (Instagram, Twitter, Spotify) when `publisher_sim.py` simulates posts. |



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
(https://github.com/karthikeya-vppcoe/vaani-sentinel-x.git)
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
   Remember to install these in your root directory (`vaani-sentinel-x/`). If any errors are encountered, consider creating a new virtual environment (venv) if the current one seems corrupted, and then reinstall the dependencies.
```pip install requests textblob python-dotenv gtts groq datetime better_profanity cryptography.fernet ```
- If any dependencies are still missing after this step, please install them manually.

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
You can manage and run the system components via the Command Center CLI (`cli/command_center.py`):

| Command | Action     | 
| :-------- | :------- | 
| `python cli/command_center.py sanitize` | Processes raw input data and structures it into content blocks. | 
| `python cli/command_center.py generate` | Generates platform-specific content (tweets, posts, voice scripts) and TTS audio files. |
| `python cli/command_center.py security process` | Flags controversial content, encrypts archives, and logs security-related events. |
| `python cli/command_center.py schedule` | Schedules the generated content for future publishing. |
| `python cli/command_center.py publish` | Simulates the publishing of scheduled content to mock social media endpoints. |
| `python cli/command_center.py run <agent_script_name>` | Manually execute a specific agent script located in the `agents/` directory (e.g., `miner_sanitizer.py`). |
| `python cli/command_center.py logs view [--agent <agent_name>] [--lines N]` | View detailed process logs. Can be filtered by agent and show the last N lines. |
| `python cli/command_center.py pipeline <status|kill|restart> [--pipeline_id ID]` | Manage running pipelines or agents (e.g., check status, kill, or restart). |

Note: Replace `<agent_script_name>`, `<agent_name>`, `N`, `<status|kill|restart>`, and `ID` with actual values as appropriate. The exact subcommands and parameters for logs and pipeline management might vary based on implementation.

## 🖥️ Web Interface Usage

- Content Tab: View, play, and download tweets, posts, and TTS files.
- Dashboard Tab: View content ethics, virality, and neutrality scores.
- Alerts Tab: See flagged/controversial content.

## 🛡️ Security Features
- JWT Authentication: Secures frontend and backend communication.
- Content Flagging: Detects and flags sensitive/controversial material.
- Encryption: Archives and encrypts content to protect sensitive data.
- Kill Switch: ```kill_switch.py``` wipes critical data in case of security breaches.

## 💻 Technology Stack

**Frontend:**
- Next.js (`next`): React framework for server-rendered applications.
- React.js (`react`): Library for building user interfaces.
- Express.js (`express`): Used by Next.js for its backend API routes and server.
- `cors`: Middleware for enabling Cross-Origin Resource Sharing.
- `dotenv`: For managing environment variables in the frontend build/dev process.

**Backend:**
- **Language:** Python
- **Frameworks/Platforms (Potential):** FastAPI, Flask, Supabase
- **Core Libraries:**
  - `requests`: For making HTTP requests.
  - `python-dotenv`: For managing environment variables.
  - `glob`, `pathlib`: For file system interactions and path manipulations.
  - `sqlite3`: Default local database for scheduling and data storage.
  - `gtts`: Google Text-to-Speech Python library for basic voice generation.
  - `groq`: Client library for accessing Groq AI inference services.
  - `better_profanity`: For filtering out profane content.
  - `datetime`: For handling dates and times, crucial for scheduling.
  - `cryptography.fernet`: For encryption/decryption of sensitive data (listed under Security as well).

**Voice Generation:**
- ElevenLabs Multilingual API: For high-quality, multilingual text-to-speech.
- Google Cloud Text-to-Speech: Cloud-based TTS service for natural-sounding voices.
- `gtts`: Python library for simpler, offline/free TTS needs.

**AI Models & Natural Language Processing (NLP):**
- **AI Models:**
  - OpenAI GPT-4 (accessed via API): Advanced models for content generation.
  - Local LLMs via Ollama: For running language models locally.
  - Models accessible via Groq API: For fast inference.
- **NLP Libraries:**
  - `textblob`: For sentiment analysis, language detection (basic), and other NLP tasks.
  - `langdetect` / `fasttext` (potential additions): For more robust language detection.

**Security:**
- **Authentication:** `jsonwebtoken`: For creating and verifying JWTs to secure APIs and sessions.
- **Content Moderation:**
  - Regex: For rule-based pattern matching to flag content.
  - Basic ML Flagging: Utilizing libraries like `textblob` for sentiment-based flagging or custom ML models.
  - `better_profanity`: For proactive filtering of unwanted terms.
- **Encryption:** `cryptography.fernet`: For strong symmetric encryption of stored data, particularly archives.

**DevOps & Databases:**
- **Version Control:** Git, GitHub
- **Databases:**
  - Local: SQLite3 (current default)
  - Cloud-based (potential): Supabase (PostgreSQL-based), MongoDB
- **Environment Management:** `python-dotenv` (backend), `dotenv` (frontend) for consistent configuration.

## Phase 2: "Pravaha" (Flow) — Key Upgrades

This phase focuses on enhancing the system's intelligence, multilingual capabilities, and operational control, moving towards a more adaptive and robust platform.

1.  **Agent F: Multilingual Content Pipeline**
    *   Expand Agent A (Knowledge Miner) to handle Hindi and Sanskrit text ingestion.
    *   Implement automatic language detection (e.g., using `langdetect` or `fasttext`).
    *   Develop mechanisms to auto-route content for distinct multilingual processing pipelines.

2.  **Agent G: Adaptive AI Writer and Voice Generator**
    *   Enhance Agent B (AI Writer) to adapt writing style based on context:
        *   Formal tone for platforms like LinkedIn.
        *   Casual and engaging tone for platforms like Instagram.
        *   Neutral or devotional tone suitable for Sanatan voice assistants.
    *   Enable dynamic Text-To-Speech (TTS) voice selection based on the detected language (e.g., specific voices for Hindi, Sanskrit, English).
    *   Integrate with advanced TTS services like ElevenLabs Multilingual API, with a fallback to Google Cloud Text-to-Speech.

3.  **Agent H: Sentiment Tuner**
    *   Introduce a new micro-agent or module for sentiment adjustment.
    *   Allow runtime selection (via CLI or API parameter) to adjust the emotional tone of the content (e.g., uplifting, neutral, devotional) before final generation.

4.  **Agent I: Context-Aware Platform Targeter**
    *   Improve the post simulation capabilities (`publisher_sim.py`) to be platform-aware:
        *   Tailor hashtags, post formats (e.g., character limits, use of emojis), and audio content (e.g., intro/outro for Spotify) based on the target platform (Instagram, Twitter, Spotify, etc.).

5.  **Security + Compliance Layer Upgrade**
    *   Expand Agent E (Security Guard) functionalities:
        *   Implement basic detection of harmful religious bias triggers (initially simulated with predefined dummy cases).
        *   Encrypt multilingual content archives separately for each language.
        *   Generate and store checksums for each encrypted archive to ensure data integrity.

6.  **Dashboard and CLI Upgrades**
    *   **(Optional)** Enhance the web UI (Agent C) to display metadata such as detected language and applied sentiment for generated content.
    *   Develop an enhanced Command Line Interface (CLI) - `cli/command_center.py` - to:
        *   Allow manual execution of individual agents or specific pipeline stages.
        *   Provide access to detailed process logs.
        *   Offer commands to manage (e.g., kill, restart) running pipelines or agents.

### Phase 2 Implementation Notes

This section provides a summary of key deliverables and development aspects related to the Phase 2 "Pravaha" upgrades.

*   **New Agents Added:** The new agents (F, G, H, I) introduced in Phase 2, along with their specific functionalities and purposes, are detailed in the "🤖 Agents and Their Functions" table and within the "Phase 2: 'Pravaha' (Flow) — Key Upgrades" descriptions above. These include agents for multilingual processing, adaptive AI writing and voice generation, sentiment tuning, and context-aware platform targeting.

*   **Libraries Used:** The "💻 Technology Stack" section has been comprehensively updated to reflect all libraries, tools, and platforms utilized for both the initial system development and the enhancements implemented in Phase 2. This includes additions for multilingual support, advanced AI models, and more capable voice generation.

*   **Blockers, Challenges, and Improvements (Phase 2):**
    *   [Challenge] Integrating multilingual support (Hindi, Sanskrit) across the entire content pipeline, from ingestion to generation and security, required careful data handling, library selection (e.g., for language detection, TTS), and model fine-tuning.
    *   [Improvement] The development of the new Command Center CLI (`cli/command_center.py`) significantly improved modularity and control over individual agents and pipeline stages, streamlining testing and operational management.
    *   [Blocker] Initial testing of the sentiment analysis models for nuanced devotional content sometimes required iterative fine-tuning of parameters and potential custom training data to achieve desired accuracy.
    *   [Challenge] Ensuring consistent adaptive AI writing styles (formal, casual, devotional) and appropriate dynamic TTS voice selection across different languages and content types involved complex logic and robust testing.
    *   [Improvement] Enhanced security measures, including per-language encryption of archives and checksum generation, were successfully implemented, increasing data integrity and protection.
    *   [Placeholder for other specific challenges, blockers resolved, or improvements made during Phase 2 development.]

    *(Note: This subsection should be updated with actual experiences and specific details upon completion or during the course of Phase 2 development.)*

## 🐛 Blockers Faced & Resolutions

| Issue                                                        | Resolution                                                                                                     |
| :----------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------- |
| Connection Refused Errors during publishing                | Made sure backend server (`npm run server`) was running before executing `cli/command_center.py publish`.        |
| 403 Forbidden Errors when publisher accesses protected routes | Publisher simulation initially used a mock token; fixed by updating `publisher_sim.py` to request a real JWT token via `/api/login`. |
| Audio Playback/Download Fails from Web UI                    | Updated `ContentPanel.tsx` in the Next.js frontend to correctly attach JWT tokens to download/play requests.   |

# A video demo (screen recording, 3–5 min) 
- [Demo_vedio](https://drive.google.com/file/d/1uufq7AhntUgNRRM_9cAvrRg55PkJ53ks/view?usp=sharing)

## 🚀 Future Improvements
- Replace SQLite with PostgreSQL for production-grade scalability.
- Add a "Run Full Pipeline" button in the frontend.
- Integrate a more powerful LLM for enhanced content generation.
