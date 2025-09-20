# Overview

The Automated Resume Relevance Check System is an AI-powered solution designed for Innomatics Research Labs' placement teams across multiple cities (Hyderabad, Bangalore, Pune, and Delhi NCR). The system automates the manual process of matching resumes against job descriptions, providing standardized evaluation with relevance scores (0-100), gap analysis, and actionable feedback. Built with Streamlit for the web interface, the system processes 18-20 job postings weekly and handles thousands of resumes at scale.

The application combines rule-based keyword matching with AI-powered semantic analysis using Google's Gemini LLM to provide both speed and contextual understanding. It features a comprehensive dashboard for placement teams to manage job postings, analyze resumes, and track performance analytics.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Streamlit web application with multi-page navigation
- **Layout**: Wide layout configuration with sidebar navigation
- **Pages**: Job Management, Resume Analysis, Dashboard, and Analytics
- **Caching**: Uses `@st.cache_resource` for component initialization to improve performance
- **File Handling**: Supports PDF and DOCX resume uploads with multiple parsing libraries as fallbacks

## Backend Architecture
- **Database Layer**: SQLite database with contextual connection management
- **Core Components**:
  - `ResumeParser`: Handles text extraction from PDF/DOCX files with multiple library fallbacks
  - `JobAnalyzer`: Processes job descriptions and extracts structured requirements
  - `ScoringEngine`: AI-powered scoring system with hybrid analysis
  - `Database`: SQLite operations with proper schema management

## Scoring Algorithm
- **Hybrid Approach**: Combines three scoring methods with weighted averages
  - Hard Match (40%): Keyword and skill matching
  - Semantic Match (40%): AI-powered semantic similarity
  - AI Analysis (20%): LLM-based contextual analysis
- **Fallback Strategy**: Multiple parsing libraries to ensure reliability
- **Skill Categorization**: Predefined categories for programming languages, web technologies, databases, cloud platforms, data science, and soft skills

## Data Storage
- **Database**: SQLite with two main tables
  - `job_descriptions`: Stores job postings with parsed data and status
  - `resume_analyses`: Stores analysis results linked to job postings
- **Schema Design**: Includes foreign key relationships, timestamps, and JSON storage for structured data
- **Indexing**: Performance optimizations for frequent queries

## AI Integration
- **Primary LLM**: Google Gemini (gemini-2.5-flash/gemini-2.5-pro) via python_gemini client
- **Text Processing**: TF-IDF vectorization with scikit-learn (when available)
- **Semantic Analysis**: Leverages Gemini's built-in semantic understanding instead of sentence transformers
- **Environment Configuration**: API key management through environment variables

## File Processing
- **Multi-library Support**: Redundant parsing capabilities
  - PDF: PyMuPDF (fitz) and pdfplumber
  - DOCX: python-docx and docx2txt
- **Error Handling**: Graceful fallbacks when libraries are unavailable
- **Text Cleaning**: Utilities for filename sanitization and name extraction

# External Dependencies

## AI Services
- **Google Gemini API**: Primary LLM for semantic analysis and structured data extraction
- **API Authentication**: Requires `GEMINI_API_KEY` environment variable

## Python Libraries
- **Core Framework**: Streamlit for web application interface
- **Data Processing**: pandas, numpy for data manipulation
- **Database**: sqlite3 (built-in) for data persistence
- **File Processing**: 
  - PyMuPDF (fitz) - Primary PDF processing
  - pdfplumber - Secondary PDF processing fallback
  - python-docx - Primary DOCX processing
  - docx2txt - Secondary DOCX processing fallback
- **Machine Learning**: scikit-learn for TF-IDF vectorization and cosine similarity
- **Text Processing**: re (built-in) for regex operations

## Development Tools
- **JSON Handling**: Built-in json module for structured data storage
- **File Operations**: Built-in os and tempfile modules
- **Date/Time**: Built-in datetime module for timestamps
- **Type Hints**: typing module for better code documentation

## Optional Dependencies
- All parsing libraries include availability checks and graceful degradation
- TF-IDF functionality falls back when scikit-learn is unavailable
- System designed to work with minimal dependencies while providing enhanced features when full stack is available