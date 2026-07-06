import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { forgeApi, missionApi, translateApi } from '../lib/api';
import { SliderCard } from '../components/SliderCard';
import { ForgeAnimation } from '../components/ForgeAnimation';
import { ScoreRadar } from '../components/ScoreRadar';
import { SequenceView } from '../components/SequenceView';
import { Mission, SliderParam } from '@protoforge/shared';

export function ForgePage() {
  const { missionId = '' } = useParams();
  const navigate = useNavigate();
  const [mission, setMission] = useState<Mission | null>(null);
  const [params, setParams] = useState<Record<string, number>>({});
  const [nl, setNl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    intron: string;
    fasta: string;
    primary: number;
    components: Record<string, number>;
    weights: Record<string, number>;
    ritual: string;
    duration_ms: number;
  } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    missionApi
      .get(missionId)
      .then((m) => {
        setMission(m);
        const defaults: Record<string, number> = {};
        m.sliders.forEach((s: SliderParam) => {
          defaults[s.key] = s.default;
        });
        setParams(defaults);
      })
      .catch((e: Error) => setErr(e.message));
  }, [missionId]);

  const handleRun = async () => {
    if (!mission) return;
    setLoading(true);
    setErr(null);
    try {
      const r = await forgeApi.run({
        mission_id: mission.id,
        params,
        generator: 'preference',
      });
      setResult({
        intron: r.intron,
        fasta: r.fasta,
        primary: r.scores.primary,
        components: r.scores.components,
        weights: r.scores.weights,
        ritual: r.ritual,
        duration_ms: r.duration_ms,
      });
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleTranslate = async () => {
    if (!mission || !nl.trim()) return;
    try {
      const r = await translateApi.run({ mission_id: mission.id, text: nl });
      setParams((prev) => ({ ...prev, ...r.values }));
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  if (err) return <p className="text-rose-600">{err}</p>;
  if (!mission) return <p className="text-slate-400">加载任务…</p>;

  return (
    <div className="space-y-4" data-testid="forge-page">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">{mission.title}</h1>
        <p className="text-sm text-slate-600">{mission.description}</p>
      </header>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <label className="text-sm font-semibold text-slate-700">自然语言描述(可选)</label>
        <div className="mt-2 flex gap-2">
          <input
            value={nl}
            onChange={(e) => setNl(e.target.value)}
            placeholder="例如:严格一点,确保 HEK293 一定不表达"
            className="flex-1 rounded border border-slate-300 px-2 py-1 text-sm"
          />
          <button
            type="button"
            onClick={handleTranslate}
            className="rounded bg-slate-800 px-3 py-1 text-sm text-white hover:bg-slate-700"
          >
            翻译成参数
          </button>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {mission.sliders.map((s) => (
          <SliderCard
            key={s.key}
            param={s}
            value={params[s.key] ?? s.default}
            onChange={(v) => setParams((p) => ({ ...p, [s.key]: v }))}
          />
        ))}
      </section>

      <section className="flex gap-3">
        <button
          type="button"
          onClick={handleRun}
          disabled={loading}
          className="rounded bg-forge-500 px-4 py-2 text-sm font-semibold text-white hover:bg-forge-600 disabled:opacity-50"
        >
          {loading ? '锻造中…' : '开始锻造'}
        </button>
        {result ? (
          <button
            type="button"
            onClick={() => navigate(`/missions/${missionId}/risk`)}
            className="rounded border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
          >
            进入风险门 →
          </button>
        ) : null}
      </section>

      <section className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <ForgeAnimation active={loading} ritual={result?.ritual} durationMs={result?.duration_ms} />
        {result ? (
          <ScoreRadar
            scores={{ primary: result.primary, components: result.components, weights: result.weights }}
          />
        ) : null}
      </section>

      {result ? <SequenceView fasta={result.fasta} intron={result.intron} /> : null}
    </div>
  );
}
