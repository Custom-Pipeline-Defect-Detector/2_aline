from typing import Dict, Any, List
import pandas as pd
from io import BytesIO
import os
from datetime import datetime
from ..database import get_db
from ..models import User, Document
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

def create_excel_from_data(data: List[Dict[str, Any]], filename: str = None) -> str:
    """
    Creates an Excel file from provided data
    
    Args:
        data: List of dictionaries representing rows of data
        filename: Optional custom filename (without extension)
    
    Returns:
        Path to the created Excel file
    """
    try:
        # Create filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_excel_{timestamp}"
        
        # Ensure filename doesn't have extension
        if filename.endswith('.xlsx'):
            filename = filename[:-5]
        
        # Create uploads directory if it doesn't exist
        uploads_dir = "uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Full path for the Excel file
        filepath = os.path.join(uploads_dir, f"{filename}.xlsx")
        
        # Create DataFrame from data
        df = pd.DataFrame(data)
        
        # Write to Excel file
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False)
            
            # Get the workbook and worksheet to apply formatting
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)  # Cap width at 50
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        logger.info(f"Excel file created successfully at {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Error creating Excel file: {str(e)}")
        raise

def generate_excel_from_query(query: str, db_session: Session) -> str:
    """
    Generates an Excel file based on a natural language query
    
    Args:
        query: Natural language query describing what data to extract
        db_session: Database session
    
    Returns:
        Path to the created Excel file
    """
    try:
        # Parse the query to determine what data to extract
        query_lower = query.lower()
        
        # Determine what type of data to extract based on keywords
        if any(keyword in query_lower for keyword in ['customer', 'client', 'contact']):
            # Extract customer data
            from .customers import get_all_customers
            customers = get_all_customers(db_session)
            
            # Convert customers to list of dictionaries
            data = []
            for customer in customers:
                data.append({
                    'ID': customer.id,
                    'Name': customer.name,
                    'Email': customer.email,
                    'Company': customer.company,
                    'Phone': customer.phone,
                    'Address': customer.address,
                    'Created At': customer.created_at.isoformat() if customer.created_at else None
                })
                
        elif any(keyword in query_lower for keyword in ['project', 'job', 'work']):
            # Extract project data
            from ..models import Project
            projects = db_session.query(Project).all()
            
            # Convert projects to list of dictionaries
            data = []
            for project in projects:
                data.append({
                    'ID': project.id,
                    'Name': project.name,
                    'Description': project.description,
                    'Status': project.status,
                    'Start Date': project.start_date.isoformat() if project.start_date else None,
                    'End Date': project.end_date.isoformat() if project.end_date else None,
                    'Created At': project.created_at.isoformat() if project.created_at else None
                })
                
        elif any(keyword in query_lower for keyword in ['proposal', 'quote', 'bid']):
            # Extract proposal data
            from ..models import Proposal
            proposals = db_session.query(Proposal).all()
            
            # Convert proposals to list of dictionaries
            data = []
            for proposal in proposals:
                data.append({
                    'ID': proposal.id,
                    'Title': proposal.title,
                    'Description': proposal.description,
                    'Status': proposal.status,
                    'Value': proposal.value,
                    'Created At': proposal.created_at.isoformat() if proposal.created_at else None
                })
                
        elif any(keyword in query_lower for keyword in ['document', 'file', 'doc']):
            # Extract document data
            documents = db_session.query(Document).all()
            
            # Convert documents to list of dictionaries
            data = []
            for document in documents:
                data.append({
                    'ID': document.id,
                    'Filename': document.filename,
                    'Type': document.mime,
                    'Size': document.file_size,
                    'Processing Status': document.processing_status,
                    'Uploaded At': document.created_at.isoformat() if document.created_at else None
                })
                
        else:
            # Default: return a sample dataset
            data = [
                {'Column A': 'Sample Data', 'Column B': 'More Sample Data', 'Column C': 123},
                {'Column A': 'Another Row', 'Column B': 'More Data', 'Column C': 456},
                {'Column A': 'Final Row', 'Column B': 'End Data', 'Column C': 789}
            ]
        
        # Generate filename based on query
        clean_filename = "".join(c for c in query.replace(" ", "_") if c.isalnum() or c == '_')[:50]
        filename = f"excel_{clean_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create Excel file
        filepath = create_excel_from_data(data, filename)
        return filepath
        
    except Exception as e:
        logger.error(f"Error generating Excel from query: {str(e)}")
        raise