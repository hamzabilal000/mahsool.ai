import axios from "axios"
import { parseEvents } from "../lib/sse.js"

axios.defaults.withCredentials = true

export const API_URL = import.meta.env?.VITE_API_URL || "http://localhost:8000"

// The backend is served through ngrok's free static domain, which answers browser requests
// with an HTML warning page unless this header is sent.
export const API_HEADERS = { "ngrok-skip-browser-warning": "true" }

export const api = axios.create({ baseURL: API_URL, withCredentials: true, headers: API_HEADERS })

export const OFFLINE_MESSAGE = "Mahsool AI is resting right now. Please try again later."

// Every API response is {success, data, error, code}; HTTP errors carry the same body. Anything
// else (no answer at all, ngrok's "endpoint offline" page, a 502 while the server restarts)
// means the backend is not reachable, and the visitor gets the friendly offline message.
export function envelopeOf(err) {
    let body = err?.response?.data
    if (body && typeof body === "object" && body.code) return body
    return { success: false, data: null, error: OFFLINE_MESSAGE, code: "OFFLINE" }
}

// GET /health: true when the backend answers.
export async function isOnline() {
    try {
        let res = await api.get("/health", { timeout: 8000 })
        return res.data?.success === true
    } catch {
        return false
    }
}

// POST /ask/stream. Calls onStage(stage), onDelta(text) while the answer arrives and resolves
// with the final envelope (same shape as POST /ask).
export async function askStream({ question, taxYear }, { onStage, onDelta }) {
    let offset = 0
    let final = null
    function handle(text) {
        let parsed = parseEvents(text, offset)
        offset = parsed.offset
        for (let { event, data } of parsed.events) {
            if (event === "stage") onStage?.(data.stage)
            else if (event === "delta") onDelta?.(data.text)
            else if (event === "done" || event === "error") final = data
        }
    }
    try {
        let res = await api.post(
            "/ask/stream",
            { question, tax_year: taxYear },
            {
                responseType: "text",
                headers: { Accept: "text/event-stream" },
                onDownloadProgress: (e) => handle(e.event?.target?.responseText ?? ""),
            },
        )
        handle(typeof res.data === "string" ? res.data : "")
    } catch (err) {
        return envelopeOf(err)
    }
    return final ?? { success: false, data: null, error: "The answer stream ended early.", code: "STREAM_ERROR" }
}

export async function sendFeedback({ askId, rating, comment }) {
    try {
        let res = await api.post("/feedback", { ask_id: askId, rating, comment })
        return res.data
    } catch (err) {
        return envelopeOf(err)
    }
}

export async function getEvalSummary() {
    try {
        let res = await api.get("/eval/summary")
        return res.data
    } catch (err) {
        return envelopeOf(err)
    }
}

// Fetched with the ngrok header (an <img src> cannot send it) and shown from an object URL.
export async function getAblationChart() {
    try {
        let res = await api.get("/eval/ablation.png", { responseType: "blob" })
        return URL.createObjectURL(res.data)
    } catch {
        return null
    }
}
