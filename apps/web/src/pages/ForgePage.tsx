import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { forgeApi, missionApi, protoforgeApi, translateApi } from '../lib/api';
import { SliderCard } from '../components/SliderCard';
import { ForgeAnimation } from '../components/ForgeAnimation';
import { ScoreRadar } from '../components/ScoreRadar';
import { SequenceView } from '../components/SequenceView';
import {
  Mission,
  SliderParam,
  UnfinishedRun,
  UploadStatus,
} from '@protoforge/shared';

// ---------------------------------------------------------------------------
// 4 档仪式定义(Phase 3 Task 2)
// 不与硬件挂钩 — 玩家在 Settings / 锻炉按钮上方主动选难度。
// 选中后存到 localStorage('protoforge.ritual'),下次启动默认走最后一档。
// ---------------------------------------------------------------------------

// 本地玩家 ID(Phase 5 接 user system 时换成 auth.uid)
const PLAYER_ID = 'default';

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

const RITUAL_DISPLAY: Record<string, string> = {
  urgent: '急锻档',
  standard: '主锻档',
  ancient: '古法锻档',
  crystal: '晶种培育档',
};

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
    upload?: UploadStatus;
  } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  // Phase 3 Task 3:上次未完成的 run 列表
  const [unfinished, setUnfinished] = useState<UnfinishedRun[]>([]);
  // Phase 3 Task 5:通关 toast
  const [toast, setToast] = useState<{ kind: 'success' | 'info' | 'warn'; text: string } | null>(null);
  // Phase 3 Task 5:待上传队列数
  const [pendingCount, setPendingCount] = useState(0);
  // 弹窗:显示队列详情
  const [showQueue, setShowQueue] = useState(false);

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

  // Phase 3 Task 3:启动时加载"上次未完成的锻造"列表
  useEffect(() => {
    forgeApi
      .unfinished()
      .then((items) => setUnfinished(items))
      .catch(() => {
        // 后端 0 列表 / 失败 → 不阻塞 UI
        setUnfinished([]);
      });
  }, []);

  // Phase 3 Task 5:启动时加载"待上传队列"数量(给右上角计数器用)
  const refreshPendingCount = () => {
    protoforgeApi
      .queue(PLAYER_ID)
      .then((r) => setPendingCount(r.pending_count))
      .catch(() => setPendingCount(0));
  };
  useEffect(() => {
    refreshPendingCount();
  }, []);

  const handleRestartUnfinished = (r: UnfinishedRun) => {
    // LOSE 的"重新开始"按钮:直接切到该 ritual(后端 run_forge 走完整流程)
    handleSelectRitual(r.ritual);
    // 不主动触发 forge — 让玩家自己点"开始锻造"
  };

  const handleSimulateExit = () => {
    // dev 专用:模拟"锻造中途退出" — 走 exit-evaluate 看 outcome
    // 这是测试按钮,仅 dev 可见。
    if (!import.meta.env.DEV) return;
    alert(
      '⚠️ 锻造中退出游戏会有概率失败\n' +
        '(dev 模拟:请直接关闭浏览器标签页,然后重新打开本页面 — 顶部"上次未完成的锻造"会展示真实 outcome)',
    );
  };

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
        upload: r.upload,
      });

      // Phase 3 Task 5:通关后 toast(按 upload.status 决定文案)
      const upload = r.upload;
      if (upload && upload.queued) {
        if (upload.status === 'uploaded') {
          setToast({ kind: 'success', text: upload.message || '✅ 已上传' });
        } else if (upload.status === 'queued') {
          setToast({ kind: 'info', text: upload.message || '📦 已入队' });
        } else if (upload.status === 'failed') {
          setToast({ kind: 'warn', text: upload.message || '⚠️ 上传失败' });
        }
        // 刷新队列计数器
        refreshPendingCount();
        // 6 秒后自动消失
        setTimeout(() => setToast(null), 6000);
      }
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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{mission.title}</h1>
            <p className="text-sm text-slate-600">{mission.description}</p>
          </div>
          {/* Phase 3 Task 5:待上传队列计数器(右上角,点击展开弹窗) */}
          <button
            type="button"
            data-testid="upload-queue-counter"
            onClick={() => {
              refreshPendingCount();
              setShowQueue(true);
            }}
            className={
              'rounded-full px-3 py-1 text-xs font-semibold transition-colors ' +
              (pendingCount > 0
                ? 'bg-amber-100 text-amber-800 hover:bg-amber-200'
                : 'bg-slate-100 text-slate-500 hover:bg-slate-200')
            }
            title="点击查看待上传作品"
          >
            📦 待上传: {pendingCount}
          </button>
        </div>
      </header>

      {/* Phase 3 Task 5:通关后 toast(浮动显示 6 秒) */}
      {toast ? (
        <div
          data-testid="upload-toast"
          data-toast-kind={toast.kind}
          role="status"
          className={
            'fixed right-6 top-20 z-50 max-w-sm rounded-lg border px-4 py-3 text-sm shadow-lg ' +
            (toast.kind === 'success'
              ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
              : toast.kind === 'warn'
                ? 'border-rose-300 bg-rose-50 text-rose-800'
                : 'border-sky-300 bg-sky-50 text-sky-800')
          }
        >
          {toast.text}
        </div>
      ) : null}

      {/* Phase 3 Task 5:待上传队列弹窗(简易版,Phase 5 接 user system 时换 /exports 完整页) */}
      {showQueue ? (
        <div
          data-testid="upload-queue-modal"
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/30"
          onClick={() => setShowQueue(false)}
        >
          <div
            className="max-h-[80vh] w-full max-w-md overflow-y-auto rounded-lg bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">待上传队列 ({pendingCount})</h2>
              <button
                type="button"
                onClick={() => setShowQueue(false)}
                className="text-slate-500 hover:text-slate-700"
                aria-label="关闭"
              >
                ✕
              </button>
            </div>
            {pendingCount === 0 ? (
              <p className="text-sm text-slate-500">暂无待上传作品</p>
            ) : (
              <button
                type="button"
                data-testid="upload-queue-retry"
                onClick={async () => {
                  await protoforgeApi.retry(PLAYER_ID);
                  refreshPendingCount();
                }}
                className="w-full rounded bg-forge-500 px-3 py-2 text-sm font-semibold text-white hover:bg-forge-600"
              >
                立即重试所有待上传
              </button>
            )}
          </div>
        </div>
      ) : null}

      {/* Phase 3 Task 3:开炉时(loading=true)顶部红色横幅 — 固定文案,无百分比 */}
      {loading ? (
        <div
          data-testid="exit-penalty-banner"
          role="alert"
          className="rounded border-2 border-rose-400 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-800"
        >
          ⚠️ 锻造中退出游戏会有概率失败
        </div>
      ) : null}

      {/* Phase 3 Task 3:上次未完成的锻造列表(KEEP/LOSE 区分) */}
      {unfinished.length > 0 ? (
        <section
          className="rounded-lg border border-slate-200 bg-white p-4"
          data-testid="unfinished-section"
        >
          <h2 className="text-sm font-semibold text-slate-700">上次未完成的锻造</h2>
          <ul className="mt-2 space-y-2" role="list">
            {unfinished.map((u) => {
              const isKeep = u.outcome === 'keep';
              return (
                <li
                  key={u.run_id}
                  data-testid={`unfinished-${u.outcome}`}
                  data-run-id={u.run_id}
                  className={
                    'rounded border px-3 py-2 text-sm ' +
                    (isKeep
                      ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
                      : 'border-rose-300 bg-rose-50 text-rose-800')
                  }
                >
                  <div className="flex items-center justify-between">
                    <span>
                      <strong>{RITUAL_DISPLAY[u.ritual] ?? u.ritual}</strong>
                      {' · '}
                      {isKeep ? (
                        <span data-testid="unfinished-keep-label">✓ 可继续查看结果</span>
                      ) : (
                        <span data-testid="unfinished-lose-label">✗ 已丢失(进度不足)</span>
                      )}
                    </span>
                    {!isKeep ? (
                      <button
                        type="button"
                        data-testid="unfinished-restart"
                        onClick={() => handleRestartUnfinished(u)}
                        className="rounded bg-rose-600 px-2 py-1 text-xs text-white hover:bg-rose-700"
                      >
                        重新开始
                      </button>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

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

      <section className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={handleRun}
          disabled={loading}
          data-testid="forge-run"
          className="rounded bg-forge-500 px-4 py-2 text-sm font-semibold text-white hover:bg-forge-600 disabled:opacity-50"
        >
          {loading ? `锻造中(${selectedRitual.display_name})…` : `开始锻造 · ${selectedRitual.display_name}`}
        </button>
        {import.meta.env.DEV ? (
          <button
            type="button"
            onClick={handleSimulateExit}
            data-testid="exit-during-forge"
            className="rounded border border-rose-400 bg-rose-50 px-3 py-2 text-xs text-rose-700 hover:bg-rose-100"
            title="dev only: 提示玩家去真的关闭浏览器看 outcome"
          >
            模拟中途退出 (dev)
          </button>
        ) : null}
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
