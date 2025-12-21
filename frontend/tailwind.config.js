/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: 'var(--bg-darker)',
        darkBg: 'var(--bg-color)',
        darkBorder: 'var(--border-color)',
        accent: 'var(--accent-color)',
        primary: 'var(--text-primary)',
        secondary: 'var(--text-secondary)',
      }
    },
  },
  plugins: [],
}
