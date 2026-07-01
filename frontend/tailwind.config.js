export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: { 50:"#eff6ff",100:"#dbeafe",500:"#3b82f6",600:"#2563eb",700:"#1d4ed8",900:"#1e3a8a" },
      },
      animation: { "slide-in": "slideIn 0.3s ease-out" },
      keyframes: { slideIn: { from: { opacity: 0, transform: "translateY(-8px)" }, to: { opacity: 1, transform: "translateY(0)" } } },
    },
  },
  plugins: [],
};
