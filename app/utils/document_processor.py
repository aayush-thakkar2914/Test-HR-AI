import PyPDF2
import docx
import io
from typing import List, Optional
import re

class DocumentProcessor:
    
    def extract_text_from_file(self, file_content: bytes, filename: str) -> Optional[str]:
        """Extract text from uploaded file based on file type"""
        try:
            file_extension = filename.lower().split('.')[-1]
            
            if file_extension == 'pdf':
                return self.extract_text_from_pdf(file_content)
            elif file_extension in ['docx', 'doc']:
                return self.extract_text_from_docx(file_content)
            elif file_extension == 'txt':
                return file_content.decode('utf-8')
            else:
                # Try to decode as text
                try:
                    return file_content.decode('utf-8')
                except:
                    return None
                    
        except Exception as e:
            print(f"Error extracting text from {filename}: {e}")
            return None
    
    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file"""
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return self.clean_text(text)
            
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""
    
    def extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            doc_file = io.BytesIO(file_content)
            doc = docx.Document(doc_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return self.clean_text(text)
            
        except Exception as e:
            print(f"Error reading DOCX: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)]', '', text)
        
        # Remove multiple consecutive newlines
        text = re.sub(r'\n+', '\n', text)
        
        return text.strip()
    
    def create_document_chunks(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split document into overlapping chunks for better search"""
        if not text:
            return []
        
        # Split into sentences first
        sentences = self.split_into_sentences(text)
        
        chunks = []
        current_chunk = ""
        current_size = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed chunk size, save current chunk
            if current_size + sentence_length > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap
                overlap_text = self.get_overlap_text(current_chunk, overlap)
                current_chunk = overlap_text + sentence
                current_size = len(current_chunk)
            else:
                current_chunk += " " + sentence
                current_size += sentence_length + 1
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting (could be improved with NLTK)
        sentences = re.split(r'[.!?]+', text)
        
        # Clean and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Filter out very short fragments
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def get_overlap_text(self, text: str, overlap_chars: int) -> str:
        """Get the last N characters for overlap"""
        if len(text) <= overlap_chars:
            return text
        
        # Try to break at word boundary
        overlap_text = text[-overlap_chars:]
        first_space = overlap_text.find(' ')
        
        if first_space > 0:
            return overlap_text[first_space:].strip()
        else:
            return overlap_text.strip()
    
    def extract_metadata(self, text: str) -> dict:
        """Extract metadata from document text"""
        metadata = {
            'word_count': len(text.split()),
            'char_count': len(text),
            'paragraph_count': text.count('\n\n') + 1,
            'has_tables': 'table' in text.lower() or '|' in text,
            'has_lists': bool(re.search(r'^\s*[\d\w]\.\s', text, re.MULTILINE)),
        }
        
        # Extract potential section headers
        headers = re.findall(r'^[A-Z][A-Z\s]{3,}$', text, re.MULTILINE)
        metadata['section_headers'] = headers[:10]  # First 10 headers
        
        return metadata
    
    def get_document_summary(self, text: str, max_length: int = 200) -> str:
        """Get a brief summary of the document"""
        if not text:
            return "No content available"
        
        # Take the first few sentences up to max_length
        sentences = self.split_into_sentences(text)
        summary = ""
        
        for sentence in sentences[:3]:  # First 3 sentences
            if len(summary + sentence) <= max_length:
                summary += sentence + ". "
            else:
                break
        
        if not summary and text:
            # Fallback: just take first max_length characters
            summary = text[:max_length] + "..."
        
        return summary.strip()