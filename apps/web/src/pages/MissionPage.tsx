import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { missionApi } from '../lib/api';
import { MissionCard } from '../components/MissionCard';
import type { Mission } from '@protoforge/shared';

export function MissionPage() {
  const [missions, setMissions] = useState<Mission[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    missionApi
      .list()
      .then(setMissions)
      .catch((e: Error) => setErr(e.message));
  }, []);

  return (
    <div className="space-y-4" data-testid="mission-page">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">任务列表</h1>
        <p className="text-sm text-slate-600">选择一个细胞工程挑战,开始锻造。</p>
      </header>

      {err ? <p className="text-rose-600">{err}</p> : null}
      {!missions && !err ? <p className="text-slate-400">加载中…</p> : null}

      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {missions?.map((m) => (
          <li key={m.id}>
            <Link to={`/missions/${m.id}/forge`} className="block">
              <MissionCard mission={m} />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
