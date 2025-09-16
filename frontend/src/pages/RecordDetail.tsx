import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UploadCloud, Trash2, Save, MessageSquarePlus, FolderMinus } from "lucide-react";
import api from "../lib/api";
import { type RecordItem, type CommentItem, type MyReview } from "../types";
import Stars from "../components/Stars";

// Busca o record: usa o objeto passado via Link (state) quando existe;
// se a página for recarregada, faz fallback em /records e filtra pelo id.
function useRecord(id: string, fallback?: RecordItem | null) {
  return useQuery({
    queryKey: ["record", id],
    queryFn: async () => {
      if (fallback) return fallback;
      const { data } = await api.get<RecordItem[]>("/records");
      const match = data.find((r) => r.id === id);
      if (!match) throw new Error("Disco não encontrado");
      return match;
    },
    staleTime: 0,
  });
}

export default function RecordDetail() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();

  // Record vindo da navegação (Link state), se existir:
  const location = useLocation() as any;
  const initial: RecordItem | null = location?.state?.record ?? null;

  const { data: rec, isLoading: recLoading } = useRecord(id, initial);

  // ----- CAPA -----
  const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const [cacheBust, setCacheBust] = useState(0);
  const coverUrl = `${apiBase}/uploads/covers/${id}.webp${cacheBust ? `?t=${cacheBust}` : ""}`;

  const fileRef = useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      await api.put(`/records/${id}/cover`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    onSuccess: () => setCacheBust(Date.now()),
  });

  const deleteCover = useMutation({
    mutationFn: async () => api.delete(`/records/${id}/cover`),
    onSuccess: () => setCacheBust(Date.now()),
  });

  // ----- MINHA AVALIAÇÃO (0..5) -----
  const myReviewQ = useQuery({
    queryKey: ["my-review", id],
    queryFn: async () => {
      const { data } = await api.get<MyReview | null>(`/reviews/records/${id}/me`);
      return data;
    },
  });

  const [rating, setRating] = useState<number>(myReviewQ.data?.rating ?? 0);
  const [reviewText, setReviewText] = useState(myReviewQ.data?.comment ?? "");

  useEffect(() => {
    if (myReviewQ.data) {
      setRating(myReviewQ.data.rating ?? 0);
      setReviewText(myReviewQ.data.comment ?? "");
    }
  }, [myReviewQ.data]);

  const saveReview = useMutation({
    mutationFn: async () =>
      api.post("/reviews", { record_id: id, rating, comment: reviewText || undefined }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["my-review", id] });
      await qc.invalidateQueries({ queryKey: ["feed"] });
    },
  });

  // ----- COMENTÁRIOS DO DISCO -----
  const commentsQ = useQuery({
    queryKey: ["record-comments", id],
    queryFn: async () => {
      const { data } = await api.get<CommentItem[]>(`/records/${id}/comments`);
      return data;
    },
  });

  const [commentText, setCommentText] = useState("");
  const sendComment = useMutation({
    mutationFn: async () => api.post(`/records/${id}/comments`, { content: commentText }),
    onSuccess: async () => {
      setCommentText("");
      await qc.invalidateQueries({ queryKey: ["record-comments", id] });
    },
  });

  // ----- REMOVER DA COLEÇÃO -----
  const removeFromCollection = useMutation({
    mutationFn: async () => api.delete(`/collection/${id}`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["collection"] });
      navigate("/collection");
    },
  });

  if (recLoading || !rec) {
    return <div className="py-16 text-center text-white/70">Carregando…</div>;
  }

  return (
    <div className="pb-28">
      {/* CAPA + METADADOS */}
      <div className="grid lg:grid-cols-3 gap-6 pt-6">
        {/* Capa */}
        <div className="card overflow-hidden">
          <div className="aspect-square bg-black/30">
            <img
              src={coverUrl}
              alt={rec.title}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.display = "none";
              }}
            />
          </div>
          <div className="p-3 flex items-center justify-between">
            <div className="text-sm text-white/60">Capa</div>
            <div className="flex items-center gap-2">
              <input
                ref={fileRef}
                className="hidden"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) upload.mutate(f);
                }}
              />
              <button className="btn" onClick={() => fileRef.current?.click()}>
                <UploadCloud size={16} className="mr-2" /> Enviar
              </button>
              <button
                className="px-3 py-2 rounded-xl border border-white/10 hover:bg-white/5"
                onClick={() => deleteCover.mutate()}
                title="Remover capa"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* Metadados + Avaliação */}
        <div className="lg:col-span-2 card p-5">
          <h1 className="text-2xl font-bold">{rec.title}</h1>
          <p className="text-white/70">{rec.artist}</p>

          <div className="mt-3 flex flex-wrap gap-2">
            {rec.year && <span className="badge">Ano {rec.year}</span>}
            {rec.genre && <span className="badge">{rec.genre}</span>}
            {rec.label && <span className="badge">{rec.label}</span>}
            <span className="badge">code: {rec.matrix_code}</span>
          </div>

          {/* Avaliação 0..5 */}
          <div className="mt-6">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">Minha avaliação</h3>
              {myReviewQ.isFetching && (
                <span className="text-xs text-white/50">carregando…</span>
              )}
            </div>

            <div className="mt-3 flex items-center gap-3">
              <Stars value={rating} onChange={setRating} />
              <span className="text-white/60 text-sm">{rating} / 5</span>
            </div>

            <div className="mt-3 grid sm:grid-cols-[1fr_auto] gap-3">
              <input
                className="input"
                placeholder="Comentário (opcional)"
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
              />
              <button
                className="btn"
                onClick={() => saveReview.mutate()}
                disabled={saveReview.isPending}
                title="Salvar avaliação"
              >
                <Save size={16} className="mr-2" /> Salvar
              </button>
            </div>

            {saveReview.isError && (
              <div className="text-sm text-red-400 mt-1">
                Erro ao salvar avaliação
              </div>
            )}
            {saveReview.isSuccess && (
              <div className="text-sm text-green-400 mt-1">
                Avaliação salva!
              </div>
            )}
          </div>

          {/* Remover da coleção */}
          <div className="mt-6 flex justify-end">
            <button
              className="px-4 py-2 rounded-xl border border-white/10 hover:bg-white/5 inline-flex items-center gap-2"
              onClick={() => removeFromCollection.mutate()}
              title="Remover da coleção"
            >
              <FolderMinus size={16} /> Remover da coleção
            </button>
          </div>
        </div>
      </div>

      {/* COMENTÁRIOS */}
      <div className="card p-5 mt-6">
        <h3 className="font-semibold flex items-center gap-2">
          <MessageSquarePlus size={18} /> Comentários
        </h3>

        <div className="mt-3 grid sm:grid-cols-[1fr_auto] gap-3">
          <input
            className="input"
            placeholder="Escreva um comentário…"
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
          />
          <button
            className="btn"
            onClick={() => sendComment.mutate()}
            disabled={!commentText.trim() || sendComment.isPending}
          >
            Publicar
          </button>
        </div>

        <div className="mt-4 space-y-3">
          {commentsQ.isLoading && (
            <div className="text-white/60">Carregando…</div>
          )}
          {!commentsQ.isLoading && commentsQ.data?.length === 0 && (
            <div className="text-white/60">Sem comentários ainda.</div>
          )}
          {commentsQ.data?.map((c) => (
            <div
              key={c.id}
              className="p-3 rounded-2xl border border-white/10 bg-white/5"
            >
              <div className="text-sm text-white/70">
                {new Date(c.created_at).toLocaleString()}
              </div>
              <div className="mt-1">{c.content}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
