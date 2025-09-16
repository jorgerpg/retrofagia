import { useState } from "react";
import { X } from "lucide-react";
import type { NewRecordForm } from "../types";

export default function AddRecordModal({
  open,
  onClose,
  onSubmit,
  submitting = false,
  error,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: NewRecordForm) => void | Promise<void>;
  submitting?: boolean;
  error?: string | null;
}) {
  const [form, setForm] = useState<NewRecordForm>({
    matrix_code: "",
    title: "",
    artist: "",
    year: undefined,
    genre: "",
    label: "",
  });

  if (!open) return null;

  const handleChange =
    (key: keyof NewRecordForm) =>
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const v = e.target.value;
      if (key === "year") {
        const n = v ? Number(v) : undefined;
        setForm((f) => ({ ...f, year: Number.isFinite(n as number) ? (n as number) : undefined }));
      } else {
        setForm((f) => ({ ...f, [key]: v }));
      }
    };

  const canSubmit = form.matrix_code && form.title && form.artist;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || submitting) return;
    await onSubmit(form);
  };

  return (
    <div className="fixed inset-0 z-50">
      {/* backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      {/* card */}
      <div className="absolute inset-x-4 sm:inset-x-auto sm:left-1/2 sm:-translate-x-1/2 top-16 sm:top-24
                      w-[min(36rem,calc(100%-2rem))] card p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Adicionar Disco</h2>
          <button className="icon-btn w-9 h-9" onClick={onClose} title="Fechar">
            <X size={18} />
          </button>
        </div>

        <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
          <div>
            <label className="text-sm text-white/70">Matrix code *</label>
            <input className="input mt-1" placeholder="ex.: ABC-123"
                   value={form.matrix_code} onChange={handleChange("matrix_code")} />
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="text-sm text-white/70">Título *</label>
              <input className="input mt-1" placeholder="Título do álbum"
                     value={form.title} onChange={handleChange("title")} />
            </div>
            <div>
              <label className="text-sm text-white/70">Artista *</label>
              <input className="input mt-1" placeholder="Nome do artista"
                     value={form.artist} onChange={handleChange("artist")} />
            </div>
          </div>
          <div className="grid sm:grid-cols-3 gap-3">
            <div>
              <label className="text-sm text-white/70">Ano</label>
              <input className="input mt-1" placeholder="1959" inputMode="numeric"
                     value={form.year ?? ""} onChange={handleChange("year")} />
            </div>
            <div>
              <label className="text-sm text-white/70">Gênero</label>
              <input className="input mt-1" placeholder="Jazz / Rock / ..."
                     value={form.genre || ""} onChange={handleChange("genre")} />
            </div>
            <div>
              <label className="text-sm text-white/70">Gravadora</label>
              <input className="input mt-1" placeholder="Columbia, etc."
                     value={form.label || ""} onChange={handleChange("label")} />
            </div>
          </div>

          {error && (
            <div className="text-sm text-red-400">{error}</div>
          )}

          <div className="pt-2 flex items-center justify-end gap-3">
            <button type="button" className="px-4 py-2 rounded-xl border border-white/10"
                    onClick={onClose} disabled={submitting}>
              Cancelar
            </button>
            <button className="btn" type="submit" disabled={!canSubmit || submitting}>
              {submitting ? "Salvando..." : "Adicionar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
