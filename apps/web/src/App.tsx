import { NavLink, Route, Routes, Navigate } from 'react-router-dom';
import { Home } from './pages/Home';
import { MissionPage } from './pages/MissionPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { ForgePage } from './pages/ForgePage';
import { RiskGatePage } from './pages/RiskGatePage';
import { GalleryPage } from './pages/GalleryPage';

function NavBar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    [
      'rounded px-3 py-1.5 text-sm font-medium transition',
      isActive ? 'bg-forge-500 text-white' : 'text-slate-600 hover:bg-slate-100',
    ].join(' ');

  return (
    <nav className="flex items-center gap-2 border-b border-slate-200 bg-white px-6 py-3">
      <span className="mr-4 text-lg font-bold text-forge-600">ProtoForge</span>
      <NavLink to="/" end className={linkClass}>主页</NavLink>
      <NavLink to="/missions" className={linkClass}>任务</NavLink>
      <NavLink to="/onboarding" className={linkClass}>LLM 配置</NavLink>
      <NavLink to="/gallery" className={linkClass}>作品库</NavLink>
    </nav>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <NavBar />
      <main className="mx-auto max-w-6xl px-6 py-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/missions" element={<MissionPage />} />
          <Route path="/missions/:missionId/forge" element={<ForgePage />} />
          <Route path="/missions/:missionId/risk" element={<RiskGatePage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/gallery" element={<GalleryPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
