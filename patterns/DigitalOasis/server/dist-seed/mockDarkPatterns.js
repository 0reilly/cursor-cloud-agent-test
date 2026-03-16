"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.darkPatterns = void 0;
exports.darkPatterns = [
    {
        id: 'dp1',
        type: 'misleading',
        name: 'Misleading Free Trial',
        description: 'Advertises free trial but automatically enrolls user into paid subscription without clear disclosure.',
        severity: 'high',
        example: 'Many streaming services use this pattern during sign-up.',
    },
    {
        id: 'dp2',
        type: 'sneaking',
        name: 'Hidden Costs',
        description: 'Additional costs are hidden until late in checkout process.',
        severity: 'medium',
        example: 'E-commerce sites adding shipping fees at final step.',
    },
    {
        id: 'dp3',
        type: 'urgent',
        name: 'Countdown Timer',
        description: 'False urgency with countdown timers suggesting limited-time offers.',
        severity: 'medium',
        example: 'Travel booking sites showing "only 2 rooms left at this price!".',
    },
    {
        id: 'dp4',
        type: 'scarcity',
        name: 'Low Stock Messages',
        description: 'Displaying false low stock notifications to pressure purchase.',
        severity: 'medium',
        example: 'Amazon showing "only 3 left in stock".',
    },
    {
        id: 'dp5',
        type: 'social_proof',
        name: 'Fake Activity Notifications',
        description: 'Showing fake notifications about others\' activity to create fear of missing out.',
        severity: 'low',
        example: 'Dating apps showing "5 people viewed your profile today".',
    },
    {
        id: 'dp6',
        type: 'obstruction',
        name: 'Roach Motel',
        description: 'Easy to get into but difficult to get out of (cancellation, account deletion).',
        severity: 'high',
        example: 'Gym memberships requiring in-person cancellation.',
    },
    {
        id: 'dp7',
        type: 'forced_action',
        name: 'Forced Continuity',
        description: 'Charging users for a new service without their explicit consent.',
        severity: 'high',
        example: 'Apple subscription renewals without clear reminders.',
    },
    {
        id: 'dp8',
        type: 'confirmshaming',
        name: 'Confirmshaming',
        description: 'Using language that shames users for opting out of something.',
        severity: 'low',
        example: '"No thanks, I don\' want to save money" button.',
    },
    {
        id: 'dp9',
        type: 'manipulative',
        name: 'Gamified Manipulation',
        description: 'Uses game-like elements (points, rewards, streaks) to encourage addictive or risky behavior.',
        severity: 'medium',
        example: 'Trading apps using confetti and celebratory messages after trades.',
    },
];
exports.default = exports.darkPatterns;
