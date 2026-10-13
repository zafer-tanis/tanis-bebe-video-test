import os
import subprocess
import tempfile
from pathlib import Path
from flask import Flask, request, send_file, abort
from PIL import Image, ImageOps, ImageDraw, ImageFont
from io import BytesIO
import secrets

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 25_000_000

@app.get('/')
def home():
    return '''<!doctype html><meta charset="utf-8"><title>Tanış Bebe video testi</title>
    <h1>Tanış Bebe — yalnızca video oluşturma testi</h1>
    <p>Instagram'a yayın yapmaz. Gerçek ürün görsellerini sırayla seçin.</p>
    <form action="/video" method="post" enctype="multipart/form-data">
    <p>Test anahtarı: <input name="key" type="password" required></p>
    <p>Ürün kodu: <input name="sku" maxlength="40" required></p>
    <p>Görseller: <input type="file" name="images" accept="image/*" multiple required></p>
    <button>MP4 oluştur ve indir</button></form>'''

@app.post('/video')
def video():
    key = os.environ.get('VIDEO_TEST_KEY', '')
    if not key or not secrets.compare_digest(request.form.get('key', ''), key):
        abort(403)
    images = request.files.getlist('images')
    if not 1 <= len(images) <= 10:
        abort(400, '1–10 ürün görseli seçin.')
    sku = request.form.get('sku', '').strip()
    if not sku or len(sku) > 40:
        abort(400)
    with tempfile.TemporaryDirectory() as td:
        folder = Path(td)
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 40)
        for index, upload in enumerate(images):
            try:
                with Image.open(upload.stream) as src:
                    if src.width * src.height > 25_000_000:
                        abort(400)
                    pic = ImageOps.contain(ImageOps.exif_transpose(src).convert('RGB'), (1000, 1450))
            except (OSError, Image.DecompressionBombError):
                abort(400, 'Görsel okunamadı.')
            canvas = Image.new('RGB', (1080, 1920), 'white')
            canvas.paste(pic, ((1080 - pic.width) // 2, 180 + (1450 - pic.height) // 2))
            draw = ImageDraw.Draw(canvas)
            draw.text((70, 80), 'Tanış Bebe', font=font, fill='#222222')
            draw.text((70, 1710), f'Ürün kodu: {sku}', font=font, fill='#222222')
            draw.text((70, 1810), 'www.tanisbebe.com.tr', font=font, fill='#222222')
            canvas.save(folder / f'{index}.jpg', quality=92)
        lines = []
        for index in range(len(images)):
            lines.extend([f"file '{index}.jpg'", 'duration 2'])
        lines.append(f"file '{len(images)-1}.jpg'")
        (folder / 'frames.txt').write_text('\n'.join(lines), encoding='utf-8')
        output = folder / 'video.mp4'
        try:
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                '-f', 'concat', '-safe', '1', '-i', str(folder / 'frames.txt'),
                '-t', str(2 * len(images)), '-r', '30', '-c:v', 'libx264',
                '-threads', '1', '-preset', 'ultrafast', '-crf', '23', '-pix_fmt', 'yuv420p',
                '-an', '-movflags', '+faststart', str(output)], check=True, timeout=180)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            abort(500, 'Video testi başarısız; sunucu kapasitesi kontrol edilmeli.')
        content = BytesIO(output.read_bytes())
    return send_file(content, mimetype='video/mp4', as_attachment=True, download_name='tanis-bebe-test.mp4')
