import re
from typing import List, Dict, Any
from datetime import datetime

def format_score(score: float) -> str:
    """Format score for display"""
    return f"{score:.1f}"

def get_verdict_color(verdict: str) -> str:
    """Get color for verdict display in Streamlit"""
    color_map = {
        'High': 'green',
        'Medium': 'orange', 
        'Low': 'red'
    }
    return color_map.get(verdict, 'gray')

def clean_filename(filename: str) -> str:
    """Clean filename for safe storage"""
    # Remove path components and keep only the filename
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove or replace special characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:90] + ('.' + ext if ext else '')
    
    return filename

def extract_name_from_resume(text: str) -> str:
    """Try to extract candidate name from resume text"""
    lines = text.split('\n')
    
    # Look for name in first few lines
    for i, line in enumerate(lines[:5]):
        line = line.strip()
        
        # Skip empty lines and common headers
        if not line or line.lower() in ['resume', 'cv', 'curriculum vitae']:
            continue
        
        # Check if line looks like a name (2-4 words, proper case)
        words = line.split()
        if 2 <= len(words) <= 4 and all(word.istitle() for word in words):
            return line
    
    return "Unknown Candidate"

def parse_experience_years(text: str) -> int:
    """Extract years of experience from text"""
    
    # Patterns to match experience
    patterns = [
        r'(\d+)[\+\-\s]*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)',
        r'(\d+)[\+\-\s]*(?:year|yr)\s*(?:of\s*)?(?:experience|exp)',
        r'experience[:\s]*(\d+)[\+\-\s]*(?:years?|yrs?)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            try:
                return int(matches[0])
            except ValueError:
                continue
    
    return 0

def extract_education_level(text: str) -> str:
    """Extract highest education level from text"""
    
    education_keywords = {
        'phd': ['phd', 'ph.d', 'doctorate', 'doctoral'],
        'masters': ['masters', 'master', 'm.s', 'ms', 'm.tech', 'mtech', 'mba'],
        'bachelors': ['bachelors', 'bachelor', 'b.s', 'bs', 'b.tech', 'btech', 'b.e', 'be'],
        'diploma': ['diploma', 'certificate'],
        'high_school': ['high school', 'secondary', '12th', 'intermediate']
    }
    
    text_lower = text.lower()
    
    for level, keywords in education_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                return level.replace('_', ' ').title()
    
    return "Not specified"

def extract_skills_from_text(text: str) -> List[str]:
    """Extract skills from text using keyword matching"""
    
    # Common technical skills
    technical_skills = [
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby',
        'go', 'rust', 'kotlin', 'swift', 'scala', 'r', 'matlab', 'sql', 'html',
        'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask',
        'spring', 'laravel', 'rails', 'mysql', 'postgresql', 'mongodb', 'redis',
        'elasticsearch', 'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git',
        'jenkins', 'terraform', 'ansible', 'linux', 'windows', 'machine learning',
        'deep learning', 'artificial intelligence', 'data science', 'pandas',
        'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'tableau', 'power bi'
    ]
    
    found_skills = []
    text_lower = text.lower()
    
    for skill in technical_skills:
        if skill in text_lower:
            found_skills.append(skill)
    
    return found_skills

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M")

def calculate_percentage(part: int, total: int) -> float:
    """Calculate percentage with division by zero protection"""
    if total == 0:
        return 0.0
    return round((part / total) * 100, 1)

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    
    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\';]', '', text)
    
    # Limit length
    text = text[:1000]
    
    return text.strip()

def get_file_size_mb(file_content: bytes) -> float:
    """Get file size in MB"""
    return len(file_content) / (1024 * 1024)

def is_supported_file_type(filename: str) -> bool:
    """Check if file type is supported"""
    supported_extensions = ['.pdf', '.docx']
    file_extension = '.' + filename.split('.')[-1].lower()
    return file_extension in supported_extensions

def extract_company_names(text: str) -> List[str]:
    """Extract potential company names from text"""
    
    # Look for common company indicators
    company_patterns = [
        r'(?:worked at|employed at|job at)\s+([A-Z][a-zA-Z\s&]+)',
        r'([A-Z][a-zA-Z\s&]+)(?:\s+Inc\.?|\s+LLC|\s+Corp\.?|\s+Ltd\.?)',
        r'([A-Z][a-zA-Z\s&]+)\s+(?:Technologies|Systems|Solutions|Services)'
    ]
    
    companies = []
    for pattern in company_patterns:
        matches = re.findall(pattern, text)
        companies.extend(matches)
    
    # Clean and deduplicate
    cleaned_companies = []
    for company in companies:
        company = company.strip()
        if len(company) > 2 and company not in cleaned_companies:
            cleaned_companies.append(company)
    
    return cleaned_companies[:5]  # Return top 5

def highlight_keywords(text: str, keywords: List[str]) -> str:
    """Highlight keywords in text (for display purposes)"""
    
    if not keywords:
        return text
    
    # Create a pattern that matches any of the keywords
    pattern = '|'.join(re.escape(keyword) for keyword in keywords)
    
    def replace_func(match):
        return f"**{match.group()}**"
    
    return re.sub(pattern, replace_func, text, flags=re.IGNORECASE)

def score_to_emoji(score: float) -> str:
    """Convert score to emoji representation"""
    if score >= 90:
        return "🎯"
    elif score >= 80:
        return "🟢"
    elif score >= 70:
        return "🟡"
    elif score >= 60:
        return "🟠"
    else:
        return "🔴"

def generate_summary_stats(analyses: List[Dict]) -> Dict[str, Any]:
    """Generate summary statistics from analysis results"""
    
    if not analyses:
        return {}
    
    scores = [analysis.get('relevance_score', 0) for analysis in analyses]
    verdicts = [analysis.get('verdict', 'Low') for analysis in analyses]
    
    return {
        'total_count': len(analyses),
        'avg_score': sum(scores) / len(scores),
        'max_score': max(scores),
        'min_score': min(scores),
        'high_count': verdicts.count('High'),
        'medium_count': verdicts.count('Medium'),
        'low_count': verdicts.count('Low'),
        'high_percentage': calculate_percentage(verdicts.count('High'), len(verdicts)),
        'medium_percentage': calculate_percentage(verdicts.count('Medium'), len(verdicts)),
        'low_percentage': calculate_percentage(verdicts.count('Low'), len(verdicts))
    }
