import { BrowserRouter, Routes, Route } from "react-router-dom"
import { ChatPage } from "./Pages/ChatPage"
import { EvalPage } from "./Pages/EvalPage"

export function App() {
    return (
        <>
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<ChatPage />} />
                    <Route path="/eval" element={<EvalPage />} />
                </Routes>
            </BrowserRouter>
        </>
    )
}
