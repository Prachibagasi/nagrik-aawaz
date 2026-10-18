from typing import Dict, List, Any, Optional, Tuple
import sys
import os

# Add parent directory to path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ShortlisterAgent:
    """Agent to shortlist candidates based on match scores"""
    
    def __init__(self, threshold: float = 80.0, top_n: Optional[int] = None):
        """Initialize Shortlister Agent
        
        Args:
            threshold: Minimum score threshold for shortlisting (default: 80.0)
            top_n: If set, keep at most this many candidates per job (the best-scoring
                ones that also meet the threshold)
        """
        self.threshold = threshold
        self.top_n = top_n
    
    def shortlist_candidates(self, matches: Dict[str, List[Tuple[Dict[str, Any], float]]]) -> Dict[str, List[Tuple[Dict[str, Any], float]]]:
        """Shortlist candidates based on match score threshold
        
        Args:
            matches: Dictionary mapping job title to list of (CV, score) tuples
            
        Returns:
            Dictionary mapping job title to shortlisted (CV, score) tuples
        """
        shortlisted = {}
        
        for job_title, job_matches in matches.items():
            # Filter by threshold
            job_shortlisted = [(cv, score) for cv, score in job_matches if score >= self.threshold]
            job_shortlisted.sort(key=lambda pair: pair[1], reverse=True)
            if self.top_n is not None:
                job_shortlisted = job_shortlisted[:self.top_n]
            
            if job_shortlisted:
                shortlisted[job_title] = job_shortlisted
        
        return shortlisted
    
    def print_shortlist_summary(self, shortlisted: Dict[str, List[Tuple[Dict[str, Any], float]]]) -> None:
        """Print summary of shortlisted candidates
        
        Args:
            shortlisted: Dictionary mapping job title to shortlisted (CV, score) tuples
        """
        print("\n===== SHORTLISTED CANDIDATES =====")
        
        for job_title, candidates in shortlisted.items():
            print(f"\nJob: {job_title}")
            print(f"Number of shortlisted candidates: {len(candidates)}")
            
            for i, (cv, score) in enumerate(candidates):
                print(f"  {i+1}. {cv.get('name', 'Unknown')} - Score: {score:.2f}%")
    
    def get_shortlist_data(self, shortlisted: Dict[str, List[Tuple[Dict[str, Any], float]]]) -> List[Dict[str, Any]]:
        """Convert shortlisted data to format suitable for database storage
        
        Args:
            shortlisted: Dictionary mapping job title to shortlisted (CV, score) tuples
            
        Returns:
            List of dictionaries with shortlisted candidate data
        """
        shortlist_data = []
        
        for job_title, candidates in shortlisted.items():
            for cv, score in candidates:
                entry = {
                    'job_title': job_title,
                    'cv_filename': cv.get('filename', ''),
                    'name': cv.get('name', 'Unknown'),
                    'email': cv.get('email', ''),
                    'phone': cv.get('phone', ''),
                    'score': score
                }
                shortlist_data.append(entry)
        
        return shortlist_data 