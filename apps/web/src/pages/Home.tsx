import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { healthApi } from '../lib/api';

interface Health {
  status: string;
  version: string;
  data_dir: string;
  proto_profile: string;
}

export function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    healthApi
      .get()
      .then((d) => setHealth(d as Health))
      .catch((e: Error) => setErr(e.message));
  }, []);

  return (
    <div className="space-y-6" data-testid="home-page">
      <section>
        <h1 className="text-3xl font-bold text-slate-900">原体锻炉 ProtoForge</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          把 Stanford Proto 论文里的合成生物学任务做成可玩的卡牌式体验。
          从极地耐低温发光菌开始,设计一段只能在你选择的细胞系里正确剪接的内含子。
        </p>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-700">侧车状态</h3>
          {err ? (
            <p className="mt-2 text-rose-600">连接失败: {err}</p>
          ) : health ? (
            <ul className="mt-2 space-y-1 text-sm text-slate-600">
              <li>状态: <span className="font-medium text-emerald-600">{health.status}</span></li>
              <li>版本: {health.version}</li>
              <li>数据目录: {health.data_dir}</li>
              <li>Proto profile: {health.proto_profile}</li>
            </ul>
          ) : (
            <p className="mt-2 text-slate-400">连接中…</p>
          )}
        </div>

        <Link
          to="/missions"
          className="rounded-lg border border-forge-500 bg-forge-50 p-4 transition hover:bg-forge-100"
        >
          <h3 className="text-sm font-semibold text-forge-700">进入任务列表 →</h3>
          <p className="mt-1 text-sm text-slate-600">选择挑战,设置参数,锻造内含子。</p>
        </Link>

        <Link
          to="/onboarding"
          className="rounded-lg border border-slate-200 bg-white p-4 transition hover:bg-slate-50"
        >
          <h3 className="text-sm font-semibold text-slate-700">LLM 配置</h3>
          <p className="mt-1 text-sm text-slate-600">接入云端 API、本地模型,或保持纯滑块模式。</p>
        </Link>
      </section>
    </div>
  );
}
