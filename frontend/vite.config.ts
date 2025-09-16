// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,                 // escuta em 0.0.0.0
    port: 5173,                 // porta local do Vite
    allowedHosts: ["jojisdomain.ddns.net"],

    // >>> Escolha APENAS UM dos blocos abaixo <<<

    // A) Acessando direto em http://jojisdomain.ddns.net:5173
    // hmr: {
    //   host: "jojisdomain.ddns.net",
    //   protocol: "ws",
    //   port: 5173,               // mesma porta pública
    // },

    // B) Acessando via proxy em http://jojisdomain.ddns.net (porta 80)
    hmr: {
      host: "jojisdomain.ddns.net",
      protocol: "ws",
      clientPort: 80,         // porta pública que o navegador enxerga
    },
  },
});
