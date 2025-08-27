/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dxsafety': {
          'primary': '#3b82f6',
          'secondary': '#64748b',
          'success': '#10b981',
          'warning': '#f59e0b',
          'danger': '#ef4444',
          'info': '#06b6d4'
        }
      }
    },
  },
  plugins: [],
}
