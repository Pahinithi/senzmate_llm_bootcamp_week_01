from pydantic import BaseModel
from typing import List
from datetime import datetime

class CVData(BaseModel):
    name: str
    skills: List[str]
    education: List[str]
    experience: List[str]

class JobData(BaseModel):
    required_skills: List[str]
    qualifications: List[str]
    experience_needed: str

class ScoreDetails(BaseModel):
    total_score: int
    skill_score: float
    education_score: float
    experience_score: float
    skill_matches: int
    total_required_skills: int
    education_match_found: bool
    experience_match_found: bool

class MatchResult(BaseModel):
    cv_data: CVData
    job_data: JobData
    score_details: ScoreDetails
    timestamp: datetime
    interpretation: str
