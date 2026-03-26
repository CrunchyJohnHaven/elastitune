import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#05070B',
        'bg-elevated': '#0B0F15',
        panel: 'rgba(10, 14, 20, 0.78)',
        'panel-solid': '#0D1219',
        'accent-blue': '#4DA3FF',
        'accent-cyan': '#7CE7FF',
        success: '#4ADE80',
        warning: '#FBBF24',
        danger: '#FB7185',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
} satisfies Config
