import type { Artifact } from '@protoforge/shared';

interface Props {
  artifact: Artifact;
  onOpen?: (id: string) => void;
}

const RITUAL_LABEL: Record<string, string> = {
  swift: '急锻',
  standard: '标准',
  ancient: '古法',
  crystal: '晶种',
};

export function ArtifactCard({ artifact, onOpen }: Props) {
  return (
    <button
      type="button"
      onClick={() => onOpen?.(artifact.id)}
      className="w-full text-left rounded-lg border border-slate-200 bg-white p-3 transition hover:border-forge-500 hover:shadow-sm"
      data-testid={`artifact-${artifact.id}`}
    >
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-900">{artifact.title}</h4>
        <span
          className={[
            'rounded px-2 py-0.5 text-xs',
            artifact.risk_passed
              ? 'bg-emerald-100 text-emerald-800'
              : 'bg-rose-100 text-rose-800',
          ].join(' ')}
        >
          {artifact.risk_passed ? '通过' : '未过'}
        </span>
      </div>
      <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
        <span>{artifact.mission_id}</span>
        <span>·</span>
        <span>{RITUAL_LABEL[artifact.ritual] ?? artifact.ritual}</span>
        <span>·</span>
        <span className="tabular-nums">{artifact.scores.primary.toFixed(3)}</span>
      </div>
      <div className="mt-1 text-[10px] text-slate-400">{artifact.created_at}</div>
    </button>
  );
}
