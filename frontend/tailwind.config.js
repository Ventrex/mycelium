/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0e14',
        card: '#141a23',
        border: '#1e2632',
        muted: '#6b7785',
        accent: '#6366f1',
        'accent-2': '#22d3ee',
        teal: '#0d9488',
        mint: '#5eead4',
        ok: '#10b981',
        amber: '#fbbf24',
        warn: '#f59e0b',
        danger: '#ef4444',
        info: '#3b82f6',
      },
    },
  },
  plugins: [],
};
