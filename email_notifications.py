
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any
import json

class EmailNotifier:
    """Email notification system for high-scoring candidates and team alerts"""
    
    def __init__(self):
        # Email configuration - using environment variables
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_user = os.getenv("EMAIL_USER", "")
        self.email_password = os.getenv("EMAIL_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.email_user)
        
        # Default team emails if not configured
        self.default_team_emails = [
            "placement@innomatics.in",
            "hr@innomatics.in"
        ]
    
    def send_high_score_alert(self, candidate: Dict[str, Any], team_emails: List[str] = None) -> bool:
        """Send alert for high-scoring candidate"""
        
        if not team_emails:
            team_emails = self.default_team_emails
        
        subject = f"🎯 High-Scoring Candidate Alert: {candidate['resume_filename']}"
        
        # Create HTML email content
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #28a745; color: white; padding: 20px; text-align: center;">
                <h1>🎯 High-Scoring Candidate Alert</h1>
            </div>
            
            <div style="padding: 20px; background-color: #f8f9fa;">
                <h2>Candidate Details</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background-color: white;">
                        <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Resume File</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{candidate['resume_filename']}</td>
                    </tr>
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Relevance Score</td>
                        <td style="padding: 10px; border: 1px solid #ddd; color: #28a745; font-weight: bold; font-size: 18px;">{candidate['relevance_score']}/100</td>
                    </tr>
                    <tr style="background-color: white;">
                        <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Job Position</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{candidate['job_title']}</td>
                    </tr>
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Company</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{candidate['company']}</td>
                    </tr>
                    <tr style="background-color: white;">
                        <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Location</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{candidate['job_location']}</td>
                    </tr>
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Analyzed At</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{candidate['created_at']}</td>
                    </tr>
                </table>
            </div>
            
            <div style="padding: 20px; background-color: white;">
                <h3>Analysis Summary</h3>
                <p>This candidate has achieved a high relevance score and should be prioritized for review.</p>
                
                <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <strong>Recommendation:</strong> Consider scheduling an interview or technical assessment.
                </div>
            </div>
            
            <div style="background-color: #6c757d; color: white; padding: 15px; text-align: center;">
                <p>Automated Resume Analysis System - Innomatics Research Labs</p>
                <p style="font-size: 12px;">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(team_emails, subject, html_content)
    
    def send_bulk_high_score_alert(self, candidates: List[Dict[str, Any]], job_details: Dict[str, Any]) -> bool:
        """Send alert for multiple high-scoring candidates from bulk processing"""
        
        subject = f"📦 Bulk Processing Alert: {len(candidates)} High-Scoring Candidates"
        
        # Create candidate table
        candidate_rows = ""
        for candidate in candidates:
            candidate_rows += f"""
            <tr style="background-color: {'#f8f9fa' if candidates.index(candidate) % 2 else 'white'};">
                <td style="padding: 8px; border: 1px solid #ddd;">{candidate['filename']}</td>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold; color: #28a745;">{candidate['score']}/100</td>
            </tr>
            """
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #17a2b8; color: white; padding: 20px; text-align: center;">
                <h1>📦 Bulk Processing Results</h1>
            </div>
            
            <div style="padding: 20px; background-color: #f8f9fa;">
                <h2>Job Details</h2>
                <p><strong>Position:</strong> {job_details['title']}</p>
                <p><strong>Company:</strong> {job_details['company']}</p>
                <p><strong>Location:</strong> {job_details['location']}</p>
            </div>
            
            <div style="padding: 20px; background-color: white;">
                <h2>High-Scoring Candidates ({len(candidates)} found)</h2>
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                    <thead>
                        <tr style="background-color: #17a2b8; color: white;">
                            <th style="padding: 10px; border: 1px solid #ddd;">Resume File</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {candidate_rows}
                    </tbody>
                </table>
            </div>
            
            <div style="background-color: #d4edda; padding: 15px; margin: 20px; border-radius: 5px;">
                <strong>Action Required:</strong> Review these high-scoring candidates in the system for potential interviews.
            </div>
            
            <div style="background-color: #6c757d; color: white; padding: 15px; text-align: center;">
                <p>Automated Resume Analysis System - Innomatics Research Labs</p>
                <p style="font-size: 12px;">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(self.default_team_emails, subject, html_content)
    
    def send_daily_summary(self, stats: Dict[str, Any], top_candidates: List[Dict[str, Any]]) -> bool:
        """Send daily summary report"""
        
        subject = f"📊 Daily Resume Analysis Summary - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Create top candidates table
        candidates_table = ""
        for candidate in top_candidates[:10]:
            candidates_table += f"""
            <tr style="background-color: {'#f8f9fa' if top_candidates.index(candidate) % 2 else 'white'};">
                <td style="padding: 8px; border: 1px solid #ddd;">{candidate.get('resume_filename', 'N/A')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{candidate.get('job_title', 'N/A')}</td>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{candidate.get('relevance_score', 0)}/100</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{candidate.get('verdict', 'N/A')}</td>
            </tr>
            """
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
            <div style="background-color: #007bff; color: white; padding: 20px; text-align: center;">
                <h1>📊 Daily Resume Analysis Summary</h1>
                <h2>{datetime.now().strftime('%B %d, %Y')}</h2>
            </div>
            
            <div style="padding: 20px; background-color: #f8f9fa;">
                <h2>Key Metrics</h2>
                <div style="display: flex; flex-wrap: wrap; gap: 15px;">
                    <div style="background-color: white; padding: 15px; border-radius: 8px; flex: 1; min-width: 150px; text-align: center;">
                        <h3 style="margin: 0; color: #007bff;">{stats.get('total_analyses', 0)}</h3>
                        <p style="margin: 5px 0;">Total Analyses</p>
                    </div>
                    <div style="background-color: white; padding: 15px; border-radius: 8px; flex: 1; min-width: 150px; text-align: center;">
                        <h3 style="margin: 0; color: #28a745;">{stats.get('high_suitability', 0)}</h3>
                        <p style="margin: 5px 0;">High Suitability</p>
                    </div>
                    <div style="background-color: white; padding: 15px; border-radius: 8px; flex: 1; min-width: 150px; text-align: center;">
                        <h3 style="margin: 0; color: #17a2b8;">{stats.get('active_jobs', 0)}</h3>
                        <p style="margin: 5px 0;">Active Jobs</p>
                    </div>
                </div>
            </div>
            
            <div style="padding: 20px; background-color: white;">
                <h2>Top Candidates Today</h2>
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                    <thead>
                        <tr style="background-color: #007bff; color: white;">
                            <th style="padding: 10px; border: 1px solid #ddd;">Resume</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">Job</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">Score</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">Verdict</th>
                        </tr>
                    </thead>
                    <tbody>
                        {candidates_table}
                    </tbody>
                </table>
            </div>
            
            <div style="background-color: #6c757d; color: white; padding: 15px; text-align: center;">
                <p>Automated Resume Analysis System - Innomatics Research Labs</p>
                <p style="font-size: 12px;">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(self.default_team_emails, subject, html_content)
    
    def send_test_email(self, team_emails: List[str]) -> bool:
        """Send test email to verify configuration"""
        
        subject = "✅ Test Email - Resume Analysis System"
        
        html_content = """
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
            <div style="background-color: #28a745; color: white; padding: 20px; text-align: center;">
                <h1>✅ Test Email Successful</h1>
            </div>
            
            <div style="padding: 20px; background-color: #f8f9fa;">
                <p>This is a test email from the Automated Resume Analysis System.</p>
                <p>If you're receiving this, email notifications are working correctly!</p>
            </div>
            
            <div style="background-color: #6c757d; color: white; padding: 15px; text-align: center;">
                <p>Automated Resume Analysis System - Innomatics Research Labs</p>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(team_emails, subject, html_content)
    
    def _send_email(self, to_emails: List[str], subject: str, html_content: str) -> bool:
        """Send email using SMTP"""
        
        if not self.email_user or not self.email_password:
            print("Email credentials not configured. Skipping email notification.")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            print(f"Email sent successfully to {', '.join(to_emails)}")
            return True
            
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return False
