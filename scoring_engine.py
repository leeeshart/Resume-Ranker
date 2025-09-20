import json
import os
import re
from typing import Dict, List, Any, Tuple
from collections import Counter
import numpy as np
# IMPORTANT: Using python_gemini integration
from google import genai
from google.genai import types

# Try to import sklearn for TF-IDF, with fallback
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Note: sentence-transformers not available in this environment
# We'll use Gemini's built-in semantic understanding instead
SENTENCE_TRANSFORMERS_AVAILABLE = False

class ScoringEngine:
    """AI-powered resume scoring and analysis engine"""
    
    def __init__(self):
        # IMPORTANT: Using python_gemini integration
        # the newest Gemini model series is "gemini-2.5-flash" or "gemini-2.5-pro"
        # do not change this unless explicitly requested by the user
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Initialize TF-IDF vectorizer if available
        if SKLEARN_AVAILABLE:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
        
        # Using Gemini's semantic understanding instead of sentence transformers
        self.sentence_model = None
        
        # Scoring weights
        self.weights = {
            'hard_match': 0.4,      # Keyword and skill matching
            'semantic_match': 0.4,   # Semantic similarity via embeddings
            'ai_analysis': 0.2       # LLM-based contextual analysis
        }
    
    def analyze_resume(self, resume_text: str, job_description: str, parsed_jd: Dict) -> Dict[str, Any]:
        """Complete resume analysis and scoring"""
        
        try:
            # Step 1: Hard matching (keywords, skills)
            hard_match_result = self._calculate_hard_match(resume_text, parsed_jd)
            
            # Step 2: Semantic matching
            semantic_result = self._calculate_semantic_match(resume_text, job_description)
            
            # Step 3: AI-powered analysis
            ai_result = self._ai_analysis(resume_text, job_description, parsed_jd)
            
            # Step 4: Calculate final score
            final_score = self._calculate_final_score(hard_match_result, semantic_result, ai_result)
            
            # Step 5: Generate verdict and suggestions
            verdict = self._get_verdict(final_score)
            suggestions = self._generate_suggestions(resume_text, parsed_jd, ai_result)
            
            return {
                'relevance_score': final_score,
                'hard_match_score': hard_match_result['score'],
                'semantic_score': semantic_result['score'],
                'ai_score': ai_result['score'],
                'verdict': verdict,
                'confidence': ai_result.get('confidence', 0.8),
                'missing_skills': ai_result.get('missing_skills', []),
                'found_skills': hard_match_result.get('found_skills', []),
                'suggestions': suggestions,
                'detailed_feedback': ai_result.get('detailed_feedback', ''),
                'score_breakdown': {
                    'hard_match': hard_match_result['score'],
                    'semantic_match': semantic_result['score'],
                    'ai_analysis': ai_result['score']
                }
            }
        
        except Exception as e:
            # Return minimal result on error
            return {
                'relevance_score': 0,
                'hard_match_score': 0,
                'semantic_score': 0,
                'ai_score': 0,
                'verdict': 'Low',
                'confidence': 0.1,
                'missing_skills': [],
                'found_skills': [],
                'suggestions': [f"Error during analysis: {str(e)}"],
                'detailed_feedback': f"Analysis failed: {str(e)}",
                'score_breakdown': {'hard_match': 0, 'semantic_match': 0, 'ai_analysis': 0}
            }
    
    def _calculate_hard_match(self, resume_text: str, parsed_jd: Dict) -> Dict[str, Any]:
        """Calculate hard matching score based on keywords and skills"""
        
        resume_lower = resume_text.lower()
        
        # Get required skills
        must_have_skills = parsed_jd.get('must_have_skills', [])
        good_to_have_skills = parsed_jd.get('good_to_have_skills', [])
        all_technologies = parsed_jd.get('technologies', [])
        
        # Find matching skills
        found_must_have = []
        found_good_to_have = []
        found_technologies = []
        
        for skill in must_have_skills:
            if self._skill_mentioned(skill, resume_lower):
                found_must_have.append(skill)
        
        for skill in good_to_have_skills:
            if self._skill_mentioned(skill, resume_lower):
                found_good_to_have.append(skill)
        
        for tech in all_technologies:
            if self._skill_mentioned(tech, resume_lower):
                found_technologies.append(tech)
        
        # Calculate score
        must_have_score = (len(found_must_have) / len(must_have_skills)) * 100 if must_have_skills else 0
        good_to_have_score = (len(found_good_to_have) / len(good_to_have_skills)) * 50 if good_to_have_skills else 0
        
        # Weight must-have more heavily
        hard_score = min(100, must_have_score + good_to_have_score)
        
        return {
            'score': round(hard_score, 1),
            'found_skills': found_must_have + found_good_to_have + found_technologies,
            'missing_must_have': [skill for skill in must_have_skills if skill not in found_must_have],
            'missing_good_to_have': [skill for skill in good_to_have_skills if skill not in found_good_to_have],
            'match_details': {
                'must_have_found': len(found_must_have),
                'must_have_total': len(must_have_skills),
                'good_to_have_found': len(found_good_to_have),
                'good_to_have_total': len(good_to_have_skills)
            }
        }
    
    def _skill_mentioned(self, skill: str, text: str) -> bool:
        """Check if a skill is mentioned in text with fuzzy matching"""
        
        skill_lower = skill.lower()
        
        # Direct match
        if skill_lower in text:
            return True
        
        # Handle common variations
        variations = self._get_skill_variations(skill_lower)
        for variation in variations:
            if variation in text:
                return True
        
        # Word boundary matching for better accuracy
        skill_words = skill_lower.split()
        if len(skill_words) == 1:
            pattern = r'\b' + re.escape(skill_lower) + r'\b'
            if re.search(pattern, text):
                return True
        
        return False
    
    def _get_skill_variations(self, skill: str) -> List[str]:
        """Get common variations of a skill name"""
        
        variations = [skill]
        
        # Common substitutions
        substitutions = {
            'javascript': ['js', 'java script'],
            'typescript': ['ts'],
            'python': ['py'],
            'machine learning': ['ml', 'machinelearning'],
            'artificial intelligence': ['ai'],
            'node.js': ['nodejs', 'node'],
            'react.js': ['reactjs', 'react'],
            'angular.js': ['angularjs', 'angular'],
            'vue.js': ['vuejs', 'vue'],
            'c++': ['cpp', 'c plus plus'],
            'c#': ['csharp', 'c sharp'],
            'sql server': ['sqlserver', 'mssql'],
            'postgresql': ['postgres', 'psql']
        }
        
        skill_lower = skill.lower()
        if skill_lower in substitutions:
            variations.extend(substitutions[skill_lower])
        
        # Reverse lookup
        for main_skill, alts in substitutions.items():
            if skill_lower in alts:
                variations.append(main_skill)
                variations.extend(alts)
        
        return list(set(variations))
    
    def _calculate_semantic_match(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """Calculate semantic similarity between resume and job description"""
        
        try:
            # Method 1: Use Gemini for semantic similarity
            gemini_result = self._gemini_semantic_similarity(resume_text, job_description)
            if gemini_result['score'] > 0:
                return gemini_result
            
            # Method 2: Use TF-IDF if sklearn is available
            elif SKLEARN_AVAILABLE:
                return self._tfidf_similarity(resume_text, job_description)
            
            # Method 3: Fallback to basic word overlap
            else:
                return self._word_overlap_similarity(resume_text, job_description)
        
        except Exception as e:
            # Return neutral score on error
            return {'score': 50.0, 'error': str(e)}
    
    def _gemini_semantic_similarity(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """Calculate semantic similarity using Gemini AI"""
        
        try:
            prompt = f"""
            Analyze the semantic similarity between the following resume and job description. 
            Provide a similarity score from 0-100 based on how well the candidate's background matches the job requirements.
            
            Job Description:
            {job_description}
            
            Resume:
            {resume_text}
            
            Please respond with a JSON object in this exact format:
            {{
                "similarity_score": 85,
                "explanation": "Brief explanation of the similarity assessment",
                "key_matches": ["match1", "match2"],
                "key_gaps": ["gap1", "gap2"]
            }}
            
            Score should be 0-100 where:
            - 90-100: Excellent match, candidate exceeds requirements
            - 80-89: Very good match, candidate meets most requirements
            - 70-79: Good match, candidate meets core requirements
            - 60-69: Fair match, candidate meets some requirements
            - 50-59: Poor match, significant gaps
            - 0-49: Very poor match, major misalignment
            """
            
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if response.text:
                result = json.loads(response.text)
                score = max(0, min(100, result.get('similarity_score', 50)))
                
                return {
                    'score': round(score, 1),
                    'method': 'gemini_semantic',
                    'explanation': result.get('explanation', ''),
                    'key_matches': result.get('key_matches', []),
                    'key_gaps': result.get('key_gaps', [])
                }
            else:
                raise Exception("Empty response from Gemini")
                
        except Exception as e:
            # Fallback to TF-IDF if Gemini fails
            print(f"Gemini semantic analysis failed: {e}")
            return {'score': 0.0, 'method': 'gemini_failed', 'error': str(e)}
    
    def _sentence_transformer_similarity(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """Legacy method - not used since sentence transformers not available"""
        return {'score': 0.0, 'method': 'sentence_transformer_unavailable'}
    
    def _tfidf_similarity(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """Calculate similarity using TF-IDF"""
        
        # Fit TF-IDF on both documents
        documents = [resume_text, job_description]
        tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)
        
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        # Convert to 0-100 scale
        score = max(0, min(100, similarity * 100))
        
        return {
            'score': round(score, 1),
            'method': 'tfidf',
            'similarity': float(similarity)
        }
    
    def _word_overlap_similarity(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """Basic word overlap similarity as fallback"""
        
        # Tokenize and clean
        resume_words = set(re.findall(r'\b\w+\b', resume_text.lower()))
        jd_words = set(re.findall(r'\b\w+\b', job_description.lower()))
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being'
        }
        
        resume_words -= stop_words
        jd_words -= stop_words
        
        # Calculate Jaccard similarity
        intersection = len(resume_words.intersection(jd_words))
        union = len(resume_words.union(jd_words))
        
        jaccard = intersection / union if union > 0 else 0
        score = jaccard * 100
        
        return {
            'score': round(score, 1),
            'method': 'word_overlap',
            'intersection_count': intersection,
            'union_count': union
        }
    
    def _ai_analysis(self, resume_text: str, job_description: str, parsed_jd: Dict) -> Dict[str, Any]:
        """Use OpenAI for comprehensive analysis"""
        
        try:
            prompt = f"""
            Analyze the following resume against the job description and provide a comprehensive evaluation.
            
            Job Description:
            {job_description}
            
            Resume:
            {resume_text}
            
            Required Skills: {parsed_jd.get('must_have_skills', [])}
            Preferred Skills: {parsed_jd.get('good_to_have_skills', [])}
            
            Please provide a detailed analysis in JSON format:
            {{
                "score": 85,
                "confidence": 0.9,
                "missing_skills": ["skill1", "skill2"],
                "strengths": ["strength1", "strength2"],
                "weaknesses": ["weakness1", "weakness2"],
                "experience_match": "good/average/poor",
                "education_match": "good/average/poor",
                "overall_fit": "excellent/good/average/poor",
                "detailed_feedback": "Comprehensive feedback about the candidate's suitability...",
                "improvement_areas": ["area1", "area2"],
                "recommendation": "hire/interview/reject"
            }}
            
            Score should be 0-100 based on overall fit for the role.
            Be specific about missing skills and areas for improvement.
            Provide actionable feedback that would help the candidate improve.
            """
            
            system_instruction = "You are an expert technical recruiter and HR analyst. Provide detailed, honest, and constructive feedback about resume-job fit."
            
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json"
                )
            )
            
            if response.text:
                result = json.loads(response.text)
            else:
                raise Exception("Empty response from Gemini model")
            
            # Ensure score is within valid range
            result['score'] = max(0, min(100, result.get('score', 50)))
            result['confidence'] = max(0, min(1, result.get('confidence', 0.8)))
            
            return result
        
        except Exception as e:
            # Return default analysis on error
            return {
                'score': 50.0,
                'confidence': 0.5,
                'missing_skills': [],
                'strengths': [],
                'weaknesses': [f"Analysis error: {str(e)}"],
                'experience_match': 'unknown',
                'education_match': 'unknown',
                'overall_fit': 'unknown',
                'detailed_feedback': f"AI analysis failed: {str(e)}",
                'improvement_areas': [],
                'recommendation': 'review_manually'
            }
    
    def _calculate_final_score(self, hard_match: Dict, semantic_match: Dict, ai_analysis: Dict) -> float:
        """Calculate weighted final score"""
        
        hard_score = hard_match.get('score', 0)
        semantic_score = semantic_match.get('score', 0)
        ai_score = ai_analysis.get('score', 0)
        
        final_score = (
            hard_score * self.weights['hard_match'] +
            semantic_score * self.weights['semantic_match'] +
            ai_score * self.weights['ai_analysis']
        )
        
        return round(final_score, 1)
    
    def _get_verdict(self, score: float) -> str:
        """Convert score to verdict"""
        
        if score >= 75:
            return "High"
        elif score >= 50:
            return "Medium"
        else:
            return "Low"
    
    def _generate_suggestions(self, resume_text: str, parsed_jd: Dict, ai_analysis: Dict) -> List[str]:
        """Generate improvement suggestions"""
        
        suggestions = []
        
        # Add AI-generated suggestions
        ai_suggestions = ai_analysis.get('improvement_areas', [])
        suggestions.extend(ai_suggestions)
        
        # Add missing skills suggestions
        missing_skills = ai_analysis.get('missing_skills', [])
        if missing_skills:
            suggestions.append(f"Consider adding these skills to your resume: {', '.join(missing_skills[:5])}")
        
        # Experience-based suggestions
        experience_match = ai_analysis.get('experience_match', '')
        if experience_match == 'poor':
            suggestions.append("Highlight relevant projects or experience that demonstrate your capabilities")
        
        # Education-based suggestions
        education_match = ai_analysis.get('education_match', '')
        if education_match == 'poor':
            suggestions.append("Consider pursuing relevant certifications or additional training")
        
        # Generic suggestions if none provided
        if not suggestions:
            suggestions = [
                "Tailor your resume to better match the job requirements",
                "Add more specific examples of your achievements",
                "Include relevant keywords from the job description"
            ]
        
        return suggestions[:5]  # Limit to top 5 suggestions
