import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Конфигурация Vite.
// base: "/" — если интерфейс размещается в подкаталоге портала
// (например ai.knus.edu.kz/career/), поменяйте на "/career/".
export default defineConfig({
  plugins: [react()],
  base: "/",
  server: {
    port: 5173,
    // Прокси на backend в режиме разработки: запросы /api/* идут на ядро.
    // На проде эту роль выполняет reverse-proxy портала (nginx), который заодно
    // скрывает адрес бэкенда и навешивает авторизацию (Azure AD SSO / вход вуза).
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
