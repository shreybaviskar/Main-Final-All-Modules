import base64
import io
import json

import logging
_logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    from PIL import Image
    import pdfplumber

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google Generative AI libraries not installed. Please install: pip install google-generativeai pillow pdfplumber")

class GeminiExtractor:
    """Utility class for extracting structured data from images and PDFs using Gemini AI"""

    def __init__(self, api_key=None):
        """Initialize Gemini with API key"""
        if not GEMINI_AVAILABLE:
            raise ImportError("Required libraries not installed. Install: pip install google-generativeai pillow pdfplumber")

        if not api_key:
            raise ValueError("Gemini API key is not set. Please Configure it in Odoo Settings.")

        self.api_key = api_key
        genai.configure(api_key=self.api_key)

        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Find and initialize an available Gemini model"""
        try:
            # Try to get available models
            available_models = []
            for model in genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    model_name = model.name.replace('models/', '')
                    available_models.append(model_name)

            if available_models:
                # Prefer vision-capable models
                vision_models = [m for m in available_models if any(x in m.lower() for x in ['vision', 'flash', '1.5'])]
                if vision_models:
                    self.model = genai.GenerativeModel(vision_models[0])
                else:
                    self.model = genai.GenerativeModel(available_models[0])
            else:
                # Fallback to common models
                for model_name in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro-vision', 'gemini-pro']:
                    try:
                        self.model = genai.GenerativeModel(model_name)
                        break
                    except Exception:
                        continue

            if not self.model:
                raise Exception("No available Gemini models found")

        except Exception as e:
            _logger.error(f"Error initializing Gemini model: {str(e)}")
            raise

    def extract_from_image(self, image_data):
        """
        Extract structured data from image

        Args:
            image_data: Binary image data (base64 or bytes)

        Returns:
            dict: Extracted structured data
        """
        try:
            # Convert base64 to PIL Image if needed
            if isinstance(image_data, str):
                # Clean the base64 string - remove whitespace and ensure proper padding
                base64_str = image_data.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                
                # Add padding if needed
                missing_padding = len(base64_str) % 4
                if missing_padding:
                    base64_str += '=' * (4 - missing_padding)
                
                try:
                    image_bytes = base64.b64decode(base64_str, validate=True)
                except Exception as e:
                    _logger.error(f"Error decoding base64: {str(e)}")
                    # Try without validation
                    image_bytes = base64.b64decode(base64_str)
                
                # Open the image
                image = Image.open(io.BytesIO(image_bytes))
            elif isinstance(image_data, bytes):
                # Open the image directly from bytes
                image = Image.open(io.BytesIO(image_data))
            else:
                image = image_data

            # Convert image to RGB mode and save as PNG bytes to avoid WEBP format issues
            # Gemini's library tries to convert to WEBP which may not be supported
            try:
                # Convert to RGB if image has transparency or is in a different mode
                if image.mode in ('RGBA', 'LA', 'P'):
                    # Create a white background for transparent images
                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                    image = rgb_image
                elif image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Save as PNG bytes to pass to Gemini (avoids WEBP conversion)
                png_buffer = io.BytesIO()
                image.save(png_buffer, format='PNG')
                png_bytes = png_buffer.getvalue()
                png_buffer.close()
                
                # Use the PNG bytes directly instead of PIL Image to avoid WEBP conversion
                image_for_gemini = png_bytes
            except Exception as e:
                _logger.warning(f"Could not convert image format, using original: {str(e)}")
                # Fallback: try to convert to RGB and save as JPEG
                try:
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    jpeg_buffer = io.BytesIO()
                    image.save(jpeg_buffer, format='JPEG', quality=95)
                    image_for_gemini = jpeg_buffer.getvalue()
                    jpeg_buffer.close()
                except Exception as e2:
                    _logger.error(f"Failed to convert image: {str(e2)}")
                    # Last resort: use original image
                    image_for_gemini = image

            extract_prompt = """Extract ALL information from this image and return it as a JSON object with the following structure. Extract everything you can see:

{
    "contact_name": "Full name of the person (if visible)",
    "company_name": "Company or organization name (if visible)",
    "email": "Email address (if visible)",
    "phone": "Phone number (if visible)",
    "mobile": "Mobile number (if visible)",
    "website": "Website URL (if visible)",
    "street": "Street address (if visible)",
    "street2": "Additional address line (if visible)",
    "city": "City name (if visible)",
    "state": "State or province name (if visible)",
    "zip": "ZIP or postal code (if visible)",
    "country": "Country name (if visible)",
    "title": "Job title or document title (if visible)",
    "job_position": "Job position or designation (if visible on business card)",
    "description": "Any additional text content, notes, or description",
    "document_number": "Any ID numbers, document numbers, reference numbers (if visible)",
    "date": "Any dates visible (birth date, expiry date, issue date, etc.)",
    "other_info": "Any other relevant information extracted"
}

IMPORTANT: 
- Return ONLY valid JSON, no additional text before or after
- If a field is not found, use null or empty string
- Extract all visible text, numbers, and information
- Be thorough and extract everything you can see"""

            # Pass image as dictionary with explicit MIME type to avoid WEBP conversion
            # Gemini's library tries to convert PIL Images to WEBP, but passing bytes
            # with explicit MIME type should avoid this
            if not isinstance(image_for_gemini, bytes):
                # If it's still a PIL Image, convert to PNG bytes
                img_buffer = io.BytesIO()
                if hasattr(image_for_gemini, 'save'):
                    image_for_gemini.save(img_buffer, format='PNG')
                    image_for_gemini = img_buffer.getvalue()
                else:
                    raise ValueError("Cannot convert image to bytes")
            
            # Pass as dictionary with explicit PNG MIME type to avoid WEBP conversion
            response = self.model.generate_content([
                {"mime_type": "image/png", "data": image_for_gemini},
                extract_prompt
            ])
            response_text = response.text.strip()

            # Clean response text (remove markdown code blocks if present)
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            elif response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON
            extracted_data = json.loads(response_text)
            return extracted_data

        except json.JSONDecodeError as e:
            _logger.error(f"Error parsing JSON from Gemini response: {str(e)}")
            _logger.error(f"Response was: {response_text[:500]}")
            # Try to extract fields manually from text
            return self._parse_text_response(response_text)
        except Exception as e:
            _logger.error(f"Error extracting from image: {str(e)}")
            raise

    def extract_from_pdf(self, pdf_data):
        """
        Extract structured data from PDF

        Args:
            pdf_data: Binary PDF data (base64 or bytes)

        Returns:
            dict: Extracted structured data
        """
        try:
            # Convert base64 to bytes if needed
            if isinstance(pdf_data, str):
                pdf_bytes = base64.b64decode(pdf_data)
            else:
                pdf_bytes = pdf_data

            # Extract text from PDF
            pdf_text = ""
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pdf_text += page_text + "\n\n"

            if not pdf_text.strip():
                raise ValueError("Could not extract text from PDF")

            # Use Gemini to extract structured data from text
            extract_prompt = f"""Extract ALL information from the following text content and return it as a JSON object with the following structure:

{pdf_text[:15000]}  # Limit to avoid token limits

Return JSON with this structure:
{{
    "contact_name": "Full name of the person (if found)",
    "company_name": "Company or organization name (if found)",
    "email": "Email address (if found)",
    "phone": "Phone number (if found)",
    "mobile": "Mobile number (if found)",
    "website": "Website URL (if found)",
    "street": "Street address (if found)",
    "street2": "Additional address line (if found)",
    "city": "City name (if found)",
    "state": "State or province name (if found)",
    "zip": "ZIP or postal code (if found)",
    "country": "Country name (if found)",
    "title": "Job title or document title (if found)",
    "job_position": "Job position or designation (if found on business card)",
    "description": "Any additional text content, notes, or description",
    "document_number": "Any ID numbers, document numbers, reference numbers (if found)",
    "date": "Any dates found (birth date, expiry date, issue date, etc.)",
    "other_info": "Any other relevant information extracted"
}}

IMPORTANT: 
- Return ONLY valid JSON, no additional text before or after
- If a field is not found, use null or empty string
- Extract all information from the text
- Be thorough and extract everything"""

            response = self.model.generate_content(extract_prompt)
            response_text = response.text.strip()

            # Clean response text
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            elif response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON
            extracted_data = json.loads(response_text)
            return extracted_data

        except json.JSONDecodeError as e:
            _logger.error(f"Error parsing JSON from Gemini response: {str(e)}")
            _logger.error(f"Response was: {response_text[:500]}")
            # Try to extract fields manually from text
            return self._parse_text_response(response_text)
        except Exception as e:
            _logger.error(f"Error extracting from PDF: {str(e)}")
            raise

    def _parse_text_response(self, text):
        """Fallback: Try to extract fields from plain text response"""
        extracted = {
            "contact_name": "",
            "company_name": "",
            "email": "",
            "phone": "",
            "mobile": "",
            "website": "",
            "street": "",
            "street2": "",
            "city": "",
            "state": "",
            "zip": "",
            "country": "",
            "title": "",
            "description": text[:1000] if text else "",
            "document_number": "",
            "date": "",
            "other_info": ""
        }

        # Try basic regex patterns to extract common fields
        import re

        # Email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            extracted["email"] = email_match.group()

        # Phone (various formats)
        phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        if phone_match:
            extracted["phone"] = phone_match.group()

        return extracted

