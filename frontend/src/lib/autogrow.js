// Height for the text: at least 2 rows, at most 6 (then the textarea scrolls). The textarea is
// border-box with no border, so its height is the text plus its vertical padding.
export function autoGrow(el) {
    if (!el) return
    let style = getComputedStyle(el)
    let line = parseFloat(style.lineHeight) || 30
    let pad = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom)
    el.style.height = "auto"
    el.style.height = `${Math.min(Math.max(el.scrollHeight, line * 2 + pad), line * 6 + pad)}px`
}
