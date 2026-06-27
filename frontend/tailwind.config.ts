import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef6ff",
          100: "#d9eaff",
          200: "#bcdaff",
          300: "#8ec2ff",
          400: "#599fff",
          500: "#3377f6",
          600: "#1f59db",
          700: "#1a47b0",
          800: "#1b3d8c",
          900: "#1b3670",
        },
      },
    },
  },
  plugins: [],
};

export default config;
