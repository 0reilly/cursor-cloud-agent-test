const fs = require('fs');
const pdfParse = require('pdf-parse');

(async () => {
  try {
    const pdfBuffer = fs.readFileSync('sample.pdf');
    console.log('PDF buffer length:', pdfBuffer.length);
    const data = await pdfParse(pdfBuffer);
    console.log('Success!');
    console.log('Pages:', data.numpages);
    console.log('Text length:', data.text.length);
    console.log('First 200 chars:', data.text.substring(0, 200));
  } catch (err) {
    console.error('Error:', err.message);
    console.error('Stack:', err.stack);
  }
})();