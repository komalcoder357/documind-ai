# DocuMind AI — Intelligent Document Understanding

**An AI-powered document intelligence platform for evidence-grounded question answering, CV analysis, job matching, and candidate comparison.**

DocuMind AI is a full-stack application designed to help users extract information from documents, ask questions about their content, retrieve supporting evidence, and evaluate CVs against job-related criteria.

The project explores how document processing, Retrieval-Augmented Generation (RAG), evidence validation, and AI-assisted analysis can be combined in a practical application.

> **Project status:** Under active development. Features and integrations should be evaluated against the current implementation and test results.

## Key Features

- **Document processing:** Upload and process supported document formats, including PDF, DOCX, and TXT.
- **Document question answering:** Ask questions about uploaded documents and retrieve relevant passages.
- **Evidence-grounded responses:** Associate answers with supporting document excerpts and citation information.
- **RAG pipeline:** Retrieve relevant document chunks to support document-based questions.
- **Citation validation:** Validate references and reject unsupported or invalid citations.
- **CV analysis:** Evaluate uploaded CVs against defined job criteria.
- **Candidate comparison:** Compare candidates using job-related evidence and criteria.
- **Portfolio checks:** Support GitHub-related checks where configured and available.
- **Authentication and access controls:** Provide user authentication and protected application functionality.
- **Workspace isolation:** Apply access boundaries to document retrieval and workspace data.
- **Document management:** Track processing status and support document operations.
- **Admin functionality:** Include administrative endpoints and access restrictions.
- **Frontend and backend separation:** Use a React-based interface with a Python API backend.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, TypeScript |
| Backend | Python, FastAPI |
| API communication | REST API |
| Document processing | PDF, DOCX, and TXT processing |
| AI document retrieval | Retrieval-Augmented Generation (RAG) |
| Evidence handling | Document chunks, citations, validation |
| Testing | pytest, Vitest |
| Development tools | Git, GitHub, VS Code |
| Configuration | Environment variables |
| Deployment | Under evaluation |

Consult the current source code and configuration files for the exact dependencies and enabled integrations.

## Architecture

```text
User
 |
 v
React + TypeScript Frontend
 |
 v
FastAPI Backend
 |
 +--> Authentication and Access Control
 |
 +--> Document Upload and Processing
 |      |
 |      +--> PDF / DOCX / TXT
 |      +--> Text Extraction
 |      +--> Document Chunks
 |
 +--> Document Retrieval and RAG
 |      |
 |      +--> Relevant Evidence Retrieval
 |      +--> Answer Generation / Extractive Fallback
 |      +--> Citation Validation
 |
 +--> CV Analysis
 |      |
 |      +--> Job Criteria
 |      +--> Evidence-Based Scoring
 |      +--> Candidate Comparison
 |
 +--> Workspace and Document Management
 |
 v
API Response with Results and Evidence
 |
 v
React User Interface
```

This diagram illustrates the high-level application workflow. The precise processing sequence and available integrations depend on the current implementation.

## RAG and Evidence-Grounded AI

DocuMind AI explores Retrieval-Augmented Generation as a way to answer questions using information retrieved from uploaded documents.

The general workflow is:

1. Upload a supported document.
2. Extract its text and organize it into retrievable chunks.
3. Submit a question about the document.
4. Retrieve relevant passages.
5. Produce a response using available evidence or an extractive fallback.
6. Validate citations and expose supporting evidence where available.

The project includes tests for citation validation, insufficient evidence, workspace isolation, and fallback behavior.

### Responsible answer generation

The application is designed to distinguish available document evidence from unsupported claims. However, retrieval and citation validation do not guarantee that every answer is factually correct.

## CV Analysis and Candidate Matching

The CV analysis component explores how candidate information can be evaluated against job-related criteria.

Its intended workflow includes:

- Uploading CV documents.
- Defining job requirements and evaluation criteria.
- Extracting relevant candidate evidence.
- Applying reproducible scoring logic.
- Comparing candidates against the same criteria.
- Identifying missing or insufficient evidence.

The system should support human review rather than treating an automated score as a final hiring decision. Scoring quality depends on the criteria, extracted information, and evaluation methodology.

## Security and Data Isolation

Security-related functionality includes authentication, access restrictions, workspace isolation, and validation of document operations.

The backend test suite includes checks for authentication, access control, user separation, and other security-related behavior.

These tests are useful safeguards, but they do not establish that the application has undergone a comprehensive security audit. Production use requires additional review of file handling, authentication, secrets, database configuration, retention policies, and deployment settings.

## Application Screenshots

### Dashboard

![DocuMind AI Dashboard](screenshots/Screenshot%20(288).png)

View the [complete screenshots folder](screenshots/) for additional application screens.

## Installation and Local Development

### Requirements

- Python and the dependencies supported by the backend project.
- Node.js and npm.
- Git.
- Internet access for installing dependencies and any external integrations that are configured.

### 1. Clone the repository

```bash
git clone https://github.com/komalcoder357/documind-ai.git
cd documind-ai
```

### 2. Start the backend

Open a terminal:

```powershell
Set-Location ".\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Backend URL:

`http://127.0.0.1:8000`

### 3. Start the frontend

Open a separate terminal:

```powershell
Set-Location ".\frontend"
npm run dev
```

Open the frontend URL shown by the development server, normally:

`http://localhost:5173/`

Keep both terminals running while testing the application.

### 4. Environment configuration

Review the repository's `.env.example` and configuration files for the required environment variables.

Use your own credentials where needed. Never commit real API keys, passwords, tokens, private documents, or local database files to GitHub.

## Testing

### Backend tests

Run from the `backend` directory:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

**Latest recorded local result:**

- 39 tests collected.
- 37 passed.
- 2 failed.

The two failures concern the expected embedding pipeline label and invalid-citation handling. These need investigation and resolution before reporting the backend test suite as fully passing.

### Frontend tests

Run from the `frontend` directory:

```powershell
npm test -- --run
```

**Latest recorded local result:**

- 2 test files passed.
- 3 tests passed.
- 0 test failures.

These results reflect the local development environment at the time of testing. They do not guarantee that every production integration or deployment configuration works correctly.

## Known Limitations

- Two backend RAG-related tests currently fail.
- Document extraction quality depends on the uploaded file and its structure.
- Scanned documents may require OCR support.
- Retrieval quality depends on the chunking and embedding configuration.
- Citation validation cannot guarantee the truth of every generated statement.
- CV scoring depends on the selected criteria and extracted evidence.
- GitHub and other external integrations may be affected by rate limits or service availability.
- The application has not yet been confirmed as production-ready through comprehensive security and real-world performance testing.
- Deployment suitability depends on persistent storage, database support, memory requirements, and configured AI services.

## Future Improvements

- Resolve the remaining backend test failures.
- Improve retrieval and citation evaluation.
- Add documented evaluation datasets and reproducible benchmarks.
- Expand real-browser and end-to-end testing.
- Improve deployment configuration and persistent storage.
- Strengthen monitoring, security review, and error handling.
- Evaluate document-processing performance on diverse real-world files.

## Project Goals

DocuMind AI is intended as a portfolio project exploring the integration of document processing, retrieval-based AI, evidence validation, CV analysis, and full-stack application engineering.

Its goal is to make document intelligence more useful, transparent, and evidence-oriented while continuing to improve reliability through testing and evaluation.

## Repository

🔗 [GitHub Repository — DocuMind AI](https://github.com/komalcoder357/documind-ai)

⭐ *Building practical AI systems through evidence, experimentation, and responsible engineering.*
