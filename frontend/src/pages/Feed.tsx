import { useQuery } from "@tanstack/react-query";
import api from "../lib/api";


type Activity = { id: string; verb: string; object_type: string; object_id: string; created_at: string };


export default function Feed() {
  const { data, isLoading } = useQuery({
    queryKey: ["feed"],
    queryFn: async () => (await api.get<Activity[]>("/feed?limit=20")).data,
  });


  return (
    <div className="pb-28">
      <h1 className="text-2xl font-bold">Feed</h1>
      <div className="mt-4 space-y-3">
        {isLoading && <div className="card p-4">carregando…</div>}
        {data?.map(a => (
          <div key={a.id} className="card p-4">
          <div className="text-sm text-white/60">{new Date(a.created_at).toLocaleString()}</div>
          <div className="font-medium mt-1">{a.verb}</div>
          <div className="text-xs text-white/50">{a.object_type} · {a.object_id}</div>
          </div>
        ))}
      </div>
    </div>
  );
}