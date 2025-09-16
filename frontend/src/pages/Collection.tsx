// src/pages/Collection.tsx
import { useEffect, useMemo, useState } from "react";
import { Search, SlidersHorizontal, Plus } from "lucide-react";
import { useAuth } from "../store/auth";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";
import { type RecordItem, type NewRecordForm } from "../types";
import RecordCard from "../components/RecordCard";
import AddRecordModal from "../components/AddRecordModal";

type CollItem = { record: RecordItem; is_favorite?: boolean };

async function fetchCollection(): Promise<CollItem[]> {
  try {
    const { data } = await api.get<any[]>("/collection/me");
    if (Array.isArray(data) && data.length && data[0]?.id) {
      return data.map((r: any) => ({ record: r, is_favorite: r.is_favorite }));
    }
    if (Array.isArray(data) && data.length && data[0]?.record) {
      return data.map((x: any) => ({ record: x.record, is_favorite: x.is_favorite }));
    }
    return [];
  } catch {
    const { data } = await api.get<RecordItem[]>("/records");
    return data.map((r) => ({ record: r, is_favorite: false }));
  }
}

export default function Collection() {
  const qc = useQueryClient();
  const { user, fetchMe, token } = useAuth();

  useEffect(() => {
    if (!user && token) fetchMe().catch(() => {});
  }, [user, token, fetchMe]);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["collection"],
    queryFn: fetchCollection,
    enabled: !!token,
    refetchOnWindowFocus: false,
    retry: false,
  });

  const [q, setQ] = useState("");
  const list = useMemo(() => {
    if (!data) return [] as CollItem[];
    const term = q.trim().toLowerCase();
    if (!term) return data;
    return data.filter(({ record: r }) =>
      r.title.toLowerCase().includes(term) || r.artist.toLowerCase().includes(term)
    );
  }, [data, q]);

  const toggleFav = useMutation({
    mutationFn: async ({ id, next }: { id: string; next: boolean }) =>
      api.patch(`/collection/${id}`, { is_favorite: next }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["collection"] }),
  });

  // --- estado do modal ---
  const [addOpen, setAddOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitErr, setSubmitErr] = useState<string | null>(null);

  // cria o disco e adiciona à coleção; trata duplicidade de matrix_code
  const createAndCollect = async (payload: NewRecordForm) => {
    setSubmitting(true);
    setSubmitErr(null);
    try {
      // 1) tenta criar o disco
      let recId: string | null = null;
      try {
        const { data: rec } = await api.post<RecordItem>("/records", payload);
        recId = rec.id;
      } catch (e: any) {
        const msg = e?.response?.data?.detail ?? "";
        const isDup = e?.response?.status === 400 && typeof msg === "string" && msg.includes("matrix_code");
        if (isDup) {
          // 2) já existe => busca por code
          const { data: found } = await api.get<RecordItem[]>("/records", {
            params: { code: payload.matrix_code },
          });
          if (Array.isArray(found) && found[0]?.id) {
            recId = found[0].id;
          } else {
            throw e;
          }
        } else {
          throw e;
        }
      }

      // 3) adiciona à coleção
      await api.post(`/collection/${recId}`);

      // 4) refresh lista e fechar
      await qc.invalidateQueries({ queryKey: ["collection"] });
      setAddOpen(false);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || "Erro ao adicionar disco";
      setSubmitErr(String(msg));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="pb-28">
      <header className="pt-6">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-bold">Minha Coleção</h1>
            <p className="text-white/60 text-sm">{list.length} álbuns</p>
          </div>
          <button className="btn" onClick={() => refetch()}>Atualizar</button>
        </div>

        <div className="mt-4 flex items-center gap-2">
          <div className="flex-1 relative">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
            <input
              className="input pl-9"
              placeholder="Buscar álbuns..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <button className="icon-btn" title="Filtro">
            <SlidersHorizontal size={18} />
          </button>
        </div>
      </header>

      <main className="mt-5 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {isLoading && Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="card h-40 animate-pulse bg-white/5" />
        ))}

        {isError && (
          <div className="col-span-full text-center text-red-400 py-10">
            Erro ao carregar: {(error as any)?.message || "desconhecido"}
          </div>
        )}

        {!isLoading && !isError && list.map(({ record, is_favorite }) => (
          <RecordCard
            key={record.id}
            rec={record}
            badge={record.genre || record.label}
            favorite={is_favorite}
            onToggleFav={() => toggleFav.mutate({ id: record.id, next: !is_favorite })}
          />
        ))}

        {!isLoading && !isError && list.length === 0 && (
          <div className="col-span-full text-center text-white/60 py-10">
            Nada por aqui… adicione um disco
          </div>
        )}
      </main>

      {/* FAB */}
      <button
        className="absolute bottom-28 right-4 icon-btn w-12 h-12"
        title="Adicionar"
        onClick={() => setAddOpen(true)}
      >
        <Plus />
      </button>

      {/* Modal */}
      <AddRecordModal
        open={addOpen}
        onClose={() => { if (!submitting) { setAddOpen(false); setSubmitErr(null); } }}
        onSubmit={createAndCollect}
        submitting={submitting}
        error={submitErr}
      />
    </div>
  );
}
