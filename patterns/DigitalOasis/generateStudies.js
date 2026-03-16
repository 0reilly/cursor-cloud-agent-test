const fs = require('fs');
const path = require('path');

// Existing product names (including new ones) - we'll extract from mockProducts.ts
const productsPath = path.join(__dirname, 'src/data/mockProducts.ts');
const productsContent = fs.readFileSync(productsPath, 'utf8');
// Extract product names using regex (simple, may be fragile)
const productNames = [];
const regex = /name: '([^']+)'/g;
let match;
while ((match = regex.exec(productsContent)) !== null) {
  productNames.push(match[1]);
}
console.log(`Found ${productNames.length} product names`);

// Categories for studies
const categories = [
  {
    theme: 'Social media addiction',
    products: productNames.filter(name => ['Instagram', 'Facebook', 'Twitter', 'TikTok', 'Snapchat', 'Reddit'].includes(name)).slice(0, 5),
    publications: ['Journal of Digital Psychology', 'Computers in Human Behavior', 'Cyberpsychology', 'Social Media + Society'],
    yearRange: [2020, 2024]
  },
  {
    theme: 'E-commerce dark patterns',
    products: productNames.filter(name => ['Amazon', 'eBay', 'Walmart', 'Target', 'AliExpress', 'Shopify'].includes(name)).slice(0, 5),
    publications: ['Consumer Protection Quarterly', 'Journal of Consumer Research', 'International Journal of Electronic Commerce', 'Marketing Science'],
    yearRange: [2019, 2023]
  },
  {
    theme: 'Gaming monetization',
    products: productNames.filter(name => ['Fortnite', 'Roblox', 'Candy Crush Saga', 'Clash of Clans', 'Pokémon GO', 'League of Legends'].includes(name)).slice(0, 5),
    publications: ['Game Studies International', 'Entertainment Computing', 'International Journal of Gaming', 'Psychology of Popular Media'],
    yearRange: [2020, 2024]
  },
  {
    theme: 'Streaming subscription traps',
    products: productNames.filter(name => ['Netflix', 'Spotify', 'Hulu', 'Disney+', 'YouTube Premium', 'Apple TV+'].includes(name)).slice(0, 5),
    publications: ['Consumer Reports', 'Journal of Broadcasting & Electronic Media', 'Media Economics', 'Television & New Media'],
    yearRange: [2021, 2024]
  },
  {
    theme: 'Privacy and data consent',
    products: productNames.filter(name => ['Facebook', 'Google Services', 'Instagram', 'TikTok', 'Uber', 'LinkedIn'].includes(name)).slice(0, 5),
    publications: ['Privacy & Security Symposium', 'Journal of Cybersecurity', 'International Data Privacy Law', 'IEEE Security & Privacy'],
    yearRange: [2020, 2024]
  },
  {
    theme: 'Financial apps gamification',
    products: productNames.filter(name => ['Robinhood', 'Coinbase', 'PayPal', 'Venmo', 'Acorns', 'Credit Karma'].includes(name)).slice(0, 5),
    publications: ['Journal of Financial Regulation', 'Behavioral Finance Review', 'Financial Innovation', 'Journal of Economic Psychology'],
    yearRange: [2021, 2024]
  },
  {
    theme: 'Productivity tools burnout',
    products: productNames.filter(name => ['Slack', 'Microsoft Teams', 'Zoom', 'Google Workspace', 'Asana', 'Notion'].includes(name)).slice(0, 5),
    publications: ['Journal of Occupational Health', 'Human–Computer Interaction', 'Information Systems Research', 'Organizational Behavior and Human Decision Processes'],
    yearRange: [2020, 2024]
  },
  {
    theme: 'Dating apps mental health',
    products: productNames.filter(name => ['Tinder', 'Bumble', 'Hinge', 'OkCupid', 'Match.com', 'Grindr'].includes(name)).slice(0, 5),
    publications: ['Journal of Social Technology Research', 'Archives of Sexual Behavior', 'Psychology of Women Quarterly', 'Computers in Human Behavior'],
    yearRange: [2021, 2024]
  },
  {
    theme: 'Fitness apps social comparison',
    products: productNames.filter(name => ['Strava', 'Fitbit', 'MyFitnessPal', 'Nike Run Club', 'Apple Fitness+', 'Garmin Connect'].includes(name)).slice(0, 5),
    publications: ['Journal of Health Psychology', 'Sports Medicine', 'Psychology of Sport and Exercise', 'Health Communication'],
    yearRange: [2020, 2024]
  }
];

// Templates for findings (generic)
const findingTemplates = [
  'Users exposed to this pattern showed a {percent}% increase in {metric}',
  '{percent}% of participants reported feeling {emotion} when using the product',
  'The design led to {percent}% higher {outcome} compared to control groups',
  'Researchers observed {percent}% more {behavior} among frequent users',
  'Intervention reduced negative effects by {percent}%',
  'Corporate revenue increased by {percent}% following implementation',
  'User satisfaction dropped by {percent}% after exposure',
  'Cognitive load increased by {percent}% during tasks',
  'Decision-making accuracy decreased by {percent}%'
];

const emotions = ['anxious', 'frustrated', 'overwhelmed', 'addicted', 'guilty', 'pressured'];
const metrics = ['session time', 'spending', 'engagement', 'click-through rate', 'conversion rate'];
const outcomes = ['compulsive use', 'regret', 'stress', 'addiction scores', 'privacy concerns'];
const behaviors = ['checking behavior', 'in-app purchases', 'data sharing', 'notification responses'];

function randomElement(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomYear(range) {
  return Math.floor(Math.random() * (range[1] - range[0] + 1)) + range[0];
}

function generateFindings(count) {
  const findings = [];
  for (let i = 0; i < count; i++) {
    let template = randomElement(findingTemplates);
    template = template.replace('{percent}', Math.floor(Math.random() * 80) + 10);
    template = template.replace('{metric}', randomElement(metrics));
    template = template.replace('{emotion}', randomElement(emotions));
    template = template.replace('{outcome}', randomElement(outcomes));
    template = template.replace('{behavior}', randomElement(behaviors));
    findings.push(template);
  }
  return findings;
}

function generateAuthors() {
  const firstNames = ['Alex', 'Jamie', 'Morgan', 'Taylor', 'Casey', 'Riley', 'Jordan', 'Quinn'];
  const lastNames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis'];
  const titles = ['Dr.', 'Prof.', 'PhD'];
  const count = Math.floor(Math.random() * 3) + 1; // 1-3 authors
  const authors = [];
  for (let i = 0; i < count; i++) {
    const firstName = randomElement(firstNames);
    const lastName = randomElement(lastNames);
    const title = Math.random() > 0.5 ? randomElement(titles) : '';
    authors.push(title ? `${title} ${firstName} ${lastName}` : `${firstName} ${lastName}`);
  }
  return authors;
}

// Generate 19 new studies
const newStudies = [];
for (let i = 12; i <= 30; i++) {
  const category = randomElement(categories);
  const products = category.products.length > 0 ? category.products : [randomElement(productNames)];
  // Ensure at least 2 products, max 5
  const selectedProducts = products.slice(0, Math.floor(Math.random() * 4) + 2);
  const title = `${category.theme}: ${['Recent Findings', 'New Research', 'Comprehensive Analysis', 'Longitudinal Study'][i % 4]}`;
  const summary = `A study investigating ${category.theme.toLowerCase()} in digital platforms, focusing on ${selectedProducts.join(', ')}.`;
  const authors = generateAuthors();
  const publication = randomElement(category.publications);
  const year = randomYear(category.yearRange);
  const findings = generateFindings(4);
  const url = `https://doi.org/10.${1000 + i}/${Math.random().toString(36).substring(2, 8)}`;
  
  newStudies.push(`  {
    id: 'study${i}',
    title: '${title}',
    summary: '${summary.replace(/'/g, "\\\\'")}',
    authors: ${JSON.stringify(authors)},
    publication: '${publication}',
    year: ${year},
    url: '${url}',
    findings: ${JSON.stringify(findings, null, 6).replace(/\\n/g, '\\n')},
    productsAffected: ${JSON.stringify(selectedProducts)}
  }`);
}

const output = newStudies.join(',\\n');
fs.writeFileSync('new_studies.txt', output);
console.log(`Generated ${newStudies.length} new studies. Saved to new_studies.txt`);
