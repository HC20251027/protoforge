import type { SliderParam } from '@protoforge/shared';

interface Props {
  param: SliderParam;
  value: number;
  onChange: (v: number) => void;
}

export function SliderCard({ param, value, onChange }: Props) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3" data-testid={`slider-${param.key}`}>
      <div className="flex items-baseline justify-between">
        <label htmlFor={`slider-${param.key}`} className="text-sm font-medium text-slate-800">
          {param.label}
        </label>
        <span className="text-sm font-semibold text-forge-600 tabular-nums">
          {Number.isInteger(param.step) ? value.toFixed(0) : value.toFixed(3)}
        </span>
      </div>
      <input
        id={`slider-${param.key}`}
        type="range"
        min={param.min}
        max={param.max}
        step={param.step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="mt-2 w-full accent-forge-500"
      />
      <div className="mt-1 flex justify-between text-[10px] text-slate-400 tabular-nums">
        <span>{param.min}</span>
        <span>{param.max}</span>
      </div>
      {param.description ? (
        <p className="mt-1 text-xs text-slate-500">{param.description}</p>
      ) : null}
    </div>
  );
}
