import re

with open('public/index.html', 'r') as f:
    html = f.read()

new_features = '''        <section class="features">
            <div class="feature">
                <h3>Watermark Removal</h3>
                <p>Remove watermarks from PDFs automatically. Paid tiers get watermark‑free output. Free tier adds a watermark.</p>
            </div>
            <div class="feature">
                <h3>Text Extraction</h3>
                <p>Extract text and metadata from any PDF. Get structured text, page count, author, creation date, and more.</p>
            </div>
            <div class="feature">
                <h3>Batch Processing</h3>
                <p>Process thousands of PDFs in parallel with our high‑throughput API. Built for developers.</p>
            </div>
            <div class="feature">
                <h3>Secure & Private</h3>
                <p>Files are encrypted in transit and at rest. Deleted after 24 hours. GDPR & SOC2 compliant.</p>
            </div>
        </section>'''

# Replace features section (from <section class="features"> to </section>)
pattern = r'<section class="features">.*?</section>'
html = re.sub(pattern, new_features, html, flags=re.DOTALL)

with open('public/index.html', 'w') as f:
    f.write(html)

print('Updated features section')