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
