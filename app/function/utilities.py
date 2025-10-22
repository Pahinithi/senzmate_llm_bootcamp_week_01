import json
import re
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import google.generativeai as genai
import PyPDF2
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from ..settings import GOOGLE_API_KEY, GEMINI_MODEL_NAME, INPUT_DIR, OUTPUT_DIR
from ..schema.schema import CVData, JobData, ScoreDetails, MatchResult

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL_NAME)

def extract_text_from_pdf(pdf_file_path: str) -> Optional[str]:
    """Extract text content from a PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file_path)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return None

def extract_cv_details(cv_text: str) -> Optional[CVData]:
    """Use Gemini to extract structured information from CV"""
    prompt = f"""
    Analyze the following CV and extract information in JSON format.

    CV Text:
    {cv_text}

    Extract and return ONLY a valid JSON object with these fields:
    {{
        "name": "candidate's full name",
        "skills": ["skill1", "skill2", "skill3", ...],
        "education": ["degree1", "degree2", ...],
        "experience": ["job title and duration", "job title and duration", ...]
    }}

    Rules:
    - Return ONLY the JSON object, no additional text
    - If information is not found, use empty string or empty array
    - Skills should include technical skills, soft skills, tools, and technologies
    """

    try:
        response = model.generate_content(prompt)
        json_text = response.text.strip()

        # Clean up the response to extract JSON
        json_text = json_text.replace('```json', '').replace('```', '').strip()

        cv_data_dict = json.loads(json_text)
        return CVData(**cv_data_dict)
    except Exception as e:
        print(f"Error extracting CV details: {e}")
        return None

def extract_job_details(job_text: str) -> Optional[JobData]:
    """Use Gemini to extract structured information from Job Description"""
    prompt = f"""
    Analyze the following Job Description and extract information in JSON format.

    Job Description:
    {job_text}

    Extract and return ONLY a valid JSON object with these fields:
    {{
        "required_skills": ["skill1", "skill2", "skill3", ...],
        "qualifications": ["qualification1", "qualification2", ...],
        "experience_needed": "X years of experience or description"
    }}

    Rules:
    - Return ONLY the JSON object, no additional text
    - If information is not found, use empty string or empty array
    - Include both technical and soft skills in required_skills
    """

    try:
        response = model.generate_content(prompt)
        json_text = response.text.strip()

        # Clean up the response to extract JSON
        json_text = json_text.replace('```json', '').replace('```', '').strip()

        job_data_dict = json.loads(json_text)
        return JobData(**job_data_dict)
    except Exception as e:
        print(f"Error extracting job details: {e}")
        return None

def calculate_match_score(cv_data: CVData, job_data: JobData) -> ScoreDetails:
    """Calculate suitability score based on CV and Job Description"""

    # Normalize strings for comparison (lowercase)
    cv_skills = [skill.lower().strip() for skill in cv_data.skills]
    required_skills = [skill.lower().strip() for skill in job_data.required_skills]
    cv_education = [edu.lower().strip() for edu in cv_data.education]
    job_qualifications = [qual.lower().strip() for qual in job_data.qualifications]

    # 1. Skill Match (70% weight)
    if len(required_skills) > 0:
        skill_matches = sum(1 for req_skill in required_skills
                          if any(req_skill in cv_skill or cv_skill in req_skill
                                for cv_skill in cv_skills))
        skill_score = (skill_matches / len(required_skills)) * 70
    else:
        skill_score = 0

    # 2. Education/Qualification Match (20% weight)
    edu_score = 0
    if len(job_qualifications) > 0:
        # Check for degree keywords
        cv_edu_text = ' '.join(cv_education).lower()

        # Common degree/qualification keywords
        degree_keywords = ['bachelor', 'master', 'phd', 'diploma', 'degree', 'bs', 'ms',
                          'computer science', 'data science', 'mathematics', 'engineering',
                          'statistics', 'ai', 'artificial intelligence', 'machine learning']

        # Check if CV has relevant education
        has_relevant_education = any(keyword in cv_edu_text for keyword in degree_keywords)

        # Also check job qualifications
        job_qual_text = ' '.join(job_qualifications).lower()

        # Count matches based on keyword presence
        matches = 0
        for keyword in degree_keywords:
            if keyword in cv_edu_text and keyword in job_qual_text:
                matches += 1

        # If candidate has relevant education, give partial credit
        if has_relevant_education:
            edu_score = 15  # Base score for having relevant education
            if matches > 0:
                edu_score = 20  # Full score if specific match found

        # Check for pursuing/completed status match
        if 'pursuing' in job_qual_text or 'completed' in job_qual_text:
            if 'bachelor' in cv_edu_text or 'university' in cv_edu_text:
                edu_score = max(edu_score, 18)

    # 3. Experience Match (10% weight)
    cv_experience = cv_data.experience
    cv_exp_text = ' '.join(cv_experience).lower()
    job_exp_text = job_data.experience_needed.lower()

    # Consider all experience as relevant since we're not filtering by specific domains
    has_relevant_exp = len(cv_exp_text.strip()) > 0

    # Parse years of experience if possible
    years_match = re.search(r'(\d+)[-\s]?(?:year|yr)', job_exp_text)
    required_years = int(years_match.group(1)) if years_match else 0

    # Count experience entries
    num_experiences = len(cv_experience)

    if num_experiences > 0 and has_relevant_exp:
        if required_years <= 1:  # Entry level or intern position
            experience_score = 10  # Full marks for having any relevant experience
        else:
            experience_score = min(10, (num_experiences / required_years) * 10)
    elif num_experiences > 0:
        experience_score = 5  # Partial credit for having some experience
    else:
        experience_score = 0

    # Total score
    total_score = round(skill_score + edu_score + experience_score)

    return ScoreDetails(
        total_score=total_score,
        skill_score=round(skill_score, 1),
        education_score=round(edu_score, 1),
        experience_score=round(experience_score, 1),
        skill_matches=skill_matches if len(required_skills) > 0 else 0,
        total_required_skills=len(required_skills),
        education_match_found=edu_score > 0,
        experience_match_found=has_relevant_exp
    )

def get_interpretation(score: int) -> str:
    """Get interpretation based on score"""
    if score >= 80:
        return "Excellent Match! Highly suitable candidate."
    elif score >= 60:
        return "Good Match! Suitable candidate with room for growth."
    elif score >= 40:
        return "Moderate Match. Some key skills may be missing."
    else:
        return "Low Match. Significant skill gaps present."

def save_results_to_file(cv_data: CVData, job_data: JobData, score_details: ScoreDetails) -> str:
    """Save results as PDF to output folder"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"match_result_{timestamp}.pdf"
    filepath = OUTPUT_DIR / filename
    
    # Create PDF document
    doc = SimpleDocTemplate(str(filepath), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.darkblue
    )
    story.append(Paragraph("CV and Job Description Match Report", title_style))
    story.append(Spacer(1, 20))
    
    # Timestamp
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Score Summary
    score_style = ParagraphStyle(
        'ScoreStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.darkgreen
    )
    story.append(Paragraph(f"Overall Match Score: {score_details.total_score}/100", score_style))
    story.append(Paragraph(f"Interpretation: {get_interpretation(score_details.total_score)}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Detailed Score Breakdown
    story.append(Paragraph("Score Breakdown", styles['Heading2']))
    
    score_data = [
        ['Category', 'Score', 'Weight', 'Details'],
        ['Skills Match', f"{score_details.skill_score:.1f}/70", '70%', f"{score_details.skill_matches}/{score_details.total_required_skills} skills matched"],
        ['Education Match', f"{score_details.education_score:.1f}/20", '20%', 'Relevant education found' if score_details.education_match_found else 'No relevant education'],
        ['Experience Match', f"{score_details.experience_score:.1f}/10", '10%', 'Relevant experience found' if score_details.experience_match_found else 'No relevant experience']
    ]
    
    score_table = Table(score_data, colWidths=[2*inch, 1.5*inch, 1*inch, 3*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(score_table)
    story.append(Spacer(1, 20))
    
    # CV Information
    story.append(Paragraph("Candidate Information", styles['Heading2']))
    story.append(Paragraph(f"<b>Name:</b> {cv_data.name}", styles['Normal']))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("<b>Skills:</b>", styles['Normal']))
    for skill in cv_data.skills:
        story.append(Paragraph(f"• {skill}", styles['Normal']))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("<b>Education:</b>", styles['Normal']))
    for edu in cv_data.education:
        story.append(Paragraph(f"• {edu}", styles['Normal']))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("<b>Experience:</b>", styles['Normal']))
    for exp in cv_data.experience:
        story.append(Paragraph(f"• {exp}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Job Requirements
    story.append(Paragraph("Job Requirements", styles['Heading2']))
    story.append(Paragraph("<b>Required Skills:</b>", styles['Normal']))
    for skill in job_data.required_skills:
        story.append(Paragraph(f"• {skill}", styles['Normal']))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("<b>Qualifications:</b>", styles['Normal']))
    for qual in job_data.qualifications:
        story.append(Paragraph(f"• {qual}", styles['Normal']))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(f"<b>Experience Needed:</b> {job_data.experience_needed}", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    
    return str(filepath)

def save_results_to_json(result: MatchResult, base_filename: str) -> str:
    """Save results as JSON to output folder"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Generate output filename
        output_file = OUTPUT_DIR / f"{base_filename}.json"
        
        # Convert Pydantic model to dictionary and then to JSON
        with open(output_file, 'w') as f:
            json.dump(result.dict(), f, indent=2, default=str)
            
        return str(output_file)
    except Exception as e:
        print(f"Error saving JSON results: {e}")
        return ""

def match_cv_with_job(cv_file_path: str, job_file_path: str) -> Tuple[Optional[MatchResult], Optional[str]]:
    """Main function to perform CV and Job Description matching"""
    try:
        # Extract text from PDFs
        cv_text = extract_text_from_pdf(cv_file_path)
        job_text = extract_text_from_pdf(job_file_path)
        
        if not cv_text or not job_text:
            return None, "Failed to extract text from one or both PDF files"
        
        # Extract structured data
        cv_data = extract_cv_details(cv_text)
        job_data = extract_job_details(job_text)
        
        if not cv_data or not job_data:
            return None, "Failed to extract data from CV or Job Description"
        
        # Calculate match score
        score_details = calculate_match_score(cv_data, job_data)
        
        # Create result object
        result = MatchResult(
            cv_data=cv_data,
            job_data=job_data,
            score_details=score_details,
            timestamp=datetime.now(),
            interpretation=get_interpretation(score_details.total_score)
        )
        
        # Generate base filename from timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"match_result_{timestamp}"
        
        # Save results to PDF
        pdf_output = save_results_to_file(cv_data, job_data, score_details)
        
        # Save results to JSON
        json_output = save_results_to_json(result, base_filename)
        
        # Return both output files (PDF and JSON)
        return result, f"PDF: {pdf_output}, JSON: {json_output}"
        
    except Exception as e:
        return None, str(e)
