/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        blue: {
          50: "#f5effa",
          100: "#eee1f6",
          200: "#dcc6e9",
          300: "#c39cd8",
          400: "#aa77c6",
          500: "#9258b4",
          600: "#7f459f",
          700: "#683887",
          800: "#522e6b",
          900: "#3b224d",
          950: "#291336",
        },
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
      },
    },
  },
  plugins: [],
};
