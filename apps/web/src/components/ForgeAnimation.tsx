interface Props {
  active: boolean;
  ritual?: string;
  durationMs?: number;
}

export function ForgeAnimation({ active, ritual, durationMs }: Props) {
  return (
    <div
      className="rounded-lg border border-slate-200 bg-slate-50 p-4"
      data-testid="forge-animation"
      data-active={active ? 'true' : 'false'}
    >
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-600">仪式</span>
        <span className="font-medium text-slate-800">{ritual ?? '—'}</span>
      </div>
      <div className="mt-3 h-24 overflow-hidden rounded bg-slate-900">
        <div
          className={[
            'h-full w-1/3 bg-gradient-to-r from-forge-400 via-forge-500 to-forge-700',
            active ? 'animate-[pulse_1.2s_ease-in-out_infinite]' : 'opacity-40',
          ].join(' ')}
          style={{
            animation: active ? 'pulse 1.2s ease-in-out infinite' : 'none',
          }}
        />
        <style>{`@keyframes pulse { 0%,100%{opacity:0.4} 50%{opacity:1} }`}</style>
      </div>
      <div className="mt-2 text-right text-xs text-slate-500 tabular-nums">
        {typeof durationMs === 'number' ? `${durationMs} ms` : ''}
      </div>
    </div>
  );
}
