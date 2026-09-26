import axios from "axios"

axios.defaults.withCredentials = true

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export const api = axios.create({ baseURL: API_URL, withCredentials: true })

// Every API response is {success, data, error, code}; HTTP errors carry the same body.
function envelopeOf(err) {
    if (err.response?.data?.code) return err.response.data
    return { success: false, data: null, error: "Can't reach the Mahsool API. Is it running?", code: "NETWORK_ERROR" }
}

// Parse server-sent events out of a growing response text. Returns the events found after
// `offset` and the new offset (the end of the last complete event).
export function parseEvents(text, offset) {
    let events = []
    let end = text.indexOf("\n\n", offset)
    while (end !== -1) {
        let block = text.slice(offset, end)
        let event = "message"
        let data = ""
        for (let line of block.split("\n")) {
            if (line.startsWith("event: ")) event = line.slice(7)
            else if (line.startsWith("data: ")) data += line.slice(6)
        }
        if (data) events.push({ event, data: JSON.parse(data) })
        offset = end + 2
        end = text.indexOf("\n\n", offset)
    }
    return { events, offset }
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

export const ABLATION_CHART_URL = `${API_URL}/eval/ablation.png`
