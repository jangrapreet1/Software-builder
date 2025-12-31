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
        sans: ['Inter', 'Outfit', 'sans-serif'], // Added Outfit for headings if needed
      },
      colors: {
        background: '#0f172a', // Deep slate for rich background
        foreground: '#f8fafc', // Bright white-ish text
        card: 'rgba(30, 41, 59, 0.7)', // Glassy dark slate
        'card-foreground': '#f1f5f9',
        primary: '#6366f1', // Indigo 500
        'primary-foreground': '#ffffff',
        secondary: '#1e293b', // Slate 800
        'secondary-foreground': '#cbd5e1',
        accent: '#8b5cf6', // Violet 500
        'accent-foreground': '#ffffff',
        destructive: '#ef4444',
        'destructive-foreground': '#ffffff',
        border: 'rgba(148, 163, 184, 0.1)',
        input: 'rgba(15, 23, 42, 0.5)',
        ring: '#6366f1',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'hero-gradient': 'linear-gradient(to bottom right, #0f172a, #1e1b4b)', // Slate to dark indigo
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'pulse-slow': 'pulse 3s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

