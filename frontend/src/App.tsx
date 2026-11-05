import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

function Placeholder() {
    const { t } = useTranslation();
    return <h1 className="p-6 text-2xl">{t('app.title')}</h1>;
}

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Placeholder />} />
                <Route path="/display" element={<Placeholder />} />
                <Route path="/settings" element={<Placeholder />} />
            </Routes>
        </BrowserRouter>
    );
}
