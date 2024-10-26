import numpy as np
from flask import Flask, request, send_file, render_template_string
import json
import io

app = Flask(__name__)

def convert_json_to_lut(json_data):
    """Convert JSON data to LUT format."""
    try:
        # LUT size (33x33x33 is common)
        lut_size = 33

        def apply_color_balance(r, g, b, balance):
            """Apply color balance adjustment."""
            return [
                r * balance[0], 
                g * balance[1], 
                b * balance[1]
            ]

        # Generating LUT
        lut = np.zeros((lut_size, lut_size, lut_size, 3))

        # Fill the LUT
        for r in range(lut_size):
            for g in range(lut_size):
                for b in range(lut_size):
                    r_val = r / (lut_size - 1)
                    g_val = g / (lut_size - 1)
                    b_val = b / (lut_size - 1)

                    r_adj, g_adj, b_adj = apply_color_balance(
                        r_val, g_val, b_val, 
                        json_data["data"]["s"]["colorBalance"]
                    )
                    lut[r, g, b] = [r_adj, g_adj, b_adj]

        # Create .cube file content
        output = io.StringIO()
        output.write(f"TITLE \"{json_data['name']}\"\n")
        output.write(f"LUT_3D_SIZE {lut_size}\n")

        for r in range(lut_size):
            for g in range(lut_size):
                for b in range(lut_size):
                    r_val, g_val, b_val = lut[r, g, b]
                    output.write(f"{r_val:.6f} {g_val:.6f} {b_val:.6f}\n")

        return output.getvalue(), json_data['name']
    except Exception as e:
        raise ValueError(f"Error processing JSON: {str(e)}")

# HTML template with modern styling
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>JSON to LUT Converter</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .upload-section {
            margin: 20px 0;
            text-align: center;
        }
        .button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 0;
        }
        .button:hover {
            background-color: #45a049;
        }
        .error {
            color: #ff0000;
            margin: 10px 0;
            padding: 10px;
            border: 1px solid #ff0000;
            border-radius: 4px;
            background-color: #fff2f2;
        }
        .instructions {
            margin: 20px 0;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
        }
        #file-name {
            margin-top: 10px;
            font-style: italic;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>JSON to LUT Converter</h1>

        <div class="instructions">
            <h3>How to use:</h3>
            <ol>
                <li>Click "Choose File" to select your JSON file</li>
                <li>Click "Convert to LUT" to process the file</li>
                <li>Download your .cube file when ready</li>
            </ol>
        </div>

        <div class="upload-section">
            <form action="/convert" method="post" enctype="multipart/form-data">
                <input type="file" name="json_file" accept=".json" 
                       onchange="document.getElementById('file-name').textContent = this.files[0].name">
                <div id="file-name"></div>
                <input type="submit" value="Convert to LUT" class="button">
            </form>

            {% if error %}
            <div class="error">
                {{ error }}
            </div>
            {% endif %}

            {% if success %}
            <form action="/download" method="post">
                <input type="hidden" name="lut_content" value="{{ lut_content }}">
                <input type="hidden" name="filename" value="{{ filename }}">
                <input type="submit" value="Download .cube File" class="button">
            </form>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/convert', methods=['POST'])
def convert():
    try:
        if 'json_file' not in request.files:
            return render_template_string(HTML_TEMPLATE, error="No file uploaded")

        file = request.files['json_file']
        if file.filename == '':
            return render_template_string(HTML_TEMPLATE, error="No file selected")

        if not file.filename.endswith('.json'):
            return render_template_string(HTML_TEMPLATE, error="Please upload a JSON file")

        # Read and parse JSON
        json_content = file.read().decode('utf-8')
        json_data = json.loads(json_content)

        # Convert to LUT
        lut_content, filename = convert_json_to_lut(json_data)

        return render_template_string(
            HTML_TEMPLATE,
            success=True,
            lut_content=lut_content,
            filename=filename
        )

    except json.JSONDecodeError:
        return render_template_string(HTML_TEMPLATE, error="Invalid JSON file")
    except ValueError as e:
        return render_template_string(HTML_TEMPLATE, error=str(e))
    except Exception as e:
        return render_template_string(HTML_TEMPLATE, error=f"An error occurred: {str(e)}")

@app.route('/download', methods=['POST'])
def download():
    lut_content = request.form['lut_content']
    filename = request.form['filename']

    # Create BytesIO object
    bio = io.BytesIO()
    bio.write(lut_content.encode('utf-8'))
    bio.seek(0)

    return send_file(
        bio,
        mimetype='text/plain',
        as_attachment=True,
        download_name=f"{filename.replace(' ', '_')}.cube"
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)