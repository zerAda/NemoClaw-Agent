from fpdf import FPDF
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PDFService:
    """Standard-Grade Document Generator for autonomous submission."""
    
    def __init__(self):
        pass

    def create_cover_letter(self, subject: str, body: str, output_path: str):
        """Generates a professional PDF cover letter.
        
        Diamond-Grade typography: Standard 12pt clean serif/sans-serif.
        """
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Header Info
            pdf.set_font("Helvetica", 'B', 16)
            pdf.cell(0, 10, subject, ln=True, align='C')
            pdf.ln(5)
            
            # Date and Location
            pdf.set_font("Helvetica", '', 10)
            now_str = datetime.now().strftime("%d/%m/%Y")
            pdf.cell(0, 10, f"Le {now_str}", ln=True, align='R')
            pdf.ln(10)
            
            # Main Body
            pdf.set_font("Helvetica", '', 11)
            # EXPERT: Multi-cell for wrapping long text blocks correctly
            pdf.multi_cell(0, 8, body)
            
            # Save
            pdf.output(output_path)
            logger.info(f"PDF Generated successfully: {output_path}")
            return True
        except Exception as e:
            logger.error(f"PDF Generation failure: {e}")
            return False
