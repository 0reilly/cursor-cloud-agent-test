const fs = require('fs');

// Dark pattern IDs
const darkPatterns = [
  { id: 'dp1', type: 'misleading', name: 'Misleading Free Trial' },
  { id: 'dp2', type: 'sneaking', name: 'Hidden Costs' },
  { id: 'dp3', type: 'urgent', name: 'Countdown Timer' },
  { id: 'dp4', type: 'scarcity', name: 'Low Stock Messages' },
  { id: 'dp5', type: 'social_proof', name: 'Fake Activity Notifications' },
  { id: 'dp6', type: 'obstruction', name: 'Roach Motel' },
  { id: 'dp7', type: 'forced_action', name: 'Forced Continuity' },
  { id: 'dp8', type: 'confirmshaming', name: 'Confirmshaming' },
  { id: 'dp9', type: 'manipulative', name: 'Gamified Manipulation' },
];

const sideEffects = [
  { id: 'se1', name: 'Increased Anxiety' },
  { id: 'se2', name: 'Sleep Disruption' },
  { id: 'se3', name: 'Attention Fragmentation' },
  { id: 'se4', name: 'Data Privacy Risks' },
  { id: 'se5', name: 'Compulsive Spending' },
  { id: 'se6', name: 'Social Isolation' },
  { id: 'se7', name: 'Gambling-like Addiction' },
  { id: 'se8', name: 'Decision Fatigue' },
];

// Categories from type definition
const categories = ['social_media', 'ecommerce', 'productivity', 'gaming', 'streaming', 'dating', 'finance'];

// List of popular apps/services with category, description, icon
const apps = [
  // Social Media (20)
  ['Twitter', 'social_media', 'Social networking service for short messages called tweets.', '🐦'],
  ['Snapchat', 'social_media', 'Multimedia messaging app with disappearing content.', '👻'],
  ['Pinterest', 'social_media', 'Image sharing and social media service for saving and discovering information.', '📌'],
  ['Reddit', 'social_media', 'Social news aggregation, web content rating, and discussion website.', '🤖'],
  ['WhatsApp', 'social_media', 'Cross-platform centralized instant messaging and voice-over-IP service.', '💬'],
  ['Discord', 'social_media', 'Voice, video and text communication service for communities.', '🎮'],
  ['Telegram', 'social_media', 'Cloud-based instant messaging and voice-over-IP service.', '📨'],
  ['Signal', 'social_media', 'Cross-platform encrypted messaging service.', '🔒'],
  ['WeChat', 'social_media', 'Chinese multi-purpose messaging, social media and mobile payment app.', '👥'],
  ['Clubhouse', 'social_media', 'Drop-in audio chat app for conversations.', '🎤'],
  ['Threads', 'social_media', 'Text-based conversation app from Meta.', '🧵'],
  ['Bluesky', 'social_media', 'Decentralized social network from former Twitter team.', '☁️'],
  ['Mastodon', 'social_media', 'Decentralized social networking platform.', '🐘'],
  ['Tumblr', 'social_media', 'Microblogging and social networking website.', '📱'],
  ['VK', 'social_media', 'Russian online social media and social networking service.', '🔷'],
  ['QQ', 'social_media', 'Chinese instant messaging software service.', '💎'],
  ['Sina Weibo', 'social_media', 'Chinese microblogging website.', '🌐'],
  ['Line', 'social_media', 'Japanese messaging app.', '📲'],
  ['Viber', 'social_media', 'Cross-platform voice over IP and instant messaging app.', '📞'],
  ['Skype', 'social_media', 'Telecommunications application for video calls.', '📹'],
  
  // Ecommerce (15)
  ['Alibaba', 'ecommerce', 'Chinese multinational technology company specializing in e-commerce.', '🏮'],
  ['Shopify', 'ecommerce', 'E-commerce platform for online stores and retail point-of-sale systems.', '🛒'],
  ['Walmart', 'ecommerce', 'American multinational retail corporation.', '🛍️'],
  ['Target', 'ecommerce', 'American retail corporation.', '🎯'],
  ['Etsy', 'ecommerce', 'E-commerce website focused on handmade or vintage items and craft supplies.', '✂️'],
  ['Wish', 'ecommerce', 'Mobile e-commerce platform that connects customers with merchants.', '⭐'],
  ['AliExpress', 'ecommerce', 'Chinese online retail service.', '📦'],
  ['Best Buy', 'ecommerce', 'American multinational consumer electronics retailer.', '📺'],
  ['Newegg', 'ecommerce', 'Online retailer of computer hardware and consumer electronics.', '💻'],
  ['Wayfair', 'ecommerce', 'American e-commerce company that sells furniture and home goods.', '🛋️'],
  ['Zalando', 'ecommerce', 'European online fashion platform.', '👠'],
  ['ASOS', 'ecommerce', 'British online fashion and cosmetic retailer.', '👗'],
  ['JD.com', 'ecommerce', 'Chinese online retail company.', '📦'],
  ['Rakuten', 'ecommerce', 'Japanese e-commerce and online retailing company.', '🛍️'],
  ['Farfetch', 'ecommerce', 'Online luxury fashion retail platform.', '👔'],
  
  // Streaming (10)
  ['Hulu', 'streaming', 'Subscription streaming service offering films and television series.', '📺'],
  ['Disney+', 'streaming', 'American subscription video on-demand over-the-top streaming service.', '🏰'],
  ['HBO Max', 'streaming', 'American subscription video on-demand streaming service.', '🎬'],
  ['Apple TV+', 'streaming', 'Subscription streaming service by Apple Inc.', '📱'],
  ['YouTube Premium', 'streaming', 'Subscription service offering ad-free YouTube and original content.', '📹'],
  ['Amazon Prime Video', 'streaming', 'Amazon\'s streaming video service.', '🎥'],
  ['Twitch', 'streaming', 'Video live streaming service for gamers.', '🟣'],
  ['Crunchyroll', 'streaming', 'American subscription video on-demand service for anime.', '🍥'],
  ['Paramount+', 'streaming', 'Subscription streaming service from Paramount Global.', '🌌'],
  ['Peacock', 'streaming', 'American streaming service from NBCUniversal.', '🦚'],
  
  // Gaming (10)
  ['Minecraft', 'gaming', 'Sandbox video game developed by Mojang Studios.', '🧱'],
  ['Roblox', 'gaming', 'Online game platform and game creation system.', '🧩'],
  ['Call of Duty Mobile', 'gaming', 'Free-to-play shooter game in the Call of Duty franchise.', '🔫'],
  ['PUBG Mobile', 'gaming', 'Battle royale mobile game.', '🎯'],
  ['Among Us', 'gaming', 'Online multiplayer social deduction game.', '👨‍🚀'],
  ['Clash of Clans', 'gaming', 'Freemium mobile strategy video game.', '⚔️'],
  ['Clash Royale', 'gaming', 'Freemium real-time strategy video game.', '👑'],
  ['Pokémon GO', 'gaming', 'Augmented reality mobile game.', '🐾'],
  ['Genshin Impact', 'gaming', 'Action role-playing game with gacha mechanics.', '⚔️'],
  ['League of Legends', 'gaming', 'Multiplayer online battle arena video game.', '⚡'],
  
  // Finance (10)
  ['PayPal', 'finance', 'Online payment system supporting online money transfers.', '💳'],
  ['Venmo', 'finance', 'Mobile payment service owned by PayPal.', '💰'],
  ['Cash App', 'finance', 'Mobile payment service developed by Square.', '💵'],
  ['Coinbase', 'finance', 'Cryptocurrency exchange platform.', '₿'],
  ['Acorns', 'finance', 'Financial technology company that invests spare change.', '🌰'],
  ['Chime', 'finance', 'Financial technology company providing banking services.', '🏦'],
  ['Mint', 'finance', 'Personal finance management service.', '🌿'],
  ['YNAB', 'finance', 'Personal budgeting software.', '📊'],
  ['TurboTax', 'finance', 'Tax preparation software.', '📑'],
  ['Credit Karma', 'finance', 'Personal finance company.', '💳'],
  
  // Dating (10)
  ['Bumble', 'dating', 'Dating app where women make the first move.', '🐝'],
  ['Hinge', 'dating', 'Dating app designed to be deleted.', '🔗'],
  ['OkCupid', 'dating', 'American online dating, friendship, and social networking platform.', '💘'],
  ['Match.com', 'dating', 'Online dating website.', '❤️'],
  ['Plenty of Fish', 'dating', 'Online dating service.', '🐟'],
  ['Grindr', 'dating', 'Geosocial networking and online dating app for LGBTQ+ people.', '🌈'],
  ['HER', 'dating', 'Dating app for LGBTQ+ women and queer people.', '👭'],
  ['Coffee Meets Bagel', 'dating', 'Dating platform that sends curated matches daily.', '☕'],
  ['eHarmony', 'dating', 'Online dating website.', '💍'],
  ['Zoosk', 'dating', 'Online dating platform.', '🐾'],
  
  // Productivity (10)
  ['Microsoft Teams', 'productivity', 'Business communication platform.', '💼'],
  ['Zoom', 'productivity', 'Video conferencing platform.', '📹'],
  ['Asana', 'productivity', 'Work management platform.', '📋'],
  ['Trello', 'productivity', 'Web-based list-making application.', '📝'],
  ['Notion', 'productivity', 'Project management and note-taking software.', '📓'],
  ['Evernote', 'productivity', 'Note-taking app.', '📒'],
  ['Google Workspace', 'productivity', 'Cloud-based productivity and collaboration tools.', '🔧'],
  ['Microsoft Office', 'productivity', 'Suite of productivity applications.', '📎'],
  ['ClickUp', 'productivity', 'Productivity platform for task management.', '⬆️'],
  ['Monday.com', 'productivity', 'Work operating system.', '📅'],
];

// Helper to assign dark patterns based on category
function getDarkPatterns(category) {
  const patterns = [];
  switch(category) {
    case 'social_media':
      patterns.push({ id: 'dp5', prevalence: 'common', desc: 'Fake activity notifications create FOMO.' });
      patterns.push({ id: 'dp7', prevalence: 'ubiquitous', desc: 'Infinite scroll encourages addictive usage.' });
      patterns.push({ id: 'dp8', prevalence: 'rare', desc: 'Confirmshaming when declining notifications.' });
      break;
    case 'ecommerce':
      patterns.push({ id: 'dp3', prevalence: 'common', desc: 'Countdown timers create false urgency.' });
      patterns.push({ id: 'dp4', prevalence: 'common', desc: 'Low stock messages pressure purchases.' });
      patterns.push({ id: 'dp2', prevalence: 'common', desc: 'Hidden costs in checkout.' });
      break;
    case 'streaming':
      patterns.push({ id: 'dp1', prevalence: 'common', desc: 'Free trial auto-converts to paid subscription.' });
      patterns.push({ id: 'dp6', prevalence: 'common', desc: 'Complex cancellation process.' });
      patterns.push({ id: 'dp7', prevalence: 'ubiquitous', desc: 'Auto-play next episode forces continued watching.' });
      break;
    case 'gaming':
      patterns.push({ id: 'dp7', prevalence: 'ubiquitous', desc: 'Forces in-app purchases to progress.' });
      patterns.push({ id: 'dp4', prevalence: 'common', desc: 'Limited-time items create artificial scarcity.' });
      patterns.push({ id: 'dp9', prevalence: 'medium', desc: 'Gamified manipulation encourages spending.' });
      break;
    case 'finance':
      patterns.push({ id: 'dp9', prevalence: 'common', desc: 'Gamified interface encourages risky behavior.' });
      patterns.push({ id: 'dp2', prevalence: 'common', desc: 'Hidden fees or commission structures.' });
      patterns.push({ id: 'dp3', prevalence: 'rare', desc: 'Urgent investment opportunities.' });
      break;
    case 'dating':
      patterns.push({ id: 'dp5', prevalence: 'ubiquitous', desc: 'Fake activity notifications about profile views.' });
      patterns.push({ id: 'dp8', prevalence: 'common', desc: 'Shames users for not upgrading to premium.' });
      patterns.push({ id: 'dp7', prevalence: 'common', desc: 'Forces purchase of premium to see likes.' });
      break;
    case 'productivity':
      patterns.push({ id: 'dp7', prevalence: 'common', desc: 'Forces constant availability through notifications.' });
      patterns.push({ id: 'dp4', prevalence: 'common', desc: 'Urgent notification badges create workplace anxiety.' });
      patterns.push({ id: 'dp8', prevalence: 'rare', desc: 'Confirmshaming when declining productivity features.' });
      break;
  }
  return patterns;
}

// Helper to assign side effects based on category
function getSideEffects(category) {
  switch(category) {
    case 'social_media': return ['se1', 'se2', 'se7']; // anxiety, sleep disruption, addiction
    case 'ecommerce': return ['se5', 'se8']; // compulsive spending, decision fatigue
    case 'streaming': return ['se2', 'se7', 'se8']; // sleep disruption, addiction, decision fatigue
    case 'gaming': return ['se7', 'se5', 'se1']; // addiction, compulsive spending, anxiety
    case 'finance': return ['se5', 'se1', 'se7']; // compulsive spending, anxiety, addiction
    case 'dating': return ['se1', 'se6', 'se7']; // anxiety, social isolation, addiction
    case 'productivity': return ['se1', 'se3', 'se8']; // anxiety, attention fragmentation, decision fatigue
    default: return ['se1', 'se8'];
  }
}

// Helper to get transparency score
function getTransparencyScore(category) {
  const scores = {
    'social_media': 20,
    'ecommerce': 45,
    'streaming': 65,
    'gaming': 30,
    'finance': 40,
    'dating': 35,
    'productivity': 75,
  };
  return scores[category] || 50;
}

// Helper to get tags
function getTags(category) {
  const tagMap = {
    'social_media': ['social', 'networking', 'communication'],
    'ecommerce': ['shopping', 'retail', 'marketplace'],
    'streaming': ['video', 'music', 'entertainment'],
    'gaming': ['mobile', 'pc', 'console', 'addictive'],
    'finance': ['money', 'investing', 'banking'],
    'dating': ['relationships', 'social', 'premium'],
    'productivity': ['work', 'tools', 'organization'],
  };
  return tagMap[category] || [];
}

// Generate product entries starting from ID 16 (since we have 15 existing)
let output = '';
for (let i = 0; i < apps.length; i++) {
  const [name, category, description, icon] = apps[i];
  const id = `product${16 + i}`;
  const darkPatterns = getDarkPatterns(category);
  const sideEffectIds = getSideEffects(category);
  const transparencyScore = getTransparencyScore(category);
  const tags = getTags(category);
  
  output += `  {\n`;
  output += `    id: '${id}',\n`;
  output += `    name: '${name}',\n`;
  output += `    category: '${category}',\n`;
  output += `    description: '${description.replace(/'/g, "\\'")}',\n`;
  output += `    darkPatterns: [\n`;
  darkPatterns.forEach(dp => {
    output += `      {\n`;
    output += `        pattern: darkPatterns.find(dp => dp.id === '${dp.id}')!,\n`;
    output += `        prevalence: '${dp.prevalence}',\n`;
    output += `        description: '${dp.desc.replace(/'/g, "\\'")}'\n`;
    output += `      },\n`;
  });
  output += `    ],\n`;
  output += `    sideEffects: [\n`;
  sideEffectIds.forEach(seId => {
    output += `      sideEffects.find(se => se.id === '${seId}')!,\n`;
  });
  output += `    ],\n`;
  output += `    transparencyScore: ${transparencyScore},\n`;
  output += `    icon: '${icon}',\n`;
  output += `    studies: getStudiesForProduct('${name}'),\n`;
  output += `    tags: ${JSON.stringify(tags)}\n`;
  output += `  },\n`;
}

// Write to file
fs.writeFileSync('new_products.txt', output);
console.log(`Generated ${apps.length} new products. Output saved to new_products.txt`);