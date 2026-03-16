const Jimp = require('jimp');
const fs = require('fs');
const path = require('path');

const SIZE = 1024;
const OUTPUT_PATH = path.join(__dirname, '../assets/icon.png');
const ADAPTIVE_ICON_PATH = path.join(__dirname, '../assets/adaptive-icon.png');
const SPLASH_ICON_PATH = path.join(__dirname, '../assets/splash-icon.png');

async function generateIcon() {
  // Create a new image with a gradient background
  const image = new Jimp(SIZE, SIZE, 0x0066CCFF); // solid blue with alpha
  // Draw a simple magnifying glass shape
  const centerX = SIZE / 2;
  const centerY = SIZE / 2;
  const radius = SIZE * 0.3;
  const handleLength = SIZE * 0.2;
  const handleWidth = SIZE * 0.05;

  // Draw circle (magnifying glass lens)
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      const dist = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2);
      if (dist <= radius && dist >= radius - SIZE * 0.05) {
        image.setPixelColor(0xFFFFFFFF, x, y); // white border
      }
    }
  }

  // Draw handle (line from circle to bottom right)
  const handleStartX = centerX + radius * Math.cos(Math.PI / 4);
  const handleStartY = centerY + radius * Math.sin(Math.PI / 4);
  const handleEndX = handleStartX + handleLength;
  const handleEndY = handleStartY + handleLength;

  for (let t = 0; t <= 1; t += 0.001) {
    const x = Math.round(handleStartX + t * (handleEndX - handleStartX));
    const y = Math.round(handleStartY + t * (handleEndY - handleStartY));
    for (let dx = -handleWidth; dx <= handleWidth; dx++) {
      for (let dy = -handleWidth; dy <= handleWidth; dy++) {
        if (x + dx >= 0 && x + dx < SIZE && y + dy >= 0 && y + dy < SIZE) {
          image.setPixelColor(0xFFFFFFFF, x + dx, y + dy);
        }
      }
    }
  }

  // Add text "DO" in the center (simplified: draw rectangles)
  const textWidth = SIZE * 0.15;
  const textHeight = SIZE * 0.4;
  // Letter D
  for (let y = centerY - textHeight/2; y < centerY + textHeight/2; y++) {
    for (let x = centerX - textWidth - textWidth/2; x < centerX - textWidth/2; x++) {
      if (x >= 0 && x < SIZE && y >= 0 && y < SIZE) {
        image.setPixelColor(0x000000FF, x, y);
      }
    }
  }
  // Letter O (circle)
  const oRadius = textHeight / 2;
  for (let y = centerY - oRadius; y < centerY + oRadius; y++) {
    for (let x = centerX + textWidth/2; x < centerX + textWidth/2 + oRadius*2; x++) {
      const dist = Math.sqrt((x - (centerX + textWidth/2 + oRadius)) ** 2 + (y - centerY) ** 2);
      if (dist <= oRadius && dist >= oRadius - textWidth/2) {
        image.setPixelColor(0x000000FF, x, y);
      }
    }
  }

  await image.writeAsync(OUTPUT_PATH);
  console.log(`Generated icon at ${OUTPUT_PATH}`);

  // Create adaptive-icon (same as icon but with transparency)
  await image.writeAsync(ADAPTIVE_ICON_PATH);
  console.log(`Generated adaptive-icon at ${ADAPTIVE_ICON_PATH}`);

  // Create splash-icon (same as icon but maybe larger? Expo uses same splash-icon)
  await image.writeAsync(SPLASH_ICON_PATH);
  console.log(`Generated splash-icon at ${SPLASH_ICON_PATH}`);
}

generateIcon().catch(err => {
  console.error('Error generating icon:', err);
  process.exit(1);
});