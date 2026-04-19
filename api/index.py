import os
import io
from flask import Flask, render_template_string, request, send_file
from PIL import Image, ImageDraw, ImageFont
from indic_unicode_reshaper import reshape

app = Flask(__name__)

# --- Path Configuration for Vercel ---
# Vercel mein api folder ke bahar files access karne ke liye
def get_base_path():
    # Vercel ke environment mein files root directory mein hoti hain
    if os.path.exists('/var/task/form_viii_base.jpg'):  # Vercel Lambda path
        return '/var/task'
    elif os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_viii_base.jpg')):
        return os.path.dirname(os.path.dirname(__file__))
    else:
        return os.getcwd()

BASE_DIR = get_base_path()
BASE_IMAGE_PATH = os.path.join(BASE_DIR, "form_viii_base.jpg")
FONT_PATH = os.path.join(BASE_DIR, "Kalam-Regular.ttf")

def get_hindi_font(size=28):
    if os.path.exists(FONT_PATH):
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except:
            print(f"Font loading error at {FONT_PATH}")
            return ImageFont.load_default()
    print(f"DEBUG: Font not found at {FONT_PATH}")
    return ImageFont.load_default()

def draw_hindi_text(draw, text, x, y, font, color="darkblue"):
    if not text: 
        return
    try:
        reshaped_text = reshape(str(text))
        draw.text((x, y), reshaped_text, font=font, fill=color)
    except Exception as e:
        print(f"Text drawing error: {e}")
        draw.text((x, y), str(text), font=font, fill=color)

@app.route('/')
def index():
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>OBC Form Generator</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }
                .container {
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    max-width: 500px;
                    width: 100%;
                }
                h2 {
                    color: #333;
                    margin-bottom: 30px;
                    text-align: center;
                }
                label {
                    font-weight: bold;
                    color: #555;
                    display: block;
                    margin-top: 15px;
                }
                input {
                    width: 100%;
                    padding: 12px;
                    margin-top: 5px;
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    font-size: 16px;
                    font-family: 'Kalam', monospace;
                }
                button {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 14px 30px;
                    border-radius: 8px;
                    font-size: 18px;
                    cursor: pointer;
                    margin-top: 25px;
                    width: 100%;
                    transition: transform 0.2s;
                }
                button:hover {
                    transform: translateY(-2px);
                }
                .note {
                    font-size: 12px;
                    color: #888;
                    text-align: center;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>📄 OBC Income Certificate Form</h2>
                <form method="POST" action="/generate">
                    <label>नाम (Name in Hindi):</label>
                    <input type="text" name="name" placeholder="उदाहरण: राम कुमार" required>
                    
                    <label>वार्षिक आय (Annual Income):</label>
                    <input type="text" name="income" placeholder="उदाहरण: 2,50,000 रुपये" required>
                    
                    <button type="submit">📥 Download Filled Form (JPG)</button>
                </form>
                <div class="note">
                    ⚡ फॉर्म जेनरेट होने के बाद अपने आप डाउनलोड हो जाएगा
                </div>
            </div>
        </body>
        </html>
    """)

@app.route('/generate', methods=['POST'])
def generate():
    # Check if base image exists
    if not os.path.exists(BASE_IMAGE_PATH):
        return f"Error: Base image missing at {BASE_IMAGE_PATH}. Please upload form_viii_base.jpg"

    try:
        # Open and process image
        img = Image.open(BASE_IMAGE_PATH).convert('RGB')
        draw = ImageDraw.Draw(img)
        font = get_hindi_font(30)

        # Get form data
        user_name = request.form.get('name', '')
        user_income = request.form.get('income', '')

        # Draw text at specific coordinates
        draw_hindi_text(draw, user_name, 210, 245, font)
        draw_hindi_text(draw, user_income, 710, 835, font)

        # Save to memory
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG', quality=95)
        img_io.seek(0)

        # Return as downloadable file
        return send_file(
            img_io, 
            mimetype='image/jpeg', 
            as_attachment=True, 
            download_name="OBC_Filled_Form.jpg"
        )
    
    except Exception as e:
        return f"Error generating form: {str(e)}"

# Vercel handler
app.debug = False
