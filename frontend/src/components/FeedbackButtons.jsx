import { useRef, useState } from "react"
import { sendFeedback } from "../api/client"

export function FeedbackButtons({ askId }) {
    let commentref = useRef()
    let [rating, setRating] = useState(null)
    let [status, setStatus] = useState("")

    async function send(value, comment) {
        setRating(value)
        let res = await sendFeedback({ askId, rating: value, comment })
        if (res.success == true) setStatus(comment ? "Thanks — comment saved." : "Thanks for the feedback.")
        else setStatus(res.error || "Could not save feedback.")
    }

    function sendComment(e) {
        e.preventDefault()
        let comment = commentref.current.value.trim()
        if (comment) send(rating, comment)
    }

    if (!askId) return null
    return (
        <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-muted">
                <span>Was this helpful?</span>
                {[["up", "👍", "Helpful"], ["down", "👎", "Not helpful"]].map(([value, icon, label]) => (
                    <button
                        key={value}
                        type="button"
                        aria-label={label}
                        aria-pressed={rating === value}
                        onClick={() => send(value)}
                        className={`rounded-md border px-2 py-0.5 text-sm ${rating === value ? "border-accent bg-accent-soft" : "border-line hover:bg-sunken"}`}
                    >
                        {icon}
                    </button>
                ))}
                {status && <span role="status">{status}</span>}
            </div>
            {rating === "down" && (
                <form onSubmit={sendComment} className="flex gap-2">
                    <input
                        ref={commentref}
                        maxLength={1000}
                        placeholder="What was wrong? (optional)"
                        className="min-w-0 flex-1 rounded-md border border-line bg-panel px-2 py-1 text-xs"
                    />
                    <button type="submit" className="rounded-md border border-line px-2 py-1 text-xs hover:bg-sunken">Send</button>
                </form>
            )}
        </div>
    )
}
