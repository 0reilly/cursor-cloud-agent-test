# Apple Notes Clone

A modern, beautiful Apple Notes clone built with Next.js 14, TypeScript, and Tailwind CSS.

## Features

- ✨ Modern, clean UI inspired by Apple Notes
- 📝 Create, edit, and delete notes
- 🔍 Search functionality
- 💾 Local storage persistence
- 🌙 Dark mode support
- 📱 Responsive design
- ⚡ Fast and lightweight

## Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Modern styling
- **Lucide React** - Beautiful icons

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Deployment to Vercel

This project is configured for Vercel deployment.

### Option 1: Deploy via Vercel CLI

1. Install Vercel CLI (if not already installed):
```bash
npm i -g vercel
```

2. Login to Vercel:
```bash
vercel login
```

3. Link to your project (if you have a project ID):
```bash
vercel link --project=KV8lOvWOpibxt6XdcSb5EhC4
```

4. Deploy to production:
```bash
vercel --prod
```

### Option 2: Deploy via Vercel Dashboard

1. Push your code to GitHub/GitLab/Bitbucket
2. Import the repository in [Vercel Dashboard](https://vercel.com/dashboard)
3. Vercel will automatically detect Next.js and configure the build settings
4. Click "Deploy"

## Project Structure

```
├── app/
│   ├── globals.css      # Global styles and Tailwind imports
│   ├── layout.tsx       # Root layout component
│   └── page.tsx         # Main notes application page
├── components/
│   ├── NoteEditor.tsx   # Note editing component
│   └── NoteList.tsx     # Notes list sidebar component
└── public/              # Static assets
```

## Features in Detail

### Notes Management
- Create new notes with the "+" button
- Click on any note in the sidebar to edit
- Notes are automatically saved to localStorage
- Delete notes with the trash icon

### Search
- Use the search bar to filter notes by title or content
- Real-time search results

### UI/UX
- Clean, minimal interface
- Smooth transitions and hover effects
- Responsive layout that works on all screen sizes
- Dark mode support (follows system preference)

## License

MIT
