import type { Mission } from '@protoforge/shared';

interface Props {
  mission: Mission;
  onSelect?: (id: string) => void;
  selected?: boolean;
}

const SCENARIO_LABEL: Record<string, string> = {
  polar: '极地',
  ocean: '深海',
  soil: '土壤',
  lunar: '月表',
  custom: '自定义',
};

const LEVEL_LABEL: Record<string, string> = {
  tutorial: '教学',
  delegation: '委托',
  network: '网络',
  tricky: '刁钻',
  free: '自由',
};

export function MissionCard({ mission, onSelect, selected }: Props) {
  return (
    <button
      type="button"
      onClick={() => onSelect?.(mission.id)}
      className={[
        'w-full text-left rounded-lg border p-4 transition',
        'hover:border-forge-500 hover:shadow-sm',
        selected ? 'border-forge-500 bg-forge-50' : 'border-slate-200 bg-white',
      ].join(' ')}
      data-testid={`mission-card-${mission.id}`}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900">{mission.title}</h3>
        <span className="text-xs uppercase tracking-wide text-slate-500">
          {SCENARIO_LABEL[mission.scenario] ?? mission.scenario}
        </span>
      </div>
      <p className="mt-1 text-sm text-slate-600 line-clamp-2">{mission.description}</p>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <span className="rounded bg-slate-100 px-2 py-1 text-slate-700">
          {LEVEL_LABEL[mission.level] ?? mission.level}
        </span>
        <span className="rounded bg-slate-100 px-2 py-1 text-slate-700">
          目标: {mission.target_cell_line}
        </span>
        <span className="rounded bg-slate-100 px-2 py-1 text-slate-700">
          脱靶: {mission.off_target}
        </span>
        <span className="rounded bg-slate-100 px-2 py-1 text-slate-700">
          滑块 ×{mission.sliders.length}
        </span>
        <span className="rounded bg-slate-100 px-2 py-1 text-slate-700">
          风险题 ×{mission.risk_rules.length}
        </span>
      </div>
    </button>
  );
}
