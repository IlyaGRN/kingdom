/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        parchment: {
          50: '#faf8f5',
          100: '#f5f0e8',
          200: '#e8dcc8',
          300: '#d9c5a5',
          400: '#c9ab7f',
          500: '#b8925f',
          600: '#a37a4a',
          700: '#86613d',
          800: '#6d4e35',
          900: '#5a412f',
        },
        medieval: {
          gold: '#c9a227',
          crimson: '#8b0000',
          navy: '#1a1a4e',
          forest: '#1a3a1a',
          bronze: '#8b5a2b',
          stone: '#6b6b6b',
        },
      },
      fontFamily: {
        medieval: ['Cinzel', 'serif'],
        body: ['Crimson Text', 'serif'],
      },
      backgroundImage: {
        'parchment-texture': "url('/textures/parchment.png')",
      },
    },
  },
  plugins: [],
}




