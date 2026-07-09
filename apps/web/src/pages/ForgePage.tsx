import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { forgeApi, missionApi, translateApi } from '../lib/api';
import { SliderCard } from '../components/SliderCard';
import { ForgeAnimation } from '../components/ForgeAnimation';
import { ScoreRadar } from '../components/ScoreRadar';
import { SequenceView } from '../components/SequenceView';
import { Mission, SliderParam } from '@protoforge/shared';

// ---------------------------------------------------------------------------
// 4 档仪式定义(Phase 3 Task 2)
// 不与硬件挂钩 — 玩家在 Settings / 锻炉按钮上方主动选难度。
// 选中后存到 localStorage('protoforge.ritual'),下次启动默认走最后一档。
// ---------------------------------------------------------------------------

export type RitualKey = 'urgent' | 'standard' | 'ancient' | 'crystal';

interface RitualOption {
  key: RitualKey;
  display_name: string;
  difficulty: number;
  duration_range: string;
  cards: number;
  badge: string;
}

const RITUAL_OPTIONS: RitualOption[] = [
  { key: 'urgent', display_name: '急锻', difficulty: 1, duration_range: '2-5s', cards: 4, badge: '急锻者' },
  { key: 'standard', display_name: '主锻', difficulty: 2, duration_range: '30-120s', cards: 6, badge: '主锻匠' },
  { key: 'ancient', display_name: '古法锻', difficulty: 3, duration_range: '5-15min', cards: 8, badge: '古法锻师' },
  { key: 'crystal', display_name: '晶种培育', difficulty: 4, duration_range: '30min-2h', cards: 12, badge: '晶种培育师' },
];

const RITUAL_STORAGE_KEY = 'protoforge.ritual';

function loadRitual(): RitualKey {
  try {
    const stored = window.localStorage.getItem(RITUAL_STORAGE_KEY);
    if (stored && ['urgent', 'standard', 'ancient', 'crystal'].includes(stored)) {
      return stored as RitualKey;
    }
  } catch {
    // localStorage 可能在隐私模式/SSR 下抛错,降级到默认
  }
  return 'urgent';
}

function saveRitual(r: RitualKey): void {
  try {
    window.localStorage.setItem(RITUAL_STORAGE_KEY, r);
  } catch {
    // noop
  }
}

export function ForgePage() {
  const { missionId = '' } = useParams();
  const navigate = useNavigate();
  const [mission, setMission] = useState<Mission | null>(null);
  const [params, setParams] = useState<Record<string, number>>({});
  const [nl, setNl] = useState('');
  const [loading, setLoading] = useState(false);
  const [ritual, setRitual] = useState<RitualKey>(() => loadRitual());
  const [result, setResult] = useState<{
    intron: string;
    fasta: string;
    primary: number;
    components: Record<string, number>;
    weights: Record<string, number>;
    ritual: string;
    duration_ms: number;
    badge_unlocked?: string | null;
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
        natural_language: nl.trim() || undefined,
        ritual, // 玩家主动选的档位
      });
      setResult({
        intron: r.intron,
        fasta: r.fasta,
        primary: r.scores.primary,
        components: r.scores.components,
        weights: r.scores.weights,
        ritual: r.ritual,
        duration_ms: r.duration_ms,
        badge_unlocked: r.badge_unlocked,
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

  const handleSelectRitual = (r: RitualKey) => {
    setRitual(r);
    saveRitual(r);
  };

  if (err) return <p className="text-rose-600">{err}</p>;
  if (!mission) return <p className="text-slate-400">加载任务…</p>;

  const selectedRitual = RITUAL_OPTIONS.find((r) => r.key === ritual)!;

  return (
    <div className="space-y-4" data-testid="forge-page">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">{mission.title}</h1>
        <p className="text-sm text-slate-600">{mission.description}</p>
      </header>

      <section className="rounded-lg border border-slate-200 bg-white p-4" data-testid="ritual-selector">
        <label className="text-sm font-semibold text-slate-700">锻炉档位(玩家主动选择难度)</label>
        <div className="mt-2 grid grid-cols-2 gap-2 md:grid-cols-4" role="group" aria-label="ritual">
          {RITUAL_OPTIONS.map((opt) => {
            const active = opt.key === ritual;
            return (
              <button
                key={opt.key}
                type="button"
                data-testid={`ritual-option-${opt.key}`}
                aria-pressed={active}
                onClick={() => handleSelectRitual(opt.key)}
                className={
                  'rounded border-2 px-3 py-2 text-left text-xs transition-colors ' +
                  (active
                    ? 'border-forge-500 bg-forge-50'
                    : 'border-slate-200 bg-white hover:border-slate-300')
                }
              >
                <div className="text-sm font-bold text-slate-900">
                  {opt.display_name}{' '}
                  <span className="text-amber-500" aria-label={`${opt.difficulty} star`}>
                    {'★'.repeat(opt.difficulty)}
                  </span>
                </div>
                <div className="mt-1 text-slate-600">耗时 {opt.duration_range}</div>
                <div className="text-slate-500">卡牌 {opt.cards} 张</div>
                <div className="mt-1 text-slate-400">徽章:{opt.badge}</div>
              </button>
            );
          })}
        </div>
        {selectedRitual.key === 'crystal' ? (
          <p
            data-testid="ritual-warning"
            className="mt-3 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800"
            role="alert"
          >
            ⚠️ 长时间等待:晶种培育档可能需要 30 分钟到 2 小时,请确认你有时间。
          </p>
        ) : null}
        {selectedRitual.key === 'ancient' ? (
          <p
            data-testid="ritual-warning"
            className="mt-3 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800"
            role="alert"
          >
            ⚠️ 长时间等待:古法锻档可能需要 5 到 15 分钟。
          </p>
        ) : null}
      </section>

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
          data-testid="forge-run"
          className="rounded bg-forge-500 px-4 py-2 text-sm font-semibold text-white hover:bg-forge-600 disabled:opacity-50"
        >
          {loading ? `锻造中(${selectedRitual.display_name})…` : `开始锻造 · ${selectedRitual.display_name}`}
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
