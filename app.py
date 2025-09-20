import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import json

from resume_parser import ResumeParser
from job_analyzer import JobAnalyzer
from scoring_engine import ScoringEngine
import os

# Database fallback logic
try:
    if os.getenv("DATABASE_URL"):
        from postgres_database import PostgreSQLDatabase as Database
        DATABASE_TYPE = "postgresql"
    else:
        from database import Database
        DATABASE_TYPE = "sqlite"
except ImportError as e:
    # Fallback to SQLite if PostgreSQL dependencies are missing
    from database import Database
    DATABASE_TYPE = "sqlite"
    if os.getenv("DATABASE_URL"):
        st.warning("PostgreSQL dependencies not available. Falling back to SQLite database.")
from utils import format_score, get_verdict_color
from email_notifications import EmailNotifier
import zipfile
import io

# Initialize components with error handling
@st.cache_resource
def init_components():
    parser = ResumeParser()
    analyzer = JobAnalyzer()
    scorer = ScoringEngine()
    
    # Initialize database with error handling
    try:
        db = Database()
        # Test database connection
        db.get_dashboard_stats()
        return parser, analyzer, scorer, db
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")
        if DATABASE_TYPE == "postgresql":
            st.info("Trying to fallback to SQLite database...")
            try:
                from database import Database as SQLiteDatabase
                db = SQLiteDatabase()
                st.success("Successfully connected to SQLite database.")
                return parser, analyzer, scorer, db
            except Exception as sqlite_error:
                st.error(f"SQLite fallback also failed: {str(sqlite_error)}")
                st.stop()
        else:
            st.error("Please check your database configuration.")
            st.stop()

def main():
    st.set_page_config(
        page_title="Automated Resume Relevance Check System",
        page_icon="📋",
        layout="wide"
    )
    
    parser, analyzer, scorer, db = init_components()
    
    st.title("📋 Automated Resume Relevance Check System")
    st.markdown("### Innomatics Research Labs - Placement Team Dashboard")
    
    # Database status indicator
    if DATABASE_TYPE == "postgresql":
        st.sidebar.success("🗄️ PostgreSQL Connected")
    else:
        st.sidebar.info("🗄️ SQLite Connected")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select Page",
        ["Job Management", "Resume Analysis", "Bulk Processing", "Advanced Search", "Dashboard", "Analytics", "Team Alerts"]
    )
    
    if page == "Job Management":
        job_management_page(analyzer, db)
    elif page == "Resume Analysis":
        resume_analysis_page(parser, scorer, db)
    elif page == "Bulk Processing":
        bulk_processing_page(parser, scorer, db)
    elif page == "Advanced Search":
        advanced_search_page(db)
    elif page == "Dashboard":
        dashboard_page(db)
    elif page == "Analytics":
        analytics_page(db)
    elif page == "Team Alerts":
        team_alerts_page(db)

def job_management_page(analyzer, db):
    st.header("📄 Job Description Management")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Upload New Job Description")
        
        job_title = st.text_input("Job Title", placeholder="e.g., Senior Python Developer")
        company_name = st.text_input("Company Name", placeholder="e.g., Tech Corp")
        location = st.selectbox("Location", ["Hyderabad", "Bangalore", "Pune", "Delhi NCR"])
        
        job_description = st.text_area(
            "Job Description",
            height=300,
            placeholder="Paste the complete job description here..."
        )
        
        if st.button("Process Job Description", type="primary"):
            if job_title and company_name and job_description:
                try:
                    with st.spinner("Analyzing job description..."):
                        # Parse job description
                        parsed_jd = analyzer.parse_job_description(job_description)
                        
                        # Store in database
                        job_id = db.store_job_description(
                            title=job_title,
                            company=company_name,
                            location=location,
                            description=job_description,
                            parsed_data=parsed_jd
                        )
                        
                        st.success(f"✅ Job description processed successfully! Job ID: {job_id}")
                        
                        # Display parsed information
                        st.subheader("Extracted Information")
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.write("**Must-have Skills:**")
                            for skill in parsed_jd.get('must_have_skills', []):
                                st.write(f"• {skill}")
                        
                        with col_b:
                            st.write("**Good-to-have Skills:**")
                            for skill in parsed_jd.get('good_to_have_skills', []):
                                st.write(f"• {skill}")
                        
                        st.write("**Qualifications:**")
                        for qual in parsed_jd.get('qualifications', []):
                            st.write(f"• {qual}")
                            
                except Exception as e:
                    st.error(f"❌ Error processing job description: {str(e)}")
            else:
                st.warning("Please fill in all required fields.")
    
    with col2:
        st.subheader("Active Job Descriptions")
        
        # Get active jobs
        jobs = db.get_active_jobs()
        
        if jobs:
            for job in jobs:
                with st.expander(f"{job['title']} - {job['company']}"):
                    st.write(f"**Location:** {job['location']}")
                    st.write(f"**Posted:** {job['created_at']}")
                    st.write(f"**Applications:** {job['application_count']}")
                    
                    if st.button(f"View Details", key=f"view_{job['id']}"):
                        st.json(job['parsed_data'])
        else:
            st.info("No active job descriptions found.")

def resume_analysis_page(parser, scorer, db):
    st.header("🔍 Resume Analysis")
    
    # Get available jobs
    jobs = db.get_active_jobs()
    
    if not jobs:
        st.warning("Please add job descriptions first in the Job Management section.")
        return
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Resume Upload")
        
        # Job selection
        job_options = {f"{job['title']} - {job['company']}": job['id'] for job in jobs}
        selected_job = st.selectbox("Select Job Position", options=list(job_options.keys()))
        job_id = job_options[selected_job] if selected_job else None
        
        # Resume upload
        uploaded_files = st.file_uploader(
            "Upload Resume(s)",
            type=['pdf', 'docx'],
            accept_multiple_files=True,
            help="Upload PDF or DOCX files"
        )
        
        if uploaded_files and job_id:
            if st.button("Analyze Resumes", type="primary"):
                results = []
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, uploaded_file in enumerate(uploaded_files):
                    try:
                        status_text.text(f"Processing {uploaded_file.name}...")
                        
                        # Extract text from resume
                        resume_text = parser.extract_text(uploaded_file)
                        
                        if not resume_text.strip():
                            st.error(f"Could not extract text from {uploaded_file.name}")
                            continue
                        
                        # Get job details
                        job_details = db.get_job_by_id(job_id)
                        
                        # Analyze resume
                        analysis_result = scorer.analyze_resume(
                            resume_text, 
                            job_details['description'],
                            job_details['parsed_data']
                        )
                        
                        # Store result
                        analysis_id = db.store_analysis_result(
                            job_id=job_id,
                            resume_filename=uploaded_file.name,
                            resume_text=resume_text,
                            analysis_result=analysis_result
                        )
                        
                        results.append({
                            'filename': uploaded_file.name,
                            'analysis_id': analysis_id,
                            **analysis_result
                        })
                        
                        progress_bar.progress((i + 1) / len(uploaded_files))
                        
                    except Exception as e:
                        st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                
                status_text.text("Analysis complete!")
                
                # Display results
                if results:
                    st.subheader("Analysis Results")
                    display_analysis_results(results)
    
    with col2:
        st.subheader("Recent Analyses")
        
        if job_id:
            recent_analyses = db.get_recent_analyses(job_id, limit=10)
            
            if recent_analyses:
                for analysis in recent_analyses:
                    verdict_color = get_verdict_color(analysis['verdict'])
                    
                    with st.expander(f"{analysis['resume_filename']} - {analysis['verdict']}"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Relevance Score", f"{analysis['relevance_score']}/100")
                        with col_b:
                            st.markdown(f"**Verdict:** :{verdict_color}[{analysis['verdict']}]")
                        
                        st.write(f"**Analyzed:** {analysis['created_at']}")
                        
                        if st.button(f"View Full Report", key=f"report_{analysis['id']}"):
                            display_detailed_analysis(analysis)
            else:
                st.info("No analyses found for this job position.")

def display_analysis_results(results):
    """Display analysis results in a formatted way"""
    
    # Sort by relevance score
    results.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    for result in results:
        verdict_color = get_verdict_color(result['verdict'])
        
        with st.expander(f"{result['filename']} - Score: {result['relevance_score']}/100"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Relevance Score", f"{result['relevance_score']}/100")
            with col2:
                st.markdown(f"**Verdict:** :{verdict_color}[{result['verdict']}]")
            with col3:
                st.metric("Confidence", f"{result.get('confidence', 0):.2f}")
            
            st.subheader("Missing Skills")
            if result.get('missing_skills'):
                for skill in result['missing_skills']:
                    st.write(f"• {skill}")
            else:
                st.write("No major skills missing")
            
            st.subheader("Improvement Suggestions")
            if result.get('suggestions'):
                for suggestion in result['suggestions']:
                    st.write(f"• {suggestion}")
            
            if result.get('detailed_feedback'):
                st.subheader("Detailed Feedback")
                st.write(result['detailed_feedback'])

def display_detailed_analysis(analysis):
    """Display detailed analysis in a modal-like format"""
    st.subheader(f"Detailed Analysis: {analysis['resume_filename']}")
    
    # Parse the stored analysis result
    analysis_data = analysis.get('analysis_result', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Relevance Score", f"{analysis_data.get('relevance_score', 0)}/100")
        st.metric("Hard Match Score", f"{analysis_data.get('hard_match_score', 0)}/100")
    
    with col2:
        st.metric("Semantic Score", f"{analysis_data.get('semantic_score', 0)}/100")
        verdict_color = get_verdict_color(analysis_data.get('verdict', 'Low'))
        st.markdown(f"**Final Verdict:** :{verdict_color}[{analysis_data.get('verdict', 'Low')}]")
    
    # Missing elements
    if analysis_data.get('missing_skills'):
        st.subheader("Missing Skills")
        for skill in analysis_data['missing_skills']:
            st.write(f"• {skill}")
    
    # Suggestions
    if analysis_data.get('suggestions'):
        st.subheader("Improvement Suggestions")
        for suggestion in analysis_data['suggestions']:
            st.write(f"• {suggestion}")
    
    # Detailed feedback
    if analysis_data.get('detailed_feedback'):
        st.subheader("AI-Generated Feedback")
        st.write(analysis_data['detailed_feedback'])

def dashboard_page(db):
    st.header("📊 Placement Dashboard")
    
    # Get statistics
    stats = db.get_dashboard_stats()
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Jobs", stats.get('active_jobs', 0))
    with col2:
        st.metric("Total Analyses", stats.get('total_analyses', 0))
    with col3:
        st.metric("High Suitability", stats.get('high_suitability', 0))
    with col4:
        st.metric("This Week", stats.get('this_week_analyses', 0))
    
    # Job-wise analysis
    st.subheader("Job-wise Analysis Summary")
    
    job_stats = db.get_job_analysis_stats()
    
    if job_stats:
        df = pd.DataFrame(job_stats)
        
        # Create columns for better layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.dataframe(
                df[['title', 'company', 'location', 'total_applications', 'high_suitability', 'avg_score']],
                use_container_width=True
            )
        
        with col2:
            st.subheader("Quick Actions")
            selected_job = st.selectbox(
                "Select Job for Details",
                options=df['title'].tolist()
            )
            
            if selected_job:
                job_data = df[df['title'] == selected_job].iloc[0]
                
                st.write(f"**Company:** {job_data['company']}")
                st.write(f"**Location:** {job_data['location']}")
                st.write(f"**Applications:** {job_data['total_applications']}")
                st.write(f"**Avg Score:** {job_data['avg_score']:.1f}")
                
                if st.button("View All Candidates"):
                    # Get job ID and show candidates
                    job_id = job_data['id']
                    candidates = db.get_candidates_by_job(job_id)
                    
                    if candidates:
                        st.subheader(f"Candidates for {selected_job}")
                        candidates_df = pd.DataFrame(candidates)
                        st.dataframe(candidates_df, use_container_width=True)
    else:
        st.info("No job analysis data available.")

def analytics_page(db):
    st.header("📈 Analytics & Insights")
    
    # Get comprehensive statistics
    stats = db.get_dashboard_stats()
    
    # Key Performance Indicators
    st.subheader("📊 Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_analyses = stats.get('total_analyses', 0)
        st.metric("Total Analyses", total_analyses)
    
    with col2:
        high_suitability = stats.get('high_suitability', 0)
        success_rate = (high_suitability / max(total_analyses, 1)) * 100
        st.metric("Success Rate", f"{success_rate:.1f}%", delta=f"+{success_rate-70:.1f}%" if success_rate > 70 else f"{success_rate-70:.1f}%")
    
    with col3:
        this_week = stats.get('this_week_analyses', 0)
        st.metric("This Week", this_week)
    
    with col4:
        active_jobs = stats.get('active_jobs', 0)
        st.metric("Active Jobs", active_jobs)
    
    # Time-based analytics
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Applications Trend")
        time_data = db.get_applications_over_time(days=30)
        
        if time_data:
            df = pd.DataFrame(time_data)
            df['date'] = pd.to_datetime(df['date'])
            
            # Create line chart with trend
            st.line_chart(df.set_index('date')['count'])
            
            # Show trend analysis
            if len(df) > 1:
                recent_avg = df.tail(7)['count'].mean()
                older_avg = df.head(7)['count'].mean()
                trend = "↗️ Increasing" if recent_avg > older_avg else "↘️ Decreasing" if recent_avg < older_avg else "→ Stable"
                st.write(f"**Trend:** {trend}")
        else:
            st.info("No time-series data available.")
    
    with col2:
        st.subheader("🎯 Score Distribution")
        score_data = db.get_score_distribution()
        
        if score_data:
            df = pd.DataFrame(score_data)
            st.bar_chart(df.set_index('score_range')['count'])
            
            # Highlight high performers
            high_scores = next((item['count'] for item in score_data if item['score_range'] == '80-100'), 0)
            total_scores = sum(item['count'] for item in score_data)
            high_percentage = (high_scores / max(total_scores, 1)) * 100
            st.write(f"**High Performers (80-100):** {high_percentage:.1f}%")
        else:
            st.info("No score distribution data available.")
    
    # Placement Success Tracking
    st.subheader("🏆 Placement Success Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Job-wise performance
        job_stats = db.get_job_analysis_stats()
        
        if job_stats:
            df = pd.DataFrame(job_stats)
            
            # Calculate success metrics
            df['success_rate'] = (df['high_suitability'] / df['total_applications'] * 100).round(1)
            df['avg_score'] = df['avg_score'].round(1)
            
            # Sort by success rate
            df_sorted = df.sort_values('success_rate', ascending=False)
            
            st.write("**Job-wise Success Rates**")
            
            # Create a styled dataframe
            display_df = df_sorted[['title', 'company', 'location', 'total_applications', 'high_suitability', 'success_rate', 'avg_score']]
            display_df.columns = ['Job Title', 'Company', 'Location', 'Total Apps', 'High Scoring', 'Success Rate %', 'Avg Score']
            
            # Color code success rates
            def highlight_success_rate(val):
                if isinstance(val, (int, float)):
                    if val >= 30:
                        return 'background-color: #d4edda'  # Green
                    elif val >= 15:
                        return 'background-color: #fff3cd'  # Yellow
                    else:
                        return 'background-color: #f8d7da'  # Red
                return ''
            
            styled_df = display_df.style.applymap(highlight_success_rate, subset=['Success Rate %'])
            st.dataframe(styled_df, use_container_width=True)
        
        else:
            st.info("No job analysis data available.")
    
    with col2:
        st.write("**Success Rate Legend**")
        st.markdown("""
        🟢 **Excellent (30%+)**: Very high success rate  
        🟡 **Good (15-29%)**: Moderate success rate  
        🔴 **Needs Improvement (<15%)**: Low success rate
        """)
        
        # Top performing jobs
        if job_stats:
            st.write("**🏆 Top Performing Jobs**")
            top_jobs = sorted(job_stats, key=lambda x: x.get('avg_score', 0), reverse=True)[:3]
            
            for i, job in enumerate(top_jobs, 1):
                success_rate = (job['high_suitability'] / max(job['total_applications'], 1)) * 100
                st.write(f"**{i}. {job['title']}**")
                st.write(f"   Avg Score: {job['avg_score']:.1f}")
                st.write(f"   Success Rate: {success_rate:.1f}%")
                st.write("")
    
    # Location-wise Performance Analysis
    st.subheader("🌍 Location-wise Performance")
    location_stats = db.get_location_stats()
    
    if location_stats:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            df = pd.DataFrame(location_stats)
            df['success_rate'] = (df['high_suitability'] / df['applications'] * 100).round(1)
            
            # Sort by applications
            df_sorted = df.sort_values('applications', ascending=False)
            
            st.dataframe(df_sorted, use_container_width=True)
        
        with col2:
            # Location performance insights
            st.write("**📍 Location Insights**")
            
            best_location = df.loc[df['success_rate'].idxmax()]
            most_active = df.loc[df['applications'].idxmax()]
            
            st.write(f"**Best Success Rate:** {best_location['location']} ({best_location['success_rate']:.1f}%)")
            st.write(f"**Most Active:** {most_active['location']} ({most_active['applications']} applications)")
            
            # Create simple visualization
            st.write("**Applications Distribution:**")
            for _, row in df_sorted.iterrows():
                percentage = (row['applications'] / df['applications'].sum()) * 100
                st.progress(percentage/100, text=f"{row['location']}: {row['applications']} ({percentage:.1f}%)")
    
    else:
        st.info("No location statistics available.")
    
    # Weekly/Monthly Trends
    st.subheader("📅 Performance Trends")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Weekly performance comparison
        st.write("**Weekly Performance**")
        
        # Get last 4 weeks of data
        weekly_data = []
        for week_offset in range(4):
            start_date = datetime.now() - timedelta(weeks=week_offset+1)
            end_date = datetime.now() - timedelta(weeks=week_offset)
            
            # Simulate weekly data (you can implement actual weekly queries in the database)
            week_analyses = stats.get('this_week_analyses', 0) if week_offset == 0 else max(0, stats.get('this_week_analyses', 0) - week_offset * 5)
            
            weekly_data.append({
                'week': f"Week {4-week_offset}",
                'analyses': week_analyses,
                'date_range': f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}"
            })
        
        weekly_df = pd.DataFrame(weekly_data)
        
        # Simple bar chart
        for _, row in weekly_df.iterrows():
            st.write(f"**{row['week']}** ({row['date_range']}): {row['analyses']} analyses")
    
    with col2:
        # Export analytics data
        st.write("**📊 Export Analytics**")
        
        if st.button("Generate Analytics Report"):
            # Create comprehensive report
            report_data = {
                'summary': stats,
                'job_performance': job_stats,
                'location_stats': location_stats,
                'score_distribution': score_data,
                'time_series': time_data,
                'generated_at': datetime.now().isoformat()
            }
            
            report_json = json.dumps(report_data, indent=2, default=str)
            
            st.download_button(
                label="Download JSON Report",
                data=report_json,
                file_name=f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        # Quick actions
        st.write("**🚀 Quick Actions**")
        if st.button("Send Weekly Report"):
            try:
                notifier = EmailNotifier()
                top_candidates = db.get_high_scoring_candidates(min_score=70)
                notifier.send_daily_summary(stats, top_candidates)
                st.success("Weekly report sent!")
            except Exception as e:
                st.error(f"Failed to send report: {str(e)}")

def bulk_processing_page(parser, scorer, db):
    st.header("📦 Bulk Resume Processing")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Bulk Upload")
        
        # Get available jobs
        jobs = db.get_active_jobs()
        if not jobs:
            st.warning("Please add job descriptions first in the Job Management section.")
            return
        
        job_options = {f"{job['title']} - {job['company']}": job['id'] for job in jobs}
        selected_job = st.selectbox("Select Job Position", options=list(job_options.keys()))
        job_id = job_options[selected_job] if selected_job else None
        
        # ZIP file upload
        uploaded_zip = st.file_uploader(
            "Upload ZIP file containing resumes",
            type=['zip'],
            help="Upload a ZIP file containing PDF or DOCX resume files"
        )
        
        # Processing options
        st.subheader("Processing Options")
        min_score_filter = st.slider("Minimum score to save", 0, 100, 50)
        notify_high_scores = st.checkbox("Send email alerts for high-scoring candidates (75+)", value=True)
        
        if uploaded_zip and job_id:
            if st.button("Process All Resumes", type="primary"):
                process_bulk_resumes(uploaded_zip, job_id, parser, scorer, db, min_score_filter, notify_high_scores)
    
    with col2:
        st.subheader("Processing Status")
        
        # Show recent bulk processing jobs
        if 'bulk_processing_results' in st.session_state:
            results = st.session_state.bulk_processing_results
            
            st.metric("Total Processed", len(results))
            high_scores = sum(1 for r in results if r.get('relevance_score', 0) >= 75)
            st.metric("High Scores (75+)", high_scores)
            
            # Show top candidates
            st.subheader("Top Candidates")
            sorted_results = sorted(results, key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            for result in sorted_results[:10]:
                with st.expander(f"{result['filename']} - {result.get('relevance_score', 0)}/100"):
                    verdict_color = get_verdict_color(result.get('verdict', 'Low'))
                    st.markdown(f"**Verdict:** :{verdict_color}[{result.get('verdict', 'Low')}]")
                    
                    if result.get('missing_skills'):
                        st.write("**Missing Skills:**")
                        for skill in result['missing_skills'][:3]:
                            st.write(f"• {skill}")

def process_bulk_resumes(uploaded_zip, job_id, parser, scorer, db, min_score_filter, notify_high_scores):
    """Process multiple resumes from ZIP file"""
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Extract ZIP file
        with zipfile.ZipFile(io.BytesIO(uploaded_zip.getvalue())) as zip_file:
            resume_files = [f for f in zip_file.filelist if f.filename.lower().endswith(('.pdf', '.docx'))]
            
            if not resume_files:
                st.error("No PDF or DOCX files found in the ZIP archive.")
                return
            
            job_details = db.get_job_by_id(job_id)
            high_scoring_candidates = []
            
            for i, file_info in enumerate(resume_files):
                try:
                    status_text.text(f"Processing {file_info.filename}...")
                    
                    # Extract file content
                    file_content = zip_file.read(file_info.filename)
                    
                    # Create a file-like object for the parser
                    class FileWrapper:
                        def __init__(self, content, filename):
                            self.content = content
                            self.name = filename
                        
                        def getvalue(self):
                            return self.content
                    
                    file_wrapper = FileWrapper(file_content, file_info.filename)
                    
                    # Extract text
                    resume_text = parser.extract_text(file_wrapper)
                    
                    if not resume_text.strip():
                        st.warning(f"Could not extract text from {file_info.filename}")
                        continue
                    
                    # Analyze resume
                    analysis_result = scorer.analyze_resume(
                        resume_text, 
                        job_details['description'],
                        job_details['parsed_data']
                    )
                    
                    # Only save if meets minimum score
                    if analysis_result['relevance_score'] >= min_score_filter:
                        analysis_id = db.store_analysis_result(
                            job_id=job_id,
                            resume_filename=file_info.filename,
                            resume_text=resume_text,
                            analysis_result=analysis_result
                        )
                        
                        # Track high-scoring candidates
                        if analysis_result['relevance_score'] >= 75:
                            high_scoring_candidates.append({
                                'filename': file_info.filename,
                                'score': analysis_result['relevance_score'],
                                'job_title': job_details['title'],
                                'analysis_id': analysis_id
                            })
                    
                    results.append({
                        'filename': file_info.filename,
                        'analysis_id': analysis_id if analysis_result['relevance_score'] >= min_score_filter else None,
                        **analysis_result
                    })
                    
                    progress_bar.progress((i + 1) / len(resume_files))
                    
                except Exception as e:
                    st.error(f"Error processing {file_info.filename}: {str(e)}")
                    continue
            
            # Send notifications for high-scoring candidates
            if notify_high_scores and high_scoring_candidates:
                try:
                    notifier = EmailNotifier()
                    notifier.send_bulk_high_score_alert(high_scoring_candidates, job_details)
                    st.success(f"Email alerts sent for {len(high_scoring_candidates)} high-scoring candidates!")
                except Exception as e:
                    st.warning(f"Could not send email alerts: {str(e)}")
            
            st.session_state.bulk_processing_results = results
            status_text.text("Bulk processing complete!")
            
            # Summary
            st.success(f"Processed {len(results)} resumes. {len([r for r in results if r.get('analysis_id')])} saved (meeting minimum score).")
            
    except Exception as e:
        st.error(f"Error processing ZIP file: {str(e)}")

def advanced_search_page(db):
    st.header("🔍 Advanced Search & Filtering")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Search Filters")
        
        # Text search
        search_query = st.text_input("Search in resume text or filename", placeholder="Enter keywords...")
        
        # Job filter
        jobs = db.get_active_jobs()
        job_options = ["All Jobs"] + [f"{job['title']} - {job['company']}" for job in jobs]
        selected_job = st.selectbox("Filter by Job", job_options)
        job_id = None
        if selected_job != "All Jobs":
            job_id = next(job['id'] for job in jobs if f"{job['title']} - {job['company']}" == selected_job)
        
        # Score filters
        st.subheader("Score Range")
        min_score = st.slider("Minimum relevance score", 0, 100, 0)
        
        # Verdict filter
        verdict_filter = st.selectbox("Filter by verdict", ["All", "High", "Medium", "Low"])
        verdict = None if verdict_filter == "All" else verdict_filter
        
        # Location filter
        locations = ["All Locations", "Hyderabad", "Bangalore", "Pune", "Delhi NCR"]
        location_filter = st.selectbox("Filter by location", locations)
        location = None if location_filter == "All Locations" else location_filter
        
        # Skills filter
        skills_input = st.text_input("Filter by skills (comma-separated)", placeholder="python, react, machine learning")
        skills = [skill.strip() for skill in skills_input.split(",") if skill.strip()] if skills_input else None
        
        # Date filters
        st.subheader("Date Range")
        date_from = st.date_input("From date", value=None)
        date_to = st.date_input("To date", value=None)
        
        search_button = st.button("Search", type="primary")
    
    with col2:
        st.subheader("Search Results")
        
        if search_button or search_query:
            try:
                # Convert dates to datetime if provided
                datetime_from = pd.to_datetime(date_from) if date_from else None
                datetime_to = pd.to_datetime(date_to) if date_to else None
                
                # Perform search
                results = db.search_analyses(
                    query=search_query,
                    job_id=job_id,
                    min_score=min_score,
                    verdict=verdict,
                    location=location,
                    skills=skills,
                    date_from=datetime_from,
                    date_to=datetime_to
                )
                
                if results:
                    st.write(f"Found {len(results)} matching candidates")
                    
                    # Results table
                    df = pd.DataFrame([{
                        'Filename': r['resume_filename'],
                        'Score': r['relevance_score'],
                        'Verdict': r['verdict'],
                        'Job': r['job_title'],
                        'Company': r['company'],
                        'Date': r['created_at'].strftime('%Y-%m-%d') if hasattr(r['created_at'], 'strftime') else str(r['created_at'])
                    } for r in results])
                    
                    # Add color coding for verdict
                    def color_verdict(val):
                        colors = {'High': 'background-color: #d4edda', 
                                'Medium': 'background-color: #fff3cd', 
                                'Low': 'background-color: #f8d7da'}
                        return colors.get(val, '')
                    
                    styled_df = df.style.applymap(color_verdict, subset=['Verdict'])
                    st.dataframe(styled_df, use_container_width=True)
                    
                    # Export options
                    st.subheader("Export Results")
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        if st.button("Export to CSV"):
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="Download CSV",
                                data=csv,
                                file_name=f"search_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                    
                    with col_b:
                        # Create detailed report
                        if st.button("Generate Detailed Report"):
                            detailed_data = []
                            for result in results:
                                analysis = result.get('analysis_result', {})
                                detailed_data.append({
                                    'Filename': result['resume_filename'],
                                    'Score': result['relevance_score'],
                                    'Verdict': result['verdict'],
                                    'Job': result['job_title'],
                                    'Missing Skills': ', '.join(analysis.get('missing_skills', [])),
                                    'Found Skills': ', '.join(analysis.get('found_skills', [])),
                                    'Feedback': analysis.get('detailed_feedback', '')[:200] + '...' if analysis.get('detailed_feedback') else ''
                                })
                            
                            detailed_df = pd.DataFrame(detailed_data)
                            csv = detailed_df.to_csv(index=False)
                            st.download_button(
                                label="Download Detailed Report",
                                data=csv,
                                file_name=f"detailed_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                
                else:
                    st.info("No candidates found matching your criteria.")
                    
            except Exception as e:
                st.error(f"Search error: {str(e)}")

def team_alerts_page(db):
    st.header("🔔 Team Alerts & Notifications")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Alert Configuration")
        
        # Email settings
        st.write("**Email Notification Settings**")
        email_enabled = st.checkbox("Enable email notifications", value=True)
        
        if email_enabled:
            # Get team email addresses
            team_emails = st.text_area(
                "Team email addresses (one per line)",
                placeholder="manager@company.com\nhr@company.com\nrecruiter@company.com",
                height=100
            )
            
            # Alert thresholds
            st.write("**Alert Thresholds**")
            high_score_threshold = st.slider("High score alert threshold", 70, 100, 80)
            daily_summary = st.checkbox("Send daily summary reports", value=True)
            
            # Test email
            if st.button("Send Test Email"):
                try:
                    notifier = EmailNotifier()
                    test_emails = [email.strip() for email in team_emails.split('\n') if email.strip()]
                    notifier.send_test_email(test_emails)
                    st.success("Test email sent successfully!")
                except Exception as e:
                    st.error(f"Failed to send test email: {str(e)}")
    
    with col2:
        st.subheader("Recent High-Scoring Candidates")
        
        # Get high-scoring candidates from last 24 hours
        high_scoring = db.get_high_scoring_candidates(min_score=75)
        
        if high_scoring:
            for candidate in high_scoring[:10]:
                with st.expander(f"{candidate['resume_filename']} - {candidate['relevance_score']}/100"):
                    st.write(f"**Job:** {candidate['job_title']}")
                    st.write(f"**Company:** {candidate['company']}")
                    st.write(f"**Location:** {candidate['job_location']}")
                    st.write(f"**Analyzed:** {candidate['created_at']}")
                    
                    if st.button(f"Send Alert Now", key=f"alert_{candidate['id']}"):
                        try:
                            notifier = EmailNotifier()
                            team_emails_list = [email.strip() for email in team_emails.split('\n') if email.strip()]
                            notifier.send_high_score_alert(candidate, team_emails_list)
                            st.success("Alert sent!")
                        except Exception as e:
                            st.error(f"Failed to send alert: {str(e)}")
        else:
            st.info("No high-scoring candidates in the last 24 hours.")
    
    # Alert history
    st.subheader("Placement Success Tracking")
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        # Weekly stats
        stats = db.get_dashboard_stats()
        st.metric("This Week Applications", stats.get('this_week_analyses', 0))
    
    with col_b:
        st.metric("High Suitability Rate", f"{stats.get('high_suitability', 0)}/{stats.get('total_analyses', 0)}")
    
    with col_c:
        high_rate = (stats.get('high_suitability', 0) / max(stats.get('total_analyses', 1), 1)) * 100
        st.metric("Success Rate", f"{high_rate:.1f}%")

if __name__ == "__main__":
    main()
