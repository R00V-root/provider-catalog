import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { cwd } from "node:process";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, cwd(), "");
  return {
    plugins: [react()],
    server: {
      host: true,
      port: Number(env.VITE_PORT || 5173)
    }
  };
});
