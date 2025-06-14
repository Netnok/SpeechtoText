// src/app/router.tsx
import {BrowserRouter, Route, Routes} from 'react-router-dom'
import RecordingPage from "../pages/RecordingPage.tsx";

const AppRouter = () => {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<RecordingPage />} />
                {/*예시*/}
                {/*<Route path="/" element={<RecordingPage />} />*/}
                {/*<Route path="/about" element={<AboutPage />} />*/}
                {/*<Route path="*" element={<NotFoundPage />} />*/}
            </Routes>
        </BrowserRouter>
    )
}

export { AppRouter }
