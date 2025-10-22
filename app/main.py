from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from .settings import API_TITLE, API_DESCRIPTION, API_VERSION, INPUT_DIR, OUTPUT_DIR
from .schema.schema import MatchResult
from .function.utilities import match_cv_with_job

# Initialize FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": API_VERSION,
        "API Title": API_TITLE
    }

@app.post("/match-cv-job", response_model=MatchResult)
async def match_cv_job(
    cv_file: UploadFile = File(..., description="CV PDF file"),
    job_file: UploadFile = File(..., description="Job Description PDF file")
):
    """
    Match CV with Job Description and get suitability score
    
    - **cv_file**: CV PDF file
    - **job_file**: Job Description PDF file
    
    Returns detailed matching results with score breakdown
    """
    try:
        # Validate file types
        if not cv_file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="CV file must be a PDF")
        
        if not job_file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Job file must be a PDF")
        
        # Generate unique filenames with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cv_filename = f"cv_{timestamp}_{cv_file.filename}"
        job_filename = f"job_{timestamp}_{job_file.filename}"
        
        # Save files to input directory
        cv_path = INPUT_DIR / cv_filename
        job_path = INPUT_DIR / job_filename
        
        # Save CV file
        with open(cv_path, "wb") as buffer:
            shutil.copyfileobj(cv_file.file, buffer)
        
        # Save Job file
        with open(job_path, "wb") as buffer:
            shutil.copyfileobj(job_file.file, buffer)
        
        # Perform matching
        match_result, output_file = match_cv_with_job(str(cv_path), str(job_path))
        
        if match_result is None:
            raise HTTPException(status_code=500, detail=output_file or "Matching failed")
        
        return match_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during matching: {str(e)}")



