import re

with open('public/index.html', 'r') as f:
    html = f.read()

new_api_docs = '''        <section class="api-docs">
            <h2>API Documentation</h2>
            <p>Integrate PDF processing into your app with a simple REST API. All endpoints require an <code>X-API-Key</code> header with your Stripe Customer ID.</p>
            <h3>Process PDF</h3>
            <pre><code>curl -X POST https://pdf-processor-api.fly.dev/process-pdf \\
  -H "X-API-Key: YOUR_CUSTOMER_ID" \\
  -F "file=@document.pdf" \\
  --output processed.pdf</code></pre>
            <h3>Extract Text & Metadata</h3>
            <pre><code>curl -X POST https://pdf-processor-api.fly.dev/extract-text \\
  -H "X-API-Key: YOUR_CUSTOMER_ID" \\
  -F "file=@document.pdf"</code></pre>
            <p>Returns JSON with extracted text, page count, PDF metadata, and usage info.</p>
            <h3>Check Usage</h3>
            <pre><code>curl -H "X-API-Key: YOUR_CUSTOMER_ID" \\
  https://pdf-processor-api.fly.dev/customer/usage</code></pre>
            <p>Get your current usage, tier, limits, and next billing cycle.</p>
            <p>Get your API key by signing up for a plan above. Full documentation at <a href="/docs">/docs</a>.</p>
        </section>'''

# Replace api-docs section
pattern = r'<section class="api-docs">.*?</section>'
html = re.sub(pattern, new_api_docs, html, flags=re.DOTALL)

with open('public/index.html', 'w') as f:
    f.write(html)

print('Updated API docs section')