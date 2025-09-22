import type { Config } from 'tailwindcss'

const config: Config = {
    content: [
        './pages/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
        './app/**/*.{js,ts,jsx,tsx,mdx}', // This line is the most important one
      ],
  theme: {
    extend: {
      // Add custom animations
      keyframes: {
        aurora: {
          from: { backgroundPosition: '0% 50%' },
          to: { backgroundPosition: '100% 50%' },
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        aurora: 'aurora 20s ease-in-out infinite',
        'fade-in-up': 'fade-in-up 0.5s ease-out',
      },
    },
  },
  plugins: [],
}
export default config