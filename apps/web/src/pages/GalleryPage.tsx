import { useEffect, useState } from 'react';
import { galleryApi } from '../lib/api';
import { ArtifactCard } from '../components/ArtifactCard';
import type { Artifact, ArtifactListResponse } from '@protoforge/shared';

export function GalleryPage() {
  const [data, setData] = useState<ArtifactListResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [open, setOpen] = useState<Artifact | null>(null);

  useEffect(() => {
    galleryApi
      .list()
      .then(setData)
      .catch((e: Error) => setErr(e.message));
  }, []);

  if (err) return <p className="text-rose-600">{err}</p>;
  if (!data) return <p className="text-slate-400">加载中…</p>;

  return (
    <div className="space-y-4" data-testid="gallery-page">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">作品库</h1>
        <p className="text-sm text-slate-600">共 {data.total} 个 artifact。</p>
      </header>

      {data.items.length === 0 ? (
        <p className="text-slate-400">还没有作品。完成一次锻造 → 风险门流程会保存到这里。</p>
      ) : (
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {data.items.map((a) => (
            <li key={a.id}>
              <ArtifactCard artifact={a} onOpen={(id) => setOpen(data.items.find((x) => x.id === id) ?? null)} />
            </li>
          ))}
        </ul>
      )}

      {open ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => setOpen(null)}
        >
          <div
            className="max-h-[80vh] w-[600px] overflow-auto rounded-lg bg-white p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold">{open.title}</h2>
            <p className="text-xs text-slate-500">{open.id} · {open.created_at}</p>
            <p className="mt-2 text-sm">mission: {open.mission_id}</p>
            <p className="text-sm">ritual: {open.ritual} · primary: {open.scores.primary.toFixed(3)}</p>
            <pre className="mt-3 max-h-64 overflow-auto rounded bg-slate-50 p-2 font-mono text-xs">
              {open.fasta}
            </pre>
            <button
              type="button"
              onClick={() => setOpen(null)}
              className="mt-3 rounded border border-slate-300 px-3 py-1 text-sm hover:bg-slate-50"
            >
              关闭
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
