import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export function Home() {
  const [status, setStatus] = useState<string>('检查中…');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.health()
      .then((d) => setStatus(`后端在线 · v${d.version}`))
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8">
      <h1 className="text-5xl font-bold text-forge-500">ProtoForge</h1>
      <p className="mt-4 text-slate-400 text-lg">原体锻炉 · 合成生物学众包游戏化平台</p>
      <div className="mt-12 p-6 rounded-lg bg-slate-900 border border-slate-800 max-w-md w-full">
        <p className="text-sm text-slate-500">Python sidecar</p>
        {error ? (
          <p className="mt-2 text-red-400 font-mono text-sm">{error}</p>
        ) : (
          <p className="mt-2 text-emerald-400 font-mono text-sm">{status}</p>
        )}
      </div>
    </main>
  );
}
