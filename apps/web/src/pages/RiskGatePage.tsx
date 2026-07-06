import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { missionApi, riskApi } from '../lib/api';
import { RiskQuestionCard } from '../components/RiskQuestionCard';
import type { Mission, RiskCheckItem, RiskCheckResponse } from '@protoforge/shared';

export function RiskGatePage() {
  const { missionId = '' } = useParams();
  const navigate = useNavigate();
  const [mission, setMission] = useState<Mission | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<RiskCheckResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    missionApi
      .get(missionId)
      .then(setMission)
      .catch((e: Error) => setErr(e.message));
  }, [missionId]);

  const allAnswered =
    mission != null && mission.risk_rules.every((r) => answers[r.rule_id]);

  const handleSubmit = async () => {
    if (!mission) return;
    try {
      const r = await riskApi.check({ mission_id: mission.id, answers });
      setResult(r);
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  if (err) return <p className="text-rose-600">{err}</p>;
  if (!mission) return <p className="text-slate-400">加载中…</p>;

  const itemByRule = (id: string): RiskCheckItem | undefined =>
    result?.items.find((i) => i.rule_id === id);

  return (
    <div className="space-y-4" data-testid="risk-gate-page">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">风险门 · {mission.title}</h1>
        <p className="text-sm text-slate-600">
          提交前必须通过生物安全 + 跨物种伦理判断。错一题即失败。
        </p>
      </header>

      <section className="space-y-3">
        {mission.risk_rules.map((rule, idx) => (
          <RiskQuestionCard
            key={rule.rule_id}
            rule={rule}
            index={idx}
            locked={result != null}
            result={
              itemByRule(rule.rule_id)
                ? {
                    correct: itemByRule(rule.rule_id)!.correct,
                    explanation: itemByRule(rule.rule_id)!.explanation,
                  }
                : undefined
            }
            onAnswer={(ruleId, ans) =>
              setAnswers((prev) => ({ ...prev, [ruleId]: ans }))
            }
          />
        ))}
      </section>

      <section className="flex items-center gap-3">
        {!result ? (
          <button
            type="button"
            disabled={!allAnswered}
            onClick={handleSubmit}
            className="rounded bg-forge-500 px-4 py-2 text-sm font-semibold text-white hover:bg-forge-600 disabled:opacity-50"
          >
            提交判定
          </button>
        ) : (
          <div className="flex items-center gap-3">
            <span
              className={[
                'rounded px-3 py-1 text-sm font-semibold',
                result.passed ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800',
              ].join(' ')}
            >
              {result.passed ? '✓ 通过' : '✗ 未通过'} (得分 {result.score.toFixed(2)})
            </span>
            <button
              type="button"
              onClick={() => navigate('/gallery')}
              className="rounded border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              查看作品库
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
