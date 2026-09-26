import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

// The API runs separately (uvicorn on :8000); the browser calls it directly with CORS +
// credentials, so no dev proxy is needed. Set VITE_API_URL to point elsewhere.
export default defineConfig({
    plugins: [react(), tailwindcss()],
    server: { port: 5173, strictPort: true },
})
