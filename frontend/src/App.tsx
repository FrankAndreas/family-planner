import { BrowserRouter, Route, Routes } from 'react-router-dom';
import CalendarPage from './pages/CalendarPage';
import SettingsPage from './pages/SettingsPage';

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<CalendarPage />} />
                {/* The wall: the same calendar, back to this week after a while untouched */}
                <Route path="/display" element={<CalendarPage />} />
                <Route path="/settings" element={<SettingsPage />} />
            </Routes>
        </BrowserRouter>
    );
}
