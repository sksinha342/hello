import os
import io
import random
from flask import Flask, render_template_string, request, send_file
from PIL import Image, ImageDraw, ImageFont
from indic_unicode_reshaper import reshape  # <--- Ye Magic hai

app = Flask(__name__)

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_IMAGE_PATH = os.path.join(BASE_DIR, "form_viii_base.jpg")
FONT_PATH = os.path.join(BASE_DIR, "Kalam-Regular.ttf")

def get_hindi_font(size=28):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

def draw_hindi_text(draw, text, x, y, font, color="darkblue"):
    """
    Reshaper ka use karke Hindi text ko jodta hai 
    taki 'नमस्ते' broken na dikhe.
    """
    if not text: return
    # Step 1: Characters ko merge karna (स्त, क्त etc.)
    reshaped_text = reshape(text)
    # Step 2: Draw karna
    draw.text((x, y), reshaped_text, font=font, fill=color)

@app.route('/')
def index():
    return render_template_string("""
        <form method="POST" action="/generate">
            Naam: <input type="text" name="name" value="नमस्ते">
            Income: <input type="text" name="income">
            <input type="submit" value="Download Form">
        </form>
    """)

@app.route('/generate', methods=['POST'])
def generate():
    if not os.path.exists(BASE_IMAGE_PATH):
        return "Base image file missing!"

    # Image load karein
    img = Image.open(BASE_IMAGE_PATH).convert('RGB')
    draw = ImageDraw.Draw(img)
    font = get_hindi_font(30)

    # Inputs
    user_name = request.form.get('name', '')
    user_income = request.form.get('income', '')

    # Rendering (Yahan Reshaper kaam karega)
    draw_hindi_text(draw, user_name, 210, 245, font)
    draw_hindi_text(draw, user_income, 710, 835, font)

    # Memory mein save karke bhejna (Vercel compatible)
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG', quality=95)
    img_io.seek(0)

    return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name="Filled_Form.jpg")

if __name__ == "__main__":
    app.run(debug=True)
