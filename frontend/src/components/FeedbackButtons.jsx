import { useRef, useState } from "react"
import { sendFeedback } from "../api/client"
import { ThumbDownIcon, ThumbUpIcon } from "./Brand"

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
            <div className="flex flex-wrap items-center gap-2 text-[15px] text-muted">
                <span>Was this helpful?</span>
                {[["up", ThumbUpIcon, "Helpful"], ["down", ThumbDownIcon, "Not helpful"]].map(([value, Icon, label]) => (
                    <button
                        key={value}
                        type="button"
                        aria-label={label}
                        aria-pressed={rating === value}
                        onClick={() => send(value)}
                        className={`grid h-11 w-11 place-items-center rounded-md border text-ink-2 ${rating === value ? "border-green bg-green-soft text-green" : "border-line hover:bg-surface-2"}`}
                    >
                        <Icon size={20} />
                    </button>
                ))}
                {status && <span role="status">{status}</span>}
            </div>
            {rating === "down" && (
                <form onSubmit={sendComment} className="flex gap-2">
                    <input
                        ref={commentref}
                        maxLength={1000}
                        dir="auto"
                        placeholder="What was wrong? (optional)"
                        className="min-h-11 min-w-0 flex-1 rounded-md border border-line bg-surface px-3 text-[15px] text-ink"
                    />
                    <button type="submit" className="min-h-11 rounded-md border border-line px-4 text-[15px] font-semibold text-ink hover:bg-surface-2">Send</button>
                </form>
            )}
        </div>
    )
}
