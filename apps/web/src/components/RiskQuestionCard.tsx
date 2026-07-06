import { useState } from 'react';
import type { RiskRule } from '@protoforge/shared';

interface Props {
  rule: RiskRule;
  index: number;
  onAnswer: (ruleId: string, answer: string) => void;
  locked?: boolean;
  result?: { correct: boolean; explanation: string };
}

export function RiskQuestionCard({ rule, index, onAnswer, locked, result }: Props) {
  const [picked, setPicked] = useState<string | null>(null);

  const handlePick = (value: string) => {
    if (locked) return;
    setPicked(value);
    onAnswer(rule.rule_id, value);
  };

  return (
    <div
      className="rounded-lg border border-slate-200 bg-white p-4"
      data-testid={`risk-${rule.rule_id}`}
    >
      <div className="text-xs uppercase tracking-wide text-slate-400">风险题 #{index + 1}</div>
      <p className="mt-1 text-sm text-slate-800">{rule.prompt}</p>
      <ul className="mt-3 space-y-2">
        {rule.options.map((opt, i) => {
          const isPicked = picked === opt;
          const isCorrect = opt === rule.correct;
          const showCorrect = locked && isCorrect;
          const showWrong = locked && isPicked && !isCorrect;
          return (
            <li key={`${rule.rule_id}-${i}`}>
              <button
                type="button"
                disabled={locked}
                onClick={() => handlePick(opt)}
                className={[
                  'w-full rounded border px-3 py-2 text-left text-sm transition',
                  isPicked && !locked ? 'border-forge-500 bg-forge-50' : 'border-slate-300 bg-white',
                  showCorrect ? 'border-emerald-500 bg-emerald-50' : '',
                  showWrong ? 'border-rose-500 bg-rose-50' : '',
                  locked && !showCorrect && !showWrong ? 'opacity-60' : '',
                ].join(' ')}
              >
                {opt}
              </button>
            </li>
          );
        })}
      </ul>
      {locked && result ? (
        <p
          className={[
            'mt-3 rounded p-2 text-xs',
            result.correct ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-800',
          ].join(' ')}
        >
          {result.correct ? '✓ 正确。' : '✗ 错误。'}
          {result.explanation}
        </p>
      ) : null}
    </div>
  );
}
