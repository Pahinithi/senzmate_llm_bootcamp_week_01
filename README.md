# CV-Job Matching System

A Python application that analyzes and matches CVs with job descriptions using AI-powered semantic analysis. The system extracts key information from both CVs and job descriptions, then calculates a compatibility score based on skills, education, and experience.

## Features

- **PDF Processing**: Extracts text from CV and job description PDFs
- **AI-Powered Analysis**: Uses Google's Gemini AI to extract structured information
- **Matching Algorithm**: Calculates compatibility scores based on:
  - Skills match (70% weight)
  - Education/qualifications (20% weight)
  - Experience (10% weight)
- **Multiple Output Formats**:
  - Detailed PDF report
  - Structured JSON data

## Prerequisites

- Python 3.11
- Google Cloud API key with access to Gemini AI
- Required Python packages (see `requirements.txt`)

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project root and add your Google API key:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

## Usage

### Running the Application

1. Start the FastAPI server:
   ```bash
   fastapi dev app/main.py
   ```

2. The API will be available at `http://localhost:8000`

### API Endpoints

- `GET /health`: Health check endpoint
- `POST /match-cv-job`: Match a CV with a job description

### Matching CV with Job Description

Send a POST request to `/match-cv-job` with two PDF files:
- `cv_file`: The candidate's CV in PDF format
- `job_file`: The job description in PDF format

Example using `curl`:
```bash
curl -X 'POST' \
  'http://localhost:8000/match-cv-job' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'cv_file=@path/to/your/cv.pdf;type=application/pdf' \
  -F 'job_file=@path/to/your/job.pdf;type=application/pdf'
```

## Output

The system generates two output files:
1. **PDF Report**: A formatted PDF with detailed matching results
2. **JSON File**: Structured data containing all matching details

Output files are saved in the `output/` directory with timestamps in their filenames.
