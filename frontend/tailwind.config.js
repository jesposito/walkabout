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
        // Semantic tokens via CSS custom properties (light/dark aware)
        deck: {
          bg: 'rgb(var(--color-deck-bg) / <alpha-value>)',
          surface: 'rgb(var(--color-deck-surface) / <alpha-value>)',
          'surface-hover': 'rgb(var(--color-deck-surface-hover) / <alpha-value>)',
          border: 'rgb(var(--color-deck-border) / <alpha-value>)',
          'text-primary': 'rgb(var(--color-deck-text-primary) / <alpha-value>)',
          'text-secondary': 'rgb(var(--color-deck-text-secondary) / <alpha-value>)',
          'text-muted': 'rgb(var(--color-deck-text-muted) / <alpha-value>)',
        },
        deal: {
          hot: 'rgb(var(--color-deal-hot) / <alpha-value>)',
          good: 'rgb(var(--color-deal-good) / <alpha-value>)',
          decent: 'rgb(var(--color-deal-decent) / <alpha-value>)',
          normal: 'rgb(var(--color-deal-normal) / <alpha-value>)',
          above: 'rgb(var(--color-deal-above) / <alpha-value>)',
        },
        accent: {
          primary: 'rgb(var(--color-accent-primary) / <alpha-value>)',
          'primary-dim': 'rgb(var(--color-accent-primary-dim) / <alpha-value>)',
          secondary: 'rgb(var(--color-accent-secondary) / <alpha-value>)',
        },
        danger: {
          DEFAULT: 'rgb(var(--color-danger) / <alpha-value>)',
          dim: 'rgb(var(--color-danger-dim) / <alpha-value>)',
        },
        ring: {
          focus: 'rgb(var(--ring-color) / <alpha-value>)',
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
        'touch': '44px',
      },
      borderRadius: {
        'card': '12px',
      },
    },
  },
  plugins: [],
}
