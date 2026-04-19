import os
import io
import random
from flask import Flask, render_template_string, request, send_file
from PIL import Image, ImageDraw, ImageFont
from indic_unicode_reshaper import reshape

app = Flask(__name__)

# --- Vercel ke liye Path Fix ---
# Vercel par files 'api' ke bahar (root mein) ho sakti hain, isliye root ko dhundna zaroori hai
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_IMAGE_PATH = os.path.join(BASE_DIR, "form_viii_base.jpg")
FONT_PATH = os.path.join(BASE_DIR, "Kalam-Regular.ttf")

def get_hindi_font(size=28):
    # Debugging ke liye check: Agar path nahi mila to error print karega logs mein
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    print(f"DEBUG: Font not found at {FONT_PATH}") # Ye Vercel logs mein dikhega
    return ImageFont.load_default()

def draw_hindi_text(draw, text, x, y, font, color="darkblue"):
    if not text: return
    reshaped_text = reshape(str(text)) # String check zaroori hai
    draw.text((x, y), reshaped_text, font=font, fill=color)

@app.route('/')
def index():
    return render_template_string("""
        <div style="font-family: sans-serif; padding: 20px;">
            <h2>OBC Form Generator</h2>
            <form method="POST" action="/generate">
                Naam: <br><input type="text" name="name" value="नमस्ते"><br><br>
                Income: <br><input type="text" name="income"><br><br>
                <input type="submit" value="Download Filled Form (JPG)">
            </form>
        </div>
    """)

@app.route('/generate', methods=['POST'])
def generate():
    if not os.path.exists(BASE_IMAGE_PATH):
        return f"Error: Base image missing at {BASE_IMAGE_PATH}"

    img = Image.open(BASE_IMAGE_PATH).convert('RGB')
    draw = ImageDraw.Draw(img)
    font = get_hindi_font(30)

    user_name = request.form.get('name', '')
    user_income = request.form.get('income', '')

    draw_hindi_text(draw, user_name, 210, 245, font)
    draw_hindi_text(draw, user_income, 710, 835, font)

    img_io = io.BytesIO()
    img.save(img_io, 'JPEG', quality=95)
    img_io.seek(0)

    return send_file(
        img_io, 
        mimetype='image/jpeg', 
        as_attachment=True, 
        download_name="Filled_Form.jpg"
    )

# --- Vercel ke liye ye zaroori hai ---
app.debug = True
# if __name__ == "__main__": hata dein, Vercel ise handle karta hai
