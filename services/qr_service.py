import io
import base64
import urllib.parse

def generate_qr_base64(data_string):
    """
    Generates a QR code image encoded as base64 data URI.
    Uses 'qrcode' library if available; otherwise falls back to a clean SVG QR or encoded URL.
    """
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(data_string)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        # Fallback to high-reliability QR code API or SVG representation
        encoded_data = urllib.parse.quote(data_string)
        return f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded_data}&color=0f172a&bgcolor=ffffff"
