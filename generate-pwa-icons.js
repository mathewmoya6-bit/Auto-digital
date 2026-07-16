// ============================================
// AUTO-D KENYA - PWA Icon Generator
// Run: npm install sharp && node generate-pwa-icons.js
// ============================================

const sharp = require('sharp');
const fs = require('fs');

// Create icons directory
if (!fs.existsSync('./icons')) {
  fs.mkdirSync('./icons');
}

// SVG template with Auto-D Kenya branding
function generateSVG(width, height) {
  const fontSize = width * 0.28;
  const badgeSize = width * 0.12;
  const subFontSize = width * 0.045;
  
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0f172a;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1e293b;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#eab308;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#ca8a04;stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Background -->
  <rect width="${width}" height="${height}" rx="${width * 0.12}" ry="${height * 0.12}" fill="url(#bg)"/>
  
  <!-- Border glow -->
  <rect x="${width * 0.02}" y="${height * 0.02}" width="${width * 0.96}" height="${height * 0.96}" 
        rx="${width * 0.1}" ry="${height * 0.1}" fill="none" 
        stroke="#eab308" stroke-width="${width * 0.008}" stroke-opacity="0.3"/>
  
  <!-- Car Icon -->
  <text x="${width * 0.5}" y="${height * 0.4}" font-family="Arial, sans-serif" font-size="${fontSize}" 
        text-anchor="middle" fill="url(#grad)">
    🚗
  </text>
  
  <!-- Auto-D Text -->
  <text x="${width * 0.5}" y="${height * 0.65}" font-family="'Space Grotesk', Arial, sans-serif" 
        font-size="${width * 0.13}" font-weight="700" text-anchor="middle" fill="#f8fafc" letter-spacing="1">
    Auto-D
  </text>
  
  <!-- Kenya Badge -->
  <rect x="${width * 0.32}" y="${height * 0.75}" width="${width * 0.36}" height="${height * 0.08}" 
        rx="${height * 0.04}" fill="none" stroke="#eab308" stroke-width="${width * 0.006}" stroke-opacity="0.5"/>
  <text x="${width * 0.5}" y="${height * 0.82}" font-family="Arial, sans-serif" 
        font-size="${subFontSize}" font-weight="600" text-anchor="middle" fill="#eab308" letter-spacing="1">
    KENYA
  </text>
  
  <!-- Bottom line -->
  <line x1="${width * 0.15}" y1="${height * 0.9}" x2="${width * 0.85}" y2="${height * 0.9}" 
        stroke="#eab308" stroke-width="${width * 0.004}" stroke-opacity="0.2"/>
</svg>`;
}

// Icon sizes needed
const sizes = [72, 96, 128, 144, 152, 192, 384, 512];

// Generate each icon
sizes.forEach((size) => {
  const svg = generateSVG(size, size);
  
  sharp(Buffer.from(svg))
    .png()
    .toFile(`./icons/icon-${size}.png`)
    .then(() => console.log(`✅ icon-${size}.png created`))
    .catch((err) => console.error(`❌ Error creating icon-${size}.png:`, err));
});

console.log('🎨 Generating PWA icons...');
