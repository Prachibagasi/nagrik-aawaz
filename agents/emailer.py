import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Any, Optional
import os
import sys
import re

# Add parent directory to path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class EmailerAgent:
    """Agent to send interview invitation emails to shortlisted candidates"""
    
    def __init__(self, smtp_server: str = None, port: int = None, sender_email: str = None, password: str = None, simulate: bool = True):
        """Initialize Emailer Agent
        
        Args:
            smtp_server: SMTP server address
            port: SMTP server port
            sender_email: Sender email address
            password: Email password
            simulate: Whether to simulate sending emails or actually send them
        """
        self.smtp_server = smtp_server or os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.port = port or int(os.environ.get('SMTP_PORT', 587))
        self.sender_email = sender_email or os.environ.get('SENDER_EMAIL', 'recruiter@example.com')
        self.password = password or os.environ.get('EMAIL_PASSWORD', '')
        self.simulate = simulate
        if not self.simulate and (not self.password or self.sender_email == 'recruiter@example.com'):
            raise ValueError(
                "Live email sending needs SENDER_EMAIL and EMAIL_PASSWORD to be set "
                "(and SMTP_SERVER / SMTP_PORT if you don't use Gmail)."
            )
    
    def generate_email_content(self, candidate_data: Dict[str, Any], job_title: str, required_skills: str = None) -> str:
        """Generate personalized email content for a candidate
        
        Args:
            candidate_data: Dictionary with candidate information
            job_title: Job title
            required_skills: Required skills for the job
            
        Returns:
            Formatted email content
        """
        candidate_name = candidate_data.get('name', 'Candidate')
        candidate_skills = candidate_data.get('skills', '')
        
        # Extract matched skills (skills mentioned in both required_skills and candidate_skills)
        matched_skills = []
        if required_skills and candidate_skills:
            required_skill_list = [skill.strip() for skill in required_skills.split(',')]
            candidate_skill_list = [skill.strip() for skill in candidate_skills.split(',')]
            
            for skill in required_skill_list:
                # Simple fuzzy matching
                for candidate_skill in candidate_skill_list:
                    if skill.lower() in candidate_skill.lower() or candidate_skill.lower() in skill.lower():
                        matched_skills.append(skill)
                        break
        
        # Format matched skills for email
        matched_skills_text = ""
        if matched_skills:
            matched_skills_text = ", ".join(matched_skills)
            matched_skills_text = f"\nBased on your resume, we were particularly impressed with your experience in: {matched_skills_text}."
        
        # Generate email content
        email_content = f"""Subject: Interview Invitation for {job_title} Position

Dear {candidate_name},

We hope this email finds you well. Thank you for your application for the {job_title} position at our company.

We have reviewed your resume and qualifications, and we are pleased to invite you for an interview.{matched_skills_text}

During the interview, we would like to discuss your experiences, skills, and how you might fit with our team. Please let us know your availability for the next week by replying to this email.

If you have any questions before the interview, please don't hesitate to ask.

We look forward to speaking with you.

Best regards,
The Recruitment Team
"""
        
        return email_content
    
    def send_email(self, recipient_email: str, content: str) -> bool:
        """Send email to recipient
        
        Args:
            recipient_email: Recipient email address
            content: Email content
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if self.simulate:
            print(f"\n--- Simulated Email to: {recipient_email} ---")
            print(content)
            print("--- End of Simulated Email ---\n")
            return True
        
        try:
            # Extract subject from content
            subject_match = re.search(r'Subject: (.*?)$', content, re.MULTILINE)
            subject = subject_match.group(1) if subject_match else "Interview Invitation"
            
            # Remove subject line from content
            content = re.sub(r'Subject: .*?$', '', content, flags=re.MULTILINE).strip()
            
            # Create a multipart message
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = recipient_email
            message["Subject"] = subject
            
            # Add content to message
            message.attach(MIMEText(content, "plain"))
            
            # Create a secure SSL context
            context = ssl.create_default_context()
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.starttls(context=context)
                server.login(self.sender_email, self.password)
                server.sendmail(self.sender_email, recipient_email, message.as_string())
            
            return True
            
        except Exception as e:
            print(f"Error sending email to {recipient_email}: {str(e)}")
            return False
    
    def send_interview_invitations(self, shortlisted_data: List[Dict[str, Any]], jd_data_by_title: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Send interview invitations to all shortlisted candidates
        
        Args:
            shortlisted_data: List of dictionaries with shortlisted candidate data
            jd_data_by_title: Dictionary mapping job titles to JD data
            
        Returns:
            List of dictionaries with email sending results
        """
        email_results = []
        
        for candidate in shortlisted_data:
            job_title = candidate.get('job_title', '')
            email = candidate.get('email', '')
            
            if not email:
                print(f"No email found for candidate: {candidate.get('name', 'Unknown')}")
                continue
            
            # Get JD data for this job title
            jd_data = jd_data_by_title.get(job_title, {})
            required_skills = jd_data.get('summary', {}).get('required_skills', [])
            if isinstance(required_skills, list):
                required_skills = ", ".join(required_skills)
            
            # Generate and send email
            content = self.generate_email_content(candidate, job_title, required_skills)
            success = self.send_email(email, content)
            
            result = {
                'candidate': candidate,
                'job_title': job_title,
                'email': email,
                'success': success,
                'timestamp': datetime.now().isoformat()
            }
            
            email_results.append(result)
        
        return email_results
    
    def print_email_summary(self, email_results: List[Dict[str, Any]]) -> None:
        """Print summary of email sending results
        
        Args:
            email_results: List of dictionaries with email sending results
        """
        print("\n===== EMAIL SUMMARY =====")
        print(f"Total emails to send: {len(email_results)}")
        
        success_count = sum(1 for result in email_results if result['success'])
        print(f"Successfully sent: {success_count}")
        print(f"Failed to send: {len(email_results) - success_count}")
        
        if not self.simulate:
            print("\nEmails sent to:")
            for result in email_results:
                if result['success']:
                    print(f"  - {result['email']} ({result['candidate']['name']})")
        else:
            print("\nEmails were simulated (not actually sent)") 