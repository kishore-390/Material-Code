/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#0a1526",
          900: "#0e1d33",
          800: "#132a49",
          700: "#1a3a63",
        },
        brand: {
          50: "#eaf2fb",
          100: "#cfe1f4",
          500: "#0b5394",
          600: "#0a4a83",
          700: "#073761",
        },
        saffron: {
          50: "#fff5e8",
          500: "#ff9933",
          600: "#e07f16",
        },
        flag: {
          50: "#eaf7e9",
          500: "#138808",
          600: "#0f6d07",
        },
        success: {
          50: "#ecfdf5",
          500: "#16a34a",
          600: "#15803d",
        },
        warning: {
          50: "#fffbeb",
          500: "#ea8c00",
          600: "#c2680a",
        },
        danger: {
          50: "#fef2f2",
          500: "#dc2626",
          600: "#b91c1c",
        },
      },
      fontFamily: {
        sans: ["'Noto Sans'", "'Noto Sans Devanagari'", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        sm: "2px",
        DEFAULT: "3px",
        md: "4px",
        lg: "5px",
        xl: "6px",
        "2xl": "6px",
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
      },
    },
  },
  plugins: [],
};
