/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          0: '#0d0b08',
          1: '#141108',
          2: '#1c1810',
          3: '#262018',
          4: '#302820',
        },
        accent: {
          DEFAULT: '#c9963a',
          dim: '#a87a28',
          glow: 'rgba(201,150,58,0.12)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      }
    }
  },
  plugins: [],
}
