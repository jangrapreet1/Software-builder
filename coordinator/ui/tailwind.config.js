/** @type {import('tailwindcss').Config} */
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        background: '#000000',
        foreground: '#FFFFFF',
        'subtle-border': 'rgba(255, 255, 255, 0.1)',
        'hover-bg': 'rgba(255, 255, 255, 0.05)',
        card: '#111111',
        'card-foreground': '#FFFFFF',
        primary: '#FFFFFF',
        'primary-foreground': '#000000',
        secondary: '#111111',
        'secondary-foreground': '#FFFFFF',
      }
    },
  },
  plugins: [],
}

