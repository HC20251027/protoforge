import { useMemo, useState } from 'react';

interface Props {
  fasta: string;
  intron: string;
}

const CHUNK = 60;

function colorFor(base: string): string {
  switch (base.toUpperCase()) {
    case 'A':
      return 'bg-emerald-200 text-emerald-900';
    case 'T':
      return 'bg-rose-200 text-rose-900';
    case 'G':
      return 'bg-amber-200 text-amber-900';
    case 'C':
      return 'bg-sky-200 text-sky-900';
    default:
      return 'bg-slate-200 text-slate-900';
  }
}

export function SequenceView({ fasta, intron }: Props) {
  const [copied, setCopied] = useState(false);
  const chunks = useMemo(() => {
    const out: string[] = [];
    for (let i = 0; i < intron.length; i += CHUNK) {
      out.push(intron.slice(i, i + CHUNK));
    }
    return out;
  }, [intron]);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(fasta);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3" data-testid="sequence-view">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-800">候选内含子 ({intron.length} bp)</h4>
        <button
          type="button"
          onClick={onCopy}
          className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50"
        >
          {copied ? '已复制' : '复制 FASTA'}
        </button>
      </div>
      <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-50 p-2 font-mono text-xs leading-relaxed">
        {chunks.map((c, i) => (
          <div key={i}>
            <span className="mr-3 inline-block w-12 text-right text-slate-400 tabular-nums">
              {(i * CHUNK + 1).toString().padStart(4, ' ')}
            </span>
            {c.split('').map((b, j) => (
              <span key={j} className={`mr-px inline-block rounded px-0.5 ${colorFor(b)}`}>
                {b}
              </span>
            ))}
          </div>
        ))}
      </pre>
    </div>
  );
}
