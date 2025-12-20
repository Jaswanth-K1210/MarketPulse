/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: '#0F1419',
        darkBg: '#1A1F2E',
        darkBorder: '#2A3139',
        accent: '#3B82F6',
      }
    },
  },
  plugins: [],
}
