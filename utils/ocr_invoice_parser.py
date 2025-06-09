import pytesseract

# Set up path to system's Tesseract binary
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_invoice_text(image_path):
    """
    Extract text from a given invoice image using Tesseract OCR.
    :param image_path: str - Path to the image file
    :return: str - Parsed text from image
    """
    return pytesseract.image_to_string(image_path)
