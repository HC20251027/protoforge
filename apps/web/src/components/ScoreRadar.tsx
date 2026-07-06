import type { ScoreVector } from '@protoforge/shared';

interface Props {
  scores: ScoreVector;
}

const METRICS: { key: string; label: string }[] = [
  { key: 'target_splice', label: '目标剪接' },
  { key: 'orthogonality', label: '正交性(越低越好)' },
  { key: 'gc_penalty', label: 'GC 偏离(越低越好)' },
  { key: 'length_penalty', label: '长度偏离(越低越好)' },
  { key: 'kmer_entropy', label: '序列熵' },
];

export function ScoreRadar({ scores }: Props) {
  const components = scores.components;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4" data-testid="score-radar">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-900">综合评分</h3>
        <span className="text-2xl font-bold text-forge-600">{scores.primary.toFixed(3)}</span>
      </div>
      <ul className="space-y-2 text-sm">
        {METRICS.map((m) => {
          const v = components[m.key];
          if (typeof v !== 'number') return null;
          const pct = Math.max(0, Math.min(1, v)) * 100;
          return (
            <li key={m.key} className="flex items-center gap-2">
              <span className="w-40 shrink-0 text-slate-600">{m.label}</span>
              <div className="h-2 flex-1 rounded bg-slate-100">
                <div
                  className="h-2 rounded bg-forge-500"
                  style={{ width: `${pct.toFixed(1)}%` }}
                />
              </div>
              <span className="w-14 text-right tabular-nums text-slate-700">
                {v.toFixed(3)}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
