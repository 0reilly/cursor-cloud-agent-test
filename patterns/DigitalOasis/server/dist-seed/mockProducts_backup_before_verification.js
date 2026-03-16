"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.products = void 0;
const mockDarkPatterns_1 = __importDefault(require("./mockDarkPatterns"));
const mockSideEffects_1 = __importDefault(require("./mockSideEffects"));
const mockStudies_1 = __importDefault(require("./mockStudies"));
// Helper to find studies by affected products
const getStudiesForProduct = (productName) => {
    return mockStudies_1.default.filter(study => study.productsAffected.some(p => p.toLowerCase().includes(productName.toLowerCase()) ||
        productName.toLowerCase().includes(p.toLowerCase())));
};
exports.products = [
    {
        id: 'product1',
        name: 'Instagram',
        category: 'social_media',
        description: 'Photo and video sharing social networking service owned by Meta Platforms.',
        darkPatterns: [
            {
                pattern: mockDarkPatterns_1.default.find(dp => dp.id === 'dp8'),
                verification: 'EU Complaint: Dark patterns to thwart AI opt-outs (noyb.eu)',
                prevalence: 'common',
                description: 'Uses guilt-inducing language when users decline notifications or features.'
            }
        ],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7')
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://instagram.com&size=128',
        studies: getStudiesForProduct('Instagram'),
        tags: ['social', 'photos', 'meta', 'addictive']
    },
    {
        id: 'product2',
        name: 'Amazon',
        category: 'ecommerce',
        description: 'Multinational technology company focusing on e-commerce, cloud computing, digital streaming, and artificial intelligence.',
        darkPatterns: [
            {
                pattern: mockDarkPatterns_1.default.find(dp => dp.id === 'dp2'),
                verification: 'FTC Complaint: Hidden costs in Amazon Prime case',
                prevalence: 'common',
                description: 'Hidden costs like Prime subscription auto-renewal.'
            },
            {
                pattern: mockDarkPatterns_1.default.find(dp => dp.id === 'dp6'),
                verification: 'FTC Complaint: Making Prime cancellation difficult (Roach Motel)',
                prevalence: 'common',
                description: 'Difficult cancellation process for Prime membership.'
            }
        ],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
            mockSideEffects_1.default.find(se => se.id === 'se4')
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://amazon.com&size=128',
        studies: getStudiesForProduct('Amazon'),
        tags: ['shopping', 'prime', 'marketplace', 'subscription']
    },
    {
        id: 'product3',
        name: 'TikTok',
        category: 'social_media',
        description: 'Video-sharing social networking service owned by ByteDance.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se1')
        ],
        transparencyScore: 15,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://tiktok.com&size=128',
        studies: getStudiesForProduct('TikTok'),
        tags: ['shortform', 'video', 'addictive', 'algorithm']
    },
    {
        id: 'product4',
        name: 'Netflix',
        category: 'streaming',
        description: 'Subscription streaming service offering films and television series.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
            mockSideEffects_1.default.find(se => se.id === 'se7')
        ],
        transparencyScore: 65,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://netflix.com&size=128',
        studies: getStudiesForProduct('Netflix'),
        tags: ['streaming', 'tv', 'movies', 'subscription']
    },
    {
        id: 'product5',
        name: 'Uber',
        category: 'finance',
        description: 'Mobility as a service provider, food delivery, and freight transportation.',
        darkPatterns: [
            {
                pattern: mockDarkPatterns_1.default.find(dp => dp.id === 'dp2'),
                verification: 'Class Action Lawsuit: Hidden fees (drip pricing)',
                prevalence: 'common',
                description: 'Surge pricing not clearly disclosed upfront.'
            }
        ],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se4')
        ],
        transparencyScore: 60,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://uber.com&size=128',
        studies: getStudiesForProduct('Uber'),
        tags: ['ride', 'delivery', 'gig', 'transport']
    },
    {
        id: 'product6',
        name: 'Candy Crush Saga',
        category: 'gaming',
        description: 'Free-to-play tile-matching video game released by King.',
        darkPatterns: [
            {
                pattern: mockDarkPatterns_1.default.find(dp => dp.id === 'dp7'),
                verification: 'Google Play Settlement (FTC): Unauthorized in-app purchases',
                prevalence: 'ubiquitous',
                description: 'Forces in-app purchases to progress.'
            }
        ],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1')
        ],
        transparencyScore: 25,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://king.com&size=128',
        studies: getStudiesForProduct('Candy Crush'),
        tags: ['mobile', 'puzzle', 'freemium', 'addictive']
    },
    {
        id: 'product7',
        name: 'Tinder',
        category: 'dating',
        description: 'Geosocial networking and online dating application.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7')
        ],
        transparencyScore: 35,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://tinder.com&size=128',
        studies: getStudiesForProduct('Tinder'),
        tags: ['dating', 'swipe', 'premium', 'social']
    },
    {
        id: 'product8',
        name: 'LinkedIn',
        category: 'social_media',
        description: 'Business and employment-oriented social media platform.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se8')
        ],
        transparencyScore: 55,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://linkedin.com&size=128',
        studies: getStudiesForProduct('LinkedIn'),
        tags: ['professional', 'networking', 'career', 'business']
    },
    {
        id: 'product9',
        name: 'Spotify',
        category: 'streaming',
        description: 'Audio streaming and media services provider.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se7')
        ],
        transparencyScore: 70,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://spotify.com&size=128',
        studies: getStudiesForProduct('Spotify'),
        tags: ['music', 'audio', 'subscription', 'streaming']
    },
    {
        id: 'product10',
        name: 'Facebook',
        category: 'social_media',
        description: 'Online social media and social networking service owned by Meta Platforms.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se4'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7')
        ],
        transparencyScore: 25,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://facebook.com&size=128',
        studies: getStudiesForProduct('Facebook'),
        tags: ['social', 'meta', 'networking', 'newsfeed']
    },
    {
        id: 'product11',
        name: 'Slack',
        category: 'productivity',
        description: 'Business communication platform with channels, direct messaging, and integrations.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se8')
        ],
        transparencyScore: 75,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://slack.com&size=128',
        studies: getStudiesForProduct('Slack'),
        tags: ['work', 'communication', 'teams', 'notifications']
    },
    {
        id: 'product12',
        name: 'Strava',
        category: 'productivity',
        description: 'Social fitness network that tracks athletic activity via GPS.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se7')
        ],
        transparencyScore: 80,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://strava.com&size=128',
        studies: getStudiesForProduct('Strava'),
        tags: ['fitness', 'tracking', 'social', 'athletics']
    },
    {
        id: 'product13',
        name: 'eBay',
        category: 'ecommerce',
        description: 'Multinational e-commerce corporation facilitating consumer-to-consumer and business-to-consumer sales.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8')
        ],
        transparencyScore: 50,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://ebay.com&size=128',
        studies: getStudiesForProduct('eBay'),
        tags: ['auction', 'marketplace', 'secondhand', 'bidding']
    },
    {
        id: 'product14',
        name: 'Fortnite',
        category: 'gaming',
        description: 'Online video game developed by Epic Games with battle royale gameplay and in-game purchases.',
        darkPatterns: [
            {
                pattern: mockDarkPatterns_1.default.find(dp => dp.id === 'dp7'),
                verification: 'FTC Settlement $245M: Unauthorized charges (Forced Continuity)',
                prevalence: 'ubiquitous',
                description: 'Forces in-game purchases for cosmetic items and battle passes.'
            }
        ],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se2')
        ],
        transparencyScore: 30,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://epicgames.com&size=128',
        studies: getStudiesForProduct('Fortnite'),
        tags: ['battle', 'royale', 'cosmetic', 'addictive']
    },
    {
        id: 'product15',
        name: 'Robinhood',
        category: 'finance',
        description: 'Financial services company known for commission-free trades of stocks, ETFs, and cryptocurrencies.',
        darkPatterns: [
            {
                pattern: mockDarkPatterns_1.default.find(dp => dp.id === 'dp9'),
                verification: 'MA Settlement $7.5M: Gamified manipulation',
                prevalence: 'common',
                description: 'Gamified trading interface encourages risky behavior.'
            }
        ],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se7')
        ],
        transparencyScore: 40,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://robinhood.com&size=128',
        studies: getStudiesForProduct('Robinhood'),
        tags: ['investing', 'trading', 'stocks', 'gamified']
    },
    {
        id: 'product16',
        name: 'Twitter',
        category: 'social_media',
        description: 'Social networking service for short messages called tweets.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://twitter.com&size=128',
        studies: getStudiesForProduct('Twitter'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product17',
        name: 'Snapchat',
        category: 'social_media',
        description: 'Multimedia messaging app with disappearing content.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://snapchat.com&size=128',
        studies: getStudiesForProduct('Snapchat'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product18',
        name: 'Pinterest',
        category: 'social_media',
        description: 'Image sharing and social media service for saving and discovering information.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://pinterest.com&size=128',
        studies: getStudiesForProduct('Pinterest'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product19',
        name: 'Reddit',
        category: 'social_media',
        description: 'Social news aggregation, web content rating, and discussion website.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://reddit.com&size=128',
        studies: getStudiesForProduct('Reddit'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product20',
        name: 'WhatsApp',
        category: 'social_media',
        description: 'Cross-platform centralized instant messaging and voice-over-IP service.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://whatsapp.com&size=128',
        studies: getStudiesForProduct('WhatsApp'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product21',
        name: 'Discord',
        category: 'social_media',
        description: 'Voice, video and text communication service for communities.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://discord.com&size=128',
        studies: getStudiesForProduct('Discord'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product22',
        name: 'Telegram',
        category: 'social_media',
        description: 'Cloud-based instant messaging and voice-over-IP service.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://telegram.org&size=128',
        studies: getStudiesForProduct('Telegram'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product23',
        name: 'Signal',
        category: 'social_media',
        description: 'Cross-platform encrypted messaging service.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://signal.org&size=128',
        studies: getStudiesForProduct('Signal'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product24',
        name: 'WeChat',
        category: 'social_media',
        description: 'Chinese multi-purpose messaging, social media and mobile payment app.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://wechat.com&size=128',
        studies: getStudiesForProduct('WeChat'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product25',
        name: 'Clubhouse',
        category: 'social_media',
        description: 'Drop-in audio chat app for conversations.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://clubhouse.com&size=128',
        studies: getStudiesForProduct('Clubhouse'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product26',
        name: 'Threads',
        category: 'social_media',
        description: 'Text-based conversation app from Meta.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://threads.net&size=128',
        studies: getStudiesForProduct('Threads'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product27',
        name: 'Bluesky',
        category: 'social_media',
        description: 'Decentralized social network from former Twitter team.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://bsky.app&size=128',
        studies: getStudiesForProduct('Bluesky'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product28',
        name: 'Mastodon',
        category: 'social_media',
        description: 'Decentralized social networking platform.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://mastodon.social&size=128',
        studies: getStudiesForProduct('Mastodon'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product29',
        name: 'Tumblr',
        category: 'social_media',
        description: 'Microblogging and social networking website.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://tumblr.com&size=128',
        studies: getStudiesForProduct('Tumblr'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product30',
        name: 'VK',
        category: 'social_media',
        description: 'Russian online social media and social networking service.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://vk.com&size=128',
        studies: getStudiesForProduct('VK'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product31',
        name: 'QQ',
        category: 'social_media',
        description: 'Chinese instant messaging software service.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://qq.com&size=128',
        studies: getStudiesForProduct('QQ'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product32',
        name: 'Sina Weibo',
        category: 'social_media',
        description: 'Chinese microblogging website.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://weibo.com&size=128',
        studies: getStudiesForProduct('Sina Weibo'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product33',
        name: 'Line',
        category: 'social_media',
        description: 'Japanese messaging app.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://line.me&size=128',
        studies: getStudiesForProduct('Line'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product34',
        name: 'Viber',
        category: 'social_media',
        description: 'Cross-platform voice over IP and instant messaging app.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://viber.com&size=128',
        studies: getStudiesForProduct('Viber'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product35',
        name: 'Skype',
        category: 'social_media',
        description: 'Telecommunications application for video calls.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 20,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://skype.com&size=128',
        studies: getStudiesForProduct('Skype'),
        tags: ["social", "networking", "communication"]
    },
    {
        id: 'product36',
        name: 'Alibaba',
        category: 'ecommerce',
        description: 'Chinese multinational technology company specializing in e-commerce.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://alibaba.com&size=128',
        studies: getStudiesForProduct('Alibaba'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product37',
        name: 'Shopify',
        category: 'ecommerce',
        description: 'E-commerce platform for online stores and retail point-of-sale systems.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://shopify.com&size=128',
        studies: getStudiesForProduct('Shopify'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product38',
        name: 'Walmart',
        category: 'ecommerce',
        description: 'American multinational retail corporation.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://walmart.com&size=128',
        studies: getStudiesForProduct('Walmart'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product39',
        name: 'Target',
        category: 'ecommerce',
        description: 'American retail corporation.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://target.com&size=128',
        studies: getStudiesForProduct('Target'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product40',
        name: 'Etsy',
        category: 'ecommerce',
        description: 'E-commerce website focused on handmade or vintage items and craft supplies.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://etsy.com&size=128',
        studies: getStudiesForProduct('Etsy'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product41',
        name: 'Wish',
        category: 'ecommerce',
        description: 'Mobile e-commerce platform that connects customers with merchants.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://wish.com&size=128',
        studies: getStudiesForProduct('Wish'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product42',
        name: 'AliExpress',
        category: 'ecommerce',
        description: 'Chinese online retail service.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://aliexpress.com&size=128',
        studies: getStudiesForProduct('AliExpress'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product43',
        name: 'Best Buy',
        category: 'ecommerce',
        description: 'American multinational consumer electronics retailer.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://bestbuy.com&size=128',
        studies: getStudiesForProduct('Best Buy'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product44',
        name: 'Newegg',
        category: 'ecommerce',
        description: 'Online retailer of computer hardware and consumer electronics.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://newegg.com&size=128',
        studies: getStudiesForProduct('Newegg'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product45',
        name: 'Wayfair',
        category: 'ecommerce',
        description: 'American e-commerce company that sells furniture and home goods.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://wayfair.com&size=128',
        studies: getStudiesForProduct('Wayfair'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product46',
        name: 'Zalando',
        category: 'ecommerce',
        description: 'European online fashion platform.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://zalando.com&size=128',
        studies: getStudiesForProduct('Zalando'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product47',
        name: 'ASOS',
        category: 'ecommerce',
        description: 'British online fashion and cosmetic retailer.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://asos.com&size=128',
        studies: getStudiesForProduct('ASOS'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product48',
        name: 'JD.com',
        category: 'ecommerce',
        description: 'Chinese online retail company.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://jd.com&size=128',
        studies: getStudiesForProduct('JD.com'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product49',
        name: 'Rakuten',
        category: 'ecommerce',
        description: 'Japanese e-commerce and online retailing company.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://rakuten.com&size=128',
        studies: getStudiesForProduct('Rakuten'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product50',
        name: 'Farfetch',
        category: 'ecommerce',
        description: 'Online luxury fashion retail platform.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 45,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://farfetch.com&size=128',
        studies: getStudiesForProduct('Farfetch'),
        tags: ["shopping", "retail", "marketplace"]
    },
    {
        id: 'product51',
        name: 'Hulu',
        category: 'streaming',
        description: 'Subscription streaming service offering films and television series.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 65,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://hulu.com&size=128',
        studies: getStudiesForProduct('Hulu'),
        tags: ["video", "music", "entertainment"]
    },
    {
        id: 'product52',
        name: 'Disney+',
        category: 'streaming',
        description: 'American subscription video on-demand over-the-top streaming service.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 65,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://disneyplus.com&size=128',
        studies: getStudiesForProduct('Disney+'),
        tags: ["video", "music", "entertainment"]
    },
    {
        id: 'product53',
        name: 'HBO Max',
        category: 'streaming',
        description: 'American subscription video on-demand streaming service.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 65,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://hbomax.com&size=128',
        studies: getStudiesForProduct('HBO Max'),
        tags: ["video", "music", "entertainment"]
    },
    {
        id: 'product54',
        name: 'Apple TV+',
        category: 'streaming',
        description: 'Subscription streaming service by Apple Inc.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 65,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://apple.com&size=128',
        studies: getStudiesForProduct('Apple TV+'),
        tags: ["video", "music", "entertainment"]
    },
    {
        id: 'product55',
        name: 'YouTube Premium',
        category: 'streaming',
        description: 'Subscription service offering ad-free YouTube and original content.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 65,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://youtube.com&size=128',
        studies: getStudiesForProduct('YouTube Premium'),
        tags: ["video", "music", "entertainment"]
    },
    {
        id: 'product56',
        name: 'Amazon Prime Video',
        category: 'streaming',
        description: 'Amazon\'s streaming video service.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 65,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://amazon.com&size=128',
        studies: getStudiesForProduct('Amazon Prime Video'),
        tags: ["video", "music", "entertainment"]
    },
    {
        id: 'product57',
        name: 'Twitch',
        category: 'streaming',
        description: 'Video live streaming service for gamers.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 65,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://twitch.tv&size=128',
        studies: getStudiesForProduct('Twitch'),
        tags: ["video", "music", "entertainment"]
    },
    {
        id: 'product58',
        name: 'Crunchyroll',
        category: 'streaming',
        description: 'American subscription video on-demand service for anime.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 65,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://crunchyroll.com&size=128',
        studies: getStudiesForProduct('Crunchyroll'),
        tags: ["video", "music", "entertainment"]
    },
    {
        id: 'product59',
        name: 'Paramount+',
        category: 'streaming',
        description: 'Subscription streaming service from Paramount Global.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 65,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://paramountplus.com&size=128',
        studies: getStudiesForProduct('Paramount+'),
        tags: ["video", "music", "entertainment"]
    },
    {
        id: 'product60',
        name: 'Peacock',
        category: 'streaming',
        description: 'American streaming service from NBCUniversal.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se2'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 65,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://peacocktv.com&size=128',
        studies: getStudiesForProduct('Peacock'),
        tags: ["video", "music", "entertainment"]
    },
    {
        id: 'product61',
        name: 'Minecraft',
        category: 'gaming',
        description: 'Sandbox video game developed by Mojang Studios.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
        ],
        transparencyScore: 30,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://minecraft.net&size=128',
        studies: getStudiesForProduct('Minecraft'),
        tags: ["mobile", "pc", "console", "addictive"]
    },
    {
        id: 'product62',
        name: 'Roblox',
        category: 'gaming',
        description: 'Online game platform and game creation system.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
        ],
        transparencyScore: 30,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://roblox.com&size=128',
        studies: getStudiesForProduct('Roblox'),
        tags: ["mobile", "pc", "console", "addictive"]
    },
    {
        id: 'product63',
        name: 'Call of Duty Mobile',
        category: 'gaming',
        description: 'Free-to-play shooter game in the Call of Duty franchise.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
        ],
        transparencyScore: 30,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://callofduty.com&size=128',
        studies: getStudiesForProduct('Call of Duty Mobile'),
        tags: ["mobile", "pc", "console", "addictive"]
    },
    {
        id: 'product64',
        name: 'PUBG Mobile',
        category: 'gaming',
        description: 'Battle royale mobile game.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
        ],
        transparencyScore: 30,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://pubgmobile.com&size=128',
        studies: getStudiesForProduct('PUBG Mobile'),
        tags: ["mobile", "pc", "console", "addictive"]
    },
    {
        id: 'product65',
        name: 'Among Us',
        category: 'gaming',
        description: 'Online multiplayer social deduction game.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
        ],
        transparencyScore: 30,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://innersloth.com&size=128',
        studies: getStudiesForProduct('Among Us'),
        tags: ["mobile", "pc", "console", "addictive"]
    },
    {
        id: 'product66',
        name: 'Clash of Clans',
        category: 'gaming',
        description: 'Freemium mobile strategy video game.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
        ],
        transparencyScore: 30,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://supercell.com&size=128',
        studies: getStudiesForProduct('Clash of Clans'),
        tags: ["mobile", "pc", "console", "addictive"]
    },
    {
        id: 'product67',
        name: 'Clash Royale',
        category: 'gaming',
        description: 'Freemium real-time strategy video game.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
        ],
        transparencyScore: 30,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://supercell.com&size=128',
        studies: getStudiesForProduct('Clash Royale'),
        tags: ["mobile", "pc", "console", "addictive"]
    },
    {
        id: 'product68',
        name: 'Pokémon GO',
        category: 'gaming',
        description: 'Augmented reality mobile game.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
        ],
        transparencyScore: 30,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://nianticlabs.com&size=128',
        studies: getStudiesForProduct('Pokémon GO'),
        tags: ["mobile", "pc", "console", "addictive"]
    },
    {
        id: 'product69',
        name: 'Genshin Impact',
        category: 'gaming',
        description: 'Action role-playing game with gacha mechanics.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
        ],
        transparencyScore: 30,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://mihoyo.com&size=128',
        studies: getStudiesForProduct('Genshin Impact'),
        tags: ["mobile", "pc", "console", "addictive"]
    },
    {
        id: 'product70',
        name: 'League of Legends',
        category: 'gaming',
        description: 'Multiplayer online battle arena video game.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se7'),
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
        ],
        transparencyScore: 30,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://leagueoflegends.com&size=128',
        studies: getStudiesForProduct('League of Legends'),
        tags: ["mobile", "pc", "console", "addictive"]
    },
    {
        id: 'product71',
        name: 'PayPal',
        category: 'finance',
        description: 'Online payment system supporting online money transfers.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 40,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://paypal.com&size=128',
        studies: getStudiesForProduct('PayPal'),
        tags: ["money", "investing", "banking"]
    },
    {
        id: 'product72',
        name: 'Venmo',
        category: 'finance',
        description: 'Mobile payment service owned by PayPal.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 40,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://venmo.com&size=128',
        studies: getStudiesForProduct('Venmo'),
        tags: ["money", "investing", "banking"]
    },
    {
        id: 'product73',
        name: 'Cash App',
        category: 'finance',
        description: 'Mobile payment service developed by Square.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 40,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://cash.app&size=128',
        studies: getStudiesForProduct('Cash App'),
        tags: ["money", "investing", "banking"]
    },
    {
        id: 'product74',
        name: 'Coinbase',
        category: 'finance',
        description: 'Cryptocurrency exchange platform.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 40,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://coinbase.com&size=128',
        studies: getStudiesForProduct('Coinbase'),
        tags: ["money", "investing", "banking"]
    },
    {
        id: 'product75',
        name: 'Acorns',
        category: 'finance',
        description: 'Financial technology company that invests spare change.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 40,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://acorns.com&size=128',
        studies: getStudiesForProduct('Acorns'),
        tags: ["money", "investing", "banking"]
    },
    {
        id: 'product76',
        name: 'Chime',
        category: 'finance',
        description: 'Financial technology company providing banking services.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 40,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://chime.com&size=128',
        studies: getStudiesForProduct('Chime'),
        tags: ["money", "investing", "banking"]
    },
    {
        id: 'product77',
        name: 'Mint',
        category: 'finance',
        description: 'Personal finance management service.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 40,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://mint.intuit.com&size=128',
        studies: getStudiesForProduct('Mint'),
        tags: ["money", "investing", "banking"]
    },
    {
        id: 'product78',
        name: 'YNAB',
        category: 'finance',
        description: 'Personal budgeting software.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 40,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://youneedabudget.com&size=128',
        studies: getStudiesForProduct('YNAB'),
        tags: ["money", "investing", "banking"]
    },
    {
        id: 'product79',
        name: 'TurboTax',
        category: 'finance',
        description: 'Tax preparation software.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 40,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://turbotax.intuit.com&size=128',
        studies: getStudiesForProduct('TurboTax'),
        tags: ["money", "investing", "banking"]
    },
    {
        id: 'product80',
        name: 'Credit Karma',
        category: 'finance',
        description: 'Personal finance company.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se5'),
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 40,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://creditkarma.com&size=128',
        studies: getStudiesForProduct('Credit Karma'),
        tags: ["money", "investing", "banking"]
    },
    {
        id: 'product81',
        name: 'Bumble',
        category: 'dating',
        description: 'Dating app where women make the first move.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 35,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://bumble.com&size=128',
        studies: getStudiesForProduct('Bumble'),
        tags: ["relationships", "social", "premium"]
    },
    {
        id: 'product82',
        name: 'Hinge',
        category: 'dating',
        description: 'Dating app designed to be deleted.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 35,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://hinge.co&size=128',
        studies: getStudiesForProduct('Hinge'),
        tags: ["relationships", "social", "premium"]
    },
    {
        id: 'product83',
        name: 'OkCupid',
        category: 'dating',
        description: 'American online dating, friendship, and social networking platform.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 35,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://okcupid.com&size=128',
        studies: getStudiesForProduct('OkCupid'),
        tags: ["relationships", "social", "premium"]
    },
    {
        id: 'product84',
        name: 'Match.com',
        category: 'dating',
        description: 'Online dating website.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 35,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://match.com&size=128',
        studies: getStudiesForProduct('Match.com'),
        tags: ["relationships", "social", "premium"]
    },
    {
        id: 'product85',
        name: 'Plenty of Fish',
        category: 'dating',
        description: 'Online dating service.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 35,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://pof.com&size=128',
        studies: getStudiesForProduct('Plenty of Fish'),
        tags: ["relationships", "social", "premium"]
    },
    {
        id: 'product86',
        name: 'Grindr',
        category: 'dating',
        description: 'Geosocial networking and online dating app for LGBTQ+ people.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 35,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://grindr.com&size=128',
        studies: getStudiesForProduct('Grindr'),
        tags: ["relationships", "social", "premium"]
    },
    {
        id: 'product87',
        name: 'HER',
        category: 'dating',
        description: 'Dating app for LGBTQ+ women and queer people.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 35,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://weareher.com&size=128',
        studies: getStudiesForProduct('HER'),
        tags: ["relationships", "social", "premium"]
    },
    {
        id: 'product88',
        name: 'Coffee Meets Bagel',
        category: 'dating',
        description: 'Dating platform that sends curated matches daily.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 35,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://coffeemeetsbagel.com&size=128',
        studies: getStudiesForProduct('Coffee Meets Bagel'),
        tags: ["relationships", "social", "premium"]
    },
    {
        id: 'product89',
        name: 'eHarmony',
        category: 'dating',
        description: 'Online dating website.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 35,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://eharmony.com&size=128',
        studies: getStudiesForProduct('eHarmony'),
        tags: ["relationships", "social", "premium"]
    },
    {
        id: 'product90',
        name: 'Zoosk',
        category: 'dating',
        description: 'Online dating platform.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se6'),
            mockSideEffects_1.default.find(se => se.id === 'se7'),
        ],
        transparencyScore: 35,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://zoosk.com&size=128',
        studies: getStudiesForProduct('Zoosk'),
        tags: ["relationships", "social", "premium"]
    },
    {
        id: 'product91',
        name: 'Microsoft Teams',
        category: 'productivity',
        description: 'Business communication platform.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 75,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://microsoft.com&size=128',
        studies: getStudiesForProduct('Microsoft Teams'),
        tags: ["work", "tools", "organization"]
    },
    {
        id: 'product92',
        name: 'Zoom',
        category: 'productivity',
        description: 'Video conferencing platform.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 75,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://zoom.us&size=128',
        studies: getStudiesForProduct('Zoom'),
        tags: ["work", "tools", "organization"]
    },
    {
        id: 'product93',
        name: 'Asana',
        category: 'productivity',
        description: 'Work management platform.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 75,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://asana.com&size=128',
        studies: getStudiesForProduct('Asana'),
        tags: ["work", "tools", "organization"]
    },
    {
        id: 'product94',
        name: 'Trello',
        category: 'productivity',
        description: 'Web-based list-making application.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 75,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://trello.com&size=128',
        studies: getStudiesForProduct('Trello'),
        tags: ["work", "tools", "organization"]
    },
    {
        id: 'product95',
        name: 'Notion',
        category: 'productivity',
        description: 'Project management and note-taking software.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 75,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://notion.so&size=128',
        studies: getStudiesForProduct('Notion'),
        tags: ["work", "tools", "organization"]
    },
    {
        id: 'product96',
        name: 'Evernote',
        category: 'productivity',
        description: 'Note-taking app.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 75,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://evernote.com&size=128',
        studies: getStudiesForProduct('Evernote'),
        tags: ["work", "tools", "organization"]
    },
    {
        id: 'product97',
        name: 'Google Workspace',
        category: 'productivity',
        description: 'Cloud-based productivity and collaboration tools.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 75,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://google.com&size=128',
        studies: getStudiesForProduct('Google Workspace'),
        tags: ["work", "tools", "organization"]
    },
    {
        id: 'product98',
        name: 'Microsoft Office',
        category: 'productivity',
        description: 'Suite of productivity applications.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 75,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://microsoft.com&size=128',
        studies: getStudiesForProduct('Microsoft Office'),
        tags: ["work", "tools", "organization"]
    },
    {
        id: 'product99',
        name: 'ClickUp',
        category: 'productivity',
        description: 'Productivity platform for task management.',
        darkPatterns: [],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 75,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://clickup.com&size=128',
        studies: getStudiesForProduct('ClickUp'),
        tags: ["work", "tools", "organization"]
    },
    {
        id: 'product100',
        name: 'Monday.com',
        category: 'productivity',
        description: 'Work operating system.',
        darkPatterns: [
            {
                pattern: mockDarkPatterns_1.default.find(dp => dp.id === 'dp7'),
                prevalence: 'common',
                description: 'Forces constant availability through notifications.'
            },
            {
                pattern: mockDarkPatterns_1.default.find(dp => dp.id === 'dp4'),
                prevalence: 'common',
                description: 'Urgent notification badges create workplace anxiety.'
            },
            {
                pattern: mockDarkPatterns_1.default.find(dp => dp.id === 'dp8'),
                prevalence: 'rare',
                description: 'Confirmshaming when declining productivity features.'
            },
        ],
        sideEffects: [
            mockSideEffects_1.default.find(se => se.id === 'se1'),
            mockSideEffects_1.default.find(se => se.id === 'se3'),
            mockSideEffects_1.default.find(se => se.id === 'se8'),
        ],
        transparencyScore: 75,
        icon: 'https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://monday.com&size=128',
        studies: getStudiesForProduct('Monday.com'),
        tags: ["work", "tools", "organization"]
    }
];
exports.default = exports.products;
