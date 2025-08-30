import qrcode
from pyzbar.pyzbar import decode
from PIL import Image

def generate(code: str):
    """
    Generate a QR code image from the given string.
    Parameters:
        code (str): The string to generate the QR code image from.
    Returns:
        PIL.Image.Image: The generated QR code image.
    """

    qr = qrcode.QRCode(version=4, error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(code)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def read(qr_code: Image.Image):
    """
    Read a QR code image from a file and decode the string.
    Parameters:
        file (Image.Image): Image of the QR code
    Returns:
        str: The decoded string from the QR code image.
    """
    result = decode(qr_code)
    if result:
        return {"success": True, "data": result[0].data.decode("utf-8")}
    return {"success": False, "error": "No data found."}