const { PDFDocument, rgb, StandardFonts } = require('pdf-lib');
const pdfParse = require('pdf-parse');


/**
 * Process a PDF buffer: add watermark if watermarked flag is true
 * @param {Uint8Array} pdfBuffer - Input PDF
 * @param {boolean} watermarked - Whether to add watermark
 * @returns {Promise<Uint8Array>} Processed PDF buffer
 */
async function processPdf(pdfBuffer, watermarked = false) {
  // Load the PDF
  const pdfDoc = await PDFDocument.load(pdfBuffer);
  const pages = pdfDoc.getPages();
  
  if (watermarked) {
    // Add watermark text to each page
    const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const fontSize = 48;
    const watermarkText = 'Processed by PDF Processor';
    
    pages.forEach((page, index) => {
      const { width, height } = page.getSize();
      // Calculate position for diagonal watermark
      const textWidth = font.widthOfTextAtSize(watermarkText, fontSize);
      const textHeight = fontSize;
      const x = (width - textWidth) / 2;
      const y = (height - textHeight) / 2;
      
      page.drawText(watermarkText, {
        x,
        y,
        size: fontSize,
        font,
        color: rgb(0.8, 0.8, 0.8),
        opacity: 0.4,
        rotate: { angle: -30, type: 'degrees' },
      });
      
      // Also add page number watermark
      page.drawText(`Page ${index + 1}`, {
        x: width - 80,
        y: 30,
        size: 10,
        font,
        color: rgb(0.6, 0.6, 0.6),
        opacity: 0.3,
      });
    });
  }
  
  // Save the modified PDF
  const processedPdf = await pdfDoc.save();
  return processedPdf;
}

async function extractTextFromPdf(pdfBuffer) {
  try {
    // Parse PDF using pdf-parse
    const data = await pdfParse(pdfBuffer);
    return { 
      text: data.text, 
      numpages: data.numpages,
      info: data.info || {},
      metadata: data.metadata || {}
    };
  } catch (err) {
    console.error('PDF text extraction error:', err);
    // Fallback to pdf-lib for page count only
    try {
      const pdfDoc = await PDFDocument.load(pdfBuffer);
      const numpages = pdfDoc.getPages().length;
      return { 
        text: `Text extraction failed: ${err.message}. PDF has ${numpages} page(s).`,
        numpages,
        info: {},
        metadata: {}
      };
    } catch (fallbackErr) {
      console.error('PDF fallback error:', fallbackErr);
      throw new Error('Failed to extract text from PDF');
    }
  }
}

module.exports = { processPdf, extractTextFromPdf };