import re
import json
import os
from typing import Dict, List, Any
# IMPORTANT: Using python_gemini integration
from google import genai
from google.genai import types

class JobAnalyzer:
    """Parse and analyze job descriptions to extract requirements"""
    
    def __init__(self):
        # IMPORTANT: Using python_gemini integration
        # the newest Gemini model series is "gemini-2.5-flash" or "gemini-2.5-pro"
        # do not change this unless explicitly requested by the user
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Common skill categories and keywords
        self.skill_categories = {
            'programming_languages': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 
                'ruby', 'go', 'rust', 'kotlin', 'swift', 'scala', 'r', 'matlab'
            ],
            'web_technologies': [
                'html', 'css', 'react', 'angular', 'vue', 'node.js', 'express',
                'django', 'flask', 'spring', 'laravel', 'rails'
            ],
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
                'oracle', 'sql server', 'sqlite', 'cassandra', 'dynamodb'
            ],
            'cloud_platforms': [
                'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes',
                'terraform', 'jenkins', 'git', 'ci/cd'
            ],
            'data_science': [
                'machine learning', 'deep learning', 'pandas', 'numpy', 'scikit-learn',
                'tensorflow', 'pytorch', 'tableau', 'power bi', 'spark'
            ],
            'soft_skills': [
                'communication', 'leadership', 'teamwork', 'problem solving',
                'analytical thinking', 'project management', 'agile', 'scrum'
            ]
        }
    
    def parse_job_description(self, job_description: str) -> Dict[str, Any]:
        """Parse job description and extract structured information"""
        
        try:
            # Use OpenAI to extract structured information
            ai_analysis = self._analyze_with_ai(job_description)
            
            # Combine AI analysis with rule-based extraction
            rule_based_analysis = self._extract_with_rules(job_description)
            
            # Merge results
            parsed_jd = self._merge_analyses(ai_analysis, rule_based_analysis)
            
            return parsed_jd
        
        except Exception as e:
            # Fallback to rule-based parsing if AI fails
            print(f"AI analysis failed, using rule-based parsing: {e}")
            return self._extract_with_rules(job_description)
    
    def _analyze_with_ai(self, job_description: str) -> Dict[str, Any]:
        """Use OpenAI to analyze job description"""
        
        prompt = f"""
        Analyze the following job description and extract structured information.
        
        Job Description:
        {job_description}
        
        Please extract and return the following information in JSON format:
        {{
            "role_title": "extracted job title",
            "must_have_skills": ["skill1", "skill2", ...],
            "good_to_have_skills": ["skill1", "skill2", ...],
            "qualifications": ["qualification1", "qualification2", ...],
            "experience_required": "years of experience required",
            "key_responsibilities": ["responsibility1", "responsibility2", ...],
            "technologies": ["tech1", "tech2", ...],
            "soft_skills": ["skill1", "skill2", ...],
            "education_level": "minimum education requirement",
            "industry": "industry/domain",
            "employment_type": "full-time/part-time/contract/etc"
        }}
        
        Be specific and extract actual skills, technologies, and requirements mentioned in the description.
        Separate must-have from good-to-have based on language like "required", "essential" vs "preferred", "nice to have".
        """
        
        system_instruction = "You are an expert HR analyst. Extract structured information from job descriptions accurately and comprehensively."
        
        response = self.gemini_client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json"
            )
        )
        
        if response.text:
            return json.loads(response.text)
        else:
            raise Exception("Empty response from Gemini model")
    
    def _extract_with_rules(self, job_description: str) -> Dict[str, Any]:
        """Rule-based extraction as fallback"""
        
        text_lower = job_description.lower()
        
        # Extract skills using keyword matching
        found_skills = []
        for category, skills in self.skill_categories.items():
            for skill in skills:
                if skill.lower() in text_lower:
                    found_skills.append(skill)
        
        # Extract experience requirements
        experience_pattern = r'(\d+)[\+\-\s]*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)'
        experience_matches = re.findall(experience_pattern, text_lower)
        experience_required = experience_matches[0] if experience_matches else "Not specified"
        
        # Extract education requirements
        education_keywords = ['bachelor', 'master', 'phd', 'degree', 'diploma', 'certification']
        education_mentions = []
        for keyword in education_keywords:
            if keyword in text_lower:
                education_mentions.append(keyword)
        
        # Separate must-have vs good-to-have (basic heuristic)
        must_have_indicators = ['required', 'essential', 'must have', 'mandatory', 'minimum']
        good_to_have_indicators = ['preferred', 'nice to have', 'plus', 'bonus', 'advantage']
        
        must_have_skills = []
        good_to_have_skills = []
        
        # Simple classification based on context
        for skill in found_skills:
            skill_context = self._get_skill_context(skill, job_description)
            
            if any(indicator in skill_context.lower() for indicator in must_have_indicators):
                must_have_skills.append(skill)
            elif any(indicator in skill_context.lower() for indicator in good_to_have_indicators):
                good_to_have_skills.append(skill)
            else:
                # Default to must-have if no clear indication
                must_have_skills.append(skill)
        
        return {
            "role_title": "Not extracted",
            "must_have_skills": list(set(must_have_skills)),
            "good_to_have_skills": list(set(good_to_have_skills)),
            "qualifications": education_mentions,
            "experience_required": experience_required,
            "key_responsibilities": [],
            "technologies": found_skills,
            "soft_skills": [],
            "education_level": "Not specified",
            "industry": "Not specified",
            "employment_type": "Not specified"
        }
    
    def _get_skill_context(self, skill: str, text: str, context_window: int = 100) -> str:
        """Get surrounding context for a skill mention"""
        
        skill_lower = skill.lower()
        text_lower = text.lower()
        
        index = text_lower.find(skill_lower)
        if index == -1:
            return ""
        
        start = max(0, index - context_window)
        end = min(len(text), index + len(skill) + context_window)
        
        return text[start:end]
    
    def _merge_analyses(self, ai_analysis: Dict, rule_analysis: Dict) -> Dict[str, Any]:
        """Merge AI and rule-based analyses"""
        
        merged = ai_analysis.copy()
        
        # Supplement AI analysis with rule-based findings
        if not merged.get('must_have_skills'):
            merged['must_have_skills'] = rule_analysis.get('must_have_skills', [])
        
        if not merged.get('good_to_have_skills'):
            merged['good_to_have_skills'] = rule_analysis.get('good_to_have_skills', [])
        
        # Combine technology lists
        ai_techs = set(merged.get('technologies', []))
        rule_techs = set(rule_analysis.get('technologies', []))
        merged['technologies'] = list(ai_techs.union(rule_techs))
        
        # Use rule-based experience if AI didn't extract it properly
        if merged.get('experience_required') == "Not specified" or not merged.get('experience_required'):
            merged['experience_required'] = rule_analysis.get('experience_required', 'Not specified')
        
        return merged
    
    def extract_keywords(self, job_description: str) -> List[str]:
        """Extract important keywords from job description"""
        
        # Remove common stop words and extract meaningful terms
        import re
        
        # Clean text
        text = re.sub(r'[^\w\s]', ' ', job_description.lower())
        words = text.split()
        
        # Common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'a', 'an', 'we', 'you', 'they', 'our', 'your', 'their'
        }
        
        # Extract keywords (2+ characters, not stop words)
        keywords = [
            word for word in words 
            if len(word) > 2 and word not in stop_words
        ]
        
        # Get word frequency and return top keywords
        from collections import Counter
        word_freq = Counter(keywords)
        
        # Return top 50 most frequent keywords
        return [word for word, count in word_freq.most_common(50)]
    
    def categorize_skills(self, skills: List[str]) -> Dict[str, List[str]]:
        """Categorize skills into different types"""
        
        categorized = {
            'technical': [],
            'programming': [],
            'tools': [],
            'soft_skills': [],
            'other': []
        }
        
        for skill in skills:
            skill_lower = skill.lower()
            
            # Check programming languages
            if any(lang in skill_lower for lang in self.skill_categories['programming_languages']):
                categorized['programming'].append(skill)
            
            # Check web technologies and databases
            elif any(tech in skill_lower for tech in 
                    self.skill_categories['web_technologies'] + self.skill_categories['databases']):
                categorized['technical'].append(skill)
            
            # Check cloud and tools
            elif any(tool in skill_lower for tool in self.skill_categories['cloud_platforms']):
                categorized['tools'].append(skill)
            
            # Check soft skills
            elif any(soft in skill_lower for soft in self.skill_categories['soft_skills']):
                categorized['soft_skills'].append(skill)
            
            else:
                categorized['other'].append(skill)
        
        return categorized
