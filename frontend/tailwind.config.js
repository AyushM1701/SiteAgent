/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        base: '#0f1012',
        sidebar: '#141619',
        panel: '#191c20',
        elevated: '#20242a',
        input: '#141619',
        border: 'rgba(255, 255, 255, 0.08)',
        'border-subtle': 'rgba(255, 255, 255, 0.04)',
        accent: {
          DEFAULT: '#6ee7b7',
          hover: '#a7f3d0',
          dim: 'rgba(110, 231, 183, 0.10)',
          glow: 'rgba(110, 231, 183, 0.18)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Cascadia Code', 'monospace'],
      },
    },
  },
  plugins: [],
};
