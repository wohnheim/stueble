import qrcode
from pyzbar.pyzbar import decode
from PIL import Image, ImageDraw
import io

def generate(code: str, size: int | None=None, rounded_edges: int | None=None):
    """
    Generate a QR code image from the given string.
    Parameters:
        code (str): The string to generate the QR code image from.
        size (int | None): The size of the QR code image
        rounded_edges (int | None): The radius of the rounded edges of the images.
    Returns:
        io.BytesIO: The generated QR code image as buffer.
    """

    qr = qrcode.QRCode(version=4, error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(code)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    img = img.convert("RGB")
    if size is not None:
        img = img.resize((size, size))

    if rounded_edges is not None:
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), img.size], radius=rounded_edges, fill=255)
        # Apply mask to the alpha channel
        img.putalpha(mask)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return buf

'''def read(qr_code: Image.Image):
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
    return {"success": False, "error": "No data found."}'''

if __name__ == "__main__":
    # Example usage
    img = generate("https://musikraum.onrender.com/")
    img.show()

    decoded = read(img)
    print(decoded)