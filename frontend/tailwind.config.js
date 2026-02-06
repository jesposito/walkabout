/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Calm Flight Deck palette
        deck: {
          bg: '#1a1a1a',
          surface: '#252525',
          'surface-hover': '#2d2d2d',
          border: '#333333',
          'text-primary': '#e5e5e5',
          'text-secondary': '#999999',
          'text-muted': '#666666',
        },
        deal: {
          hot: '#00ff88',
          good: '#22d3ee',
          decent: '#a78bfa',
          normal: '#999999',
          above: '#ef4444',
        },
        accent: {
          primary: '#00ff88',
          'primary-dim': '#00cc6e',
          secondary: '#22d3ee',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'price-lg': ['2rem', { lineHeight: '1', fontWeight: '600' }],
        'price-md': ['1.5rem', { lineHeight: '1', fontWeight: '600' }],
        'price-sm': ['1.125rem', { lineHeight: '1', fontWeight: '600' }],
        'code-sm': ['0.8125rem', { lineHeight: '1.5' }],
      },
      spacing: {
        'touch': '44px', // minimum touch target
      },
      borderRadius: {
        'card': '12px',
      },
    },
  },
  plugins: [],
}
